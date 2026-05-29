"""
Gardener S3 Tools — image storage via any S3-compatible backend (MinIO, AWS S3,
Cloudflare R2, Backblaze B2, Wasabi, etc.). Uses boto3 with a configurable endpoint.
"""
import os
import uuid
import base64
from datetime import datetime
from typing import Optional

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError


# Configuration — prefer generic GARDENER_S3_* names, fall back to legacy GARDENER_MINIO_*.
def _env(*names: str, default: str = "") -> str:
    for n in names:
        v = os.environ.get(n)
        if v:
            return v
    return default


S3_ENDPOINT = _env("GARDENER_S3_ENDPOINT", "GARDENER_MINIO_ENDPOINT")
S3_ACCESS_KEY = _env("GARDENER_S3_ACCESS_KEY", "GARDENER_MINIO_ACCESS_KEY")
S3_SECRET_KEY = _env("GARDENER_S3_SECRET_KEY", "GARDENER_MINIO_SECRET_KEY")
S3_BUCKET = _env("GARDENER_S3_BUCKET", "GARDENER_MINIO_BUCKET", default="plant-photos")
S3_REGION = _env("GARDENER_S3_REGION", default="us-east-1")  # placeholder for MinIO/R2


def _get_client():
    """Return a boto3 S3 client configured for the chosen backend, or None if unconfigured."""
    if not S3_SECRET_KEY:
        return None
    kwargs = {
        "aws_access_key_id": S3_ACCESS_KEY,
        "aws_secret_access_key": S3_SECRET_KEY,
        "region_name": S3_REGION,
        "config": Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    }
    if S3_ENDPOINT:
        kwargs["endpoint_url"] = S3_ENDPOINT if S3_ENDPOINT.startswith("http") else f"https://{S3_ENDPOINT}"
    return boto3.client("s3", **kwargs)


def _public_url(key: str) -> str:
    base = S3_ENDPOINT if S3_ENDPOINT.startswith("http") else f"https://{S3_ENDPOINT}"
    return f"{base.rstrip('/')}/{S3_BUCKET}/{key}"


def _key_from_url(url: str) -> str:
    marker = f"/{S3_BUCKET}/"
    return url.split(marker, 1)[1] if marker in url else url.rsplit("/", 1)[-1]


def _ensure_bucket(client):
    try:
        client.head_bucket(Bucket=S3_BUCKET)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchBucket", "NotFound"):
            create_kwargs = {"Bucket": S3_BUCKET}
            if S3_REGION and S3_REGION != "us-east-1":
                create_kwargs["CreateBucketConfiguration"] = {"LocationConstraint": S3_REGION}
            try:
                client.create_bucket(**create_kwargs)
            except ClientError:
                pass


def _sniff_content_type(image_bytes: bytes) -> str:
    if image_bytes[:4] == b"\x89PNG":
        return "image/png"
    if image_bytes[:2] in (b"\xff\xd8", b"\xff\xd9"):
        return "image/jpeg"
    if image_bytes[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def gardener_upload_photo(
    image_data: Optional[str] = None,
    image_url: Optional[str] = None,
    plant_id: Optional[str] = None,
    photo_type: str = "current",
) -> dict:
    """Upload a plant photo to the configured S3 bucket."""
    client = _get_client()
    if not client:
        return {"success": False, "error": "S3 not configured (missing credentials)"}

    try:
        if image_url:
            import requests
            resp = requests.get(image_url, timeout=30,
                                headers={"User-Agent": "Gardener/1.0"})
            if resp.status_code != 200:
                return {"success": False, "error": f"Failed to download image: {resp.status_code}"}
            image_bytes = resp.content
        elif image_data:
            image_bytes = base64.b64decode(image_data)
        else:
            return {"success": False, "error": "Either image_data or image_url required"}

        content_type = _sniff_content_type(image_bytes)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        prefix = f"plant_{plant_id}/" if plant_id else "unassigned/"
        ext = content_type.split("/")[-1]
        key = f"{prefix}{photo_type}_{timestamp}_{unique_id}.{ext}"

        _ensure_bucket(client)
        client.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=image_bytes,
            ContentType=content_type,
        )
        return {"success": True, "url": _public_url(key), "key": key}

    except ClientError as e:
        return {"success": False, "error": f"S3 error: {e.response.get('Error', {}).get('Message', str(e))}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def gardener_download_photo(url: str) -> dict:
    """Download a photo from S3 and return it as base64."""
    client = _get_client()
    if not client:
        return {"success": False, "error": "S3 not configured"}
    try:
        key = _key_from_url(url)
        obj = client.get_object(Bucket=S3_BUCKET, Key=key)
        image_bytes = obj["Body"].read()
        return {"success": True, "data": base64.b64encode(image_bytes).decode("utf-8")}
    except ClientError as e:
        return {"success": False, "error": f"S3 error: {e.response.get('Error', {}).get('Message', str(e))}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def gardener_list_photos(plant_id: Optional[str] = None, prefix: Optional[str] = None) -> dict:
    """List photos under a plant or arbitrary prefix."""
    client = _get_client()
    if not client:
        return {"success": False, "error": "S3 not configured"}
    try:
        filter_prefix = f"plant_{plant_id}/" if plant_id else (prefix or "")
        photos = []
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=filter_prefix):
            for obj in page.get("Contents", []) or []:
                photos.append({
                    "key": obj["Key"],
                    "url": _public_url(obj["Key"]),
                    "last_modified": obj["LastModified"].isoformat() if obj.get("LastModified") else None,
                    "size": obj.get("Size", 0),
                })
        return {"success": True, "photos": photos}
    except ClientError as e:
        return {"success": False, "error": f"S3 error: {e.response.get('Error', {}).get('Message', str(e))}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def gardener_delete_photo(url: str) -> dict:
    """Delete a photo from S3."""
    client = _get_client()
    if not client:
        return {"success": False, "error": "S3 not configured"}
    try:
        client.delete_object(Bucket=S3_BUCKET, Key=_key_from_url(url))
        return {"success": True}
    except ClientError as e:
        return {"success": False, "error": f"S3 error: {e.response.get('Error', {}).get('Message', str(e))}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def gardener_compare_photos(photo1_url: str, photo2_url: str) -> dict:
    """Two-image comparison handed off to the vision tool by the agent."""
    return {
        "success": True,
        "message": "Use vision tool to compare photos",
        "photo1_url": photo1_url,
        "photo2_url": photo2_url,
    }


def register_tools():
    """Register S3 tools with the toolset registry."""
    from tools.registry import registry

    tools = [
        ("gardener_upload_photo", gardener_upload_photo),
        ("gardener_download_photo", gardener_download_photo),
        ("gardener_list_photos", gardener_list_photos),
        ("gardener_delete_photo", gardener_delete_photo),
        ("gardener_compare_photos", gardener_compare_photos),
    ]
    for name, handler in tools:
        registry.register(
            name=name,
            toolset="gardener",
            schema={"name": name, "description": f"Gardener S3: {name}", "parameters": {"schema": "object"}},
            handler=handler,
            check_fn=lambda: bool(_env("GARDENER_S3_SECRET_KEY", "GARDENER_MINIO_SECRET_KEY")),
            requires_env=[],
        )


try:
    register_tools()
except Exception:
    pass
