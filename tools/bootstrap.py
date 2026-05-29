"""
Gardener bootstrap — one-liner setup for python recipes.

Usage from any recipe (SKILL.md, scripts, ad-hoc):
    from bootstrap import setup; setup()
    from db import gardener_add_plant
    from plantnet import gardener_identify_plant

`setup()` is idempotent. It:
  • loads profile .env into os.environ (stripping surrounding quotes)
  • validates required runtime env vars
  • adds this tools dir to sys.path
"""
import os
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
SKILL_DIR = TOOLS_DIR.parent

REQUIRED_ENV_VARS = [
    "GARDENER_DB_URL",
    "PLANTNET_API_KEY",
]


def _candidate_env_paths() -> list[Path]:
    paths = []

    # Preferred explicit override
    env_override = os.environ.get("GARDENER_ENV_PATH")
    if env_override:
        paths.append(Path(env_override).expanduser())

    # If inside ~/.hermes/profiles/<name>/skills/gardening/tools, use that profile's .env
    profile_marker = "/.hermes/profiles/"
    skill_dir_str = str(SKILL_DIR)
    if profile_marker in skill_dir_str:
        profile_root = Path(skill_dir_str.split("/skills/", 1)[0])
        paths.append(profile_root / ".env")

    # Generic fallback
    paths.append(Path.home() / ".hermes" / ".env")

    # Deduplicate while preserving order
    deduped = []
    seen = set()
    for p in paths:
        key = str(p)
        if key not in seen:
            seen.add(key)
            deduped.append(p)
    return deduped


def _is_placeholder(value: str) -> bool:
    if not value:
        return True
    v = value.strip().lower()
    return (
        "replace_with" in v
        or "your-" in v
        or "example" in v
        or v.endswith("-here")
    )


def _validate_required_env() -> None:
    missing = []
    for key in REQUIRED_ENV_VARS:
        value = os.environ.get(key, "")
        if _is_placeholder(value):
            missing.append(key)

    if missing:
        missing_list = ", ".join(missing)
        raise RuntimeError(
            "Gardening skill is not configured. Missing required env vars: "
            f"{missing_list}. Set them in your profile .env file."
        )


def setup(validate_required: bool = True) -> None:
    for env_path in _candidate_env_paths():
        if env_path.exists():
            with env_path.open() as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    os.environ.setdefault(k, v)
            break

    if validate_required:
        _validate_required_env()

    tools_dir_str = str(TOOLS_DIR)
    if tools_dir_str not in sys.path:
        sys.path.insert(0, tools_dir_str)
