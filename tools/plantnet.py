"""
Gardener Pl@ntNet Integration — primary plant identification via Pl@ntNet API.

Pl@ntNet is trained on ~30M images and outperforms general vision LLMs at species ID.
We call it first; the vision LLM is a fallback when Pl@ntNet returns low confidence,
no match, or the request fails.

API docs: https://my.plantnet.org/doc
"""
import os
import io
from typing import List, Optional, Union

import requests


PLANTNET_ENDPOINT = "https://my-api.plantnet.org/v2/identify"
DEFAULT_PROJECT = "all"  # "all" covers worldwide flora incl. houseplants
VALID_ORGANS = {"leaf", "flower", "fruit", "bark", "habit", "auto"}
DEFAULT_TIMEOUT = 30


def _load_image_bytes(image: Union[str, bytes]) -> tuple[bytes, str]:
    """Accept a URL, a local path, or raw bytes. Return (bytes, filename)."""
    if isinstance(image, bytes):
        return image, "plant.jpg"
    if isinstance(image, str):
        if image.startswith(("http://", "https://")):
            resp = requests.get(image, timeout=DEFAULT_TIMEOUT,
                                headers={"User-Agent": "Gardener/1.0 (plant-care-assistant)"})
            resp.raise_for_status()
            return resp.content, image.rsplit("/", 1)[-1] or "plant.jpg"
        with open(image, "rb") as f:
            return f.read(), os.path.basename(image) or "plant.jpg"
    raise TypeError(f"Unsupported image type: {type(image)}")


def gardener_identify_plant(
    images: Union[str, bytes, List[Union[str, bytes]]],
    organs: Optional[List[str]] = None,
    project: str = DEFAULT_PROJECT,
    max_results: int = 5,
) -> dict:
    """Identify a plant from one or more photos via Pl@ntNet.

    Args:
        images: A single image (URL, local path, or raw bytes) or a list of up to 5.
            Multiple angles (whole plant + close-up leaf + flower) sharply increase accuracy.
        organs: Parallel list naming each image's organ: leaf | flower | fruit | bark | habit | auto.
            Defaults to ["auto"] * len(images). Pl@ntNet uses this as a hint, not a constraint.
        project: Pl@ntNet flora project. "all" is the safe default for houseplants.
        max_results: How many candidate species to return.

    Returns dict:
        {
          "success": True,
          "best_match": {
            "scientific_name": "Monstera deliciosa",
            "common_name": "Swiss cheese plant",
            "genus": "Monstera",
            "family": "Araceae",
            "confidence": 0.8421,
          },
          "candidates": [ {scientific_name, common_name, confidence}, ... ],
          "remaining_requests": 487,
        }
        or {"success": False, "error": "..."} on failure.

    Confidence interpretation (Pl@ntNet `score`, 0.0–1.0):
        >= 0.50  →  Very strong, treat as identified (still confirm with user).
        0.25–0.50 → Likely; show alternatives.
        0.10–0.25 → Weak; show top 2–3, ask user.
        < 0.10   →  No reliable match; fall back to vision LLM or ask user directly.
    """
    api_key = os.environ.get("PLANTNET_API_KEY") or os.environ.get("GARDENER_PLANTNET_API_KEY")
    if not api_key:
        return {"success": False, "error": "PLANTNET_API_KEY not set in environment"}

    if not isinstance(images, list):
        images = [images]
    if len(images) == 0 or len(images) > 5:
        return {"success": False, "error": "Pl@ntNet accepts 1 to 5 images"}

    if organs is None:
        organs = ["auto"] * len(images)
    if len(organs) != len(images):
        return {"success": False, "error": "organs list must match images list length"}
    bad = [o for o in organs if o not in VALID_ORGANS]
    if bad:
        return {"success": False, "error": f"Invalid organ(s): {bad}. Use one of {sorted(VALID_ORGANS)}"}

    try:
        files = []
        for idx, img in enumerate(images):
            data, name = _load_image_bytes(img)
            files.append(("images", (name, io.BytesIO(data), "image/jpeg")))
        data_payload = [("organs", o) for o in organs]

        url = f"{PLANTNET_ENDPOINT}/{project}"
        resp = requests.post(
            url,
            params={"api-key": api_key, "nb-results": max_results, "lang": "en"},
            files=files,
            data=data_payload,
            timeout=DEFAULT_TIMEOUT,
        )
    except requests.RequestException as e:
        return {"success": False, "error": f"Pl@ntNet request failed: {e}"}
    except (OSError, ValueError) as e:
        return {"success": False, "error": f"Image load failed: {e}"}

    if resp.status_code == 401:
        return {"success": False, "error": "Pl@ntNet auth failed — check PLANTNET_API_KEY"}
    if resp.status_code == 404:
        return {"success": False, "error": "no_match", "message": "Pl@ntNet found no candidate species"}
    if resp.status_code == 429:
        return {"success": False, "error": "quota_exceeded", "message": "Pl@ntNet daily quota reached"}
    if resp.status_code >= 400:
        return {"success": False, "error": f"Pl@ntNet HTTP {resp.status_code}: {resp.text[:200]}"}

    try:
        payload = resp.json()
    except ValueError:
        return {"success": False, "error": "Pl@ntNet returned non-JSON response"}

    results = payload.get("results") or []
    if not results:
        return {"success": False, "error": "no_match", "remaining_requests": payload.get("remainingIdentificationRequests")}

    def _flatten(r):
        sp = r.get("species") or {}
        return {
            "scientific_name": sp.get("scientificNameWithoutAuthor"),
            "common_name": (sp.get("commonNames") or [None])[0],
            "common_names": sp.get("commonNames") or [],
            "genus": (sp.get("genus") or {}).get("scientificNameWithoutAuthor"),
            "family": (sp.get("family") or {}).get("scientificNameWithoutAuthor"),
            "confidence": round(float(r.get("score") or 0.0), 4),
        }

    candidates = [_flatten(r) for r in results]
    return {
        "success": True,
        "best_match": candidates[0],
        "candidates": candidates,
        "remaining_requests": payload.get("remainingIdentificationRequests"),
    }


# ─── Tool Registration ─────────────────────────────────────────────────

def register_tools():
    from tools.registry import registry
    registry.register(
        name="gardener_identify_plant",
        toolset="gardener",
        schema={
            "name": "gardener_identify_plant",
            "description": "Identify a plant species from photos via Pl@ntNet. Returns top candidates with confidence scores.",
            "parameters": {"schema": "object"},
        },
        handler=gardener_identify_plant,
    )


try:
    register_tools()
except Exception:
    pass
