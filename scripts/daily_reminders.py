#!/usr/bin/env python3
"""
Gardener Daily Reminders — cron script for daily care reminders.

Communicator-agnostic by design: this script only emits structured JSON
about what care tasks are due and who can receive them. It does not write
human-facing reminder copy; wording is left to the Hermes LLM at delivery time.
"""
import os
import sys
import json
from datetime import datetime

# Add skill root to path so `tools.*` imports work both from the skill's own
# scripts/ directory and from profile-level cron script copies.
_SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if not os.path.isdir(os.path.join(_SKILL_ROOT, "tools")):
    # fallback: if script copied elsewhere, honor explicit override
    _SKILL_ROOT = os.environ.get("GARDENING_SKILL_ROOT", _SKILL_ROOT)
sys.path.insert(0, _SKILL_ROOT)

from tools.db import _get_connection


CARE_EMOJI = {
    "water": "💧",
    "fertilize": "🌱",
    "repot": "🪴",
    "prune": "✂️",
    "misting": "💨",
}


def _dict_from_row(row) -> dict:
    """Convert psycopg2 row to a plain dict."""
    if row is None:
        return None
    if hasattr(row, "keys"):
        return dict(row)
    return dict(row)


def _format_target(platform: str, identifier) -> str | None:
    """Return a Hermes send_message target for one stored platform identifier."""
    if not platform or identifier in (None, ""):
        return None
    if isinstance(identifier, dict):
        target = identifier.get("target")
        if target:
            return str(target)
        identifier = (
            identifier.get("identifier")
            or identifier.get("id")
            or identifier.get("chat_id")
            or identifier.get("user_id")
        )
    if identifier in (None, ""):
        return None
    identifier = str(identifier)
    if identifier.startswith(f"{platform}:"):
        return identifier
    return f"{platform}:{identifier}"


def normalize_recipient(user: dict) -> dict:
    """Normalize a DB user row into communicator-agnostic Hermes targets."""
    platform_identifiers = user.get("platform_identifiers") or {}
    targets = []
    for platform, identifier in platform_identifiers.items():
        target = _format_target(platform, identifier)
        if target:
            targets.append(target)
    return {
        "gardener_user_id": user.get("id"),
        "hermes_user_id": user.get("hermes_user_id"),
        "name": user.get("name"),
        "timezone": user.get("timezone"),
        "targets": targets,
    }


def get_all_recipients() -> list:
    """Get all users for this single-household Gardener agent."""
    conn = _get_connection()
    if not conn:
        return []
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, hermes_user_id, name, timezone, platform_identifiers
                FROM gardener_users
                ORDER BY id ASC
            """)
            return [normalize_recipient(_dict_from_row(row)) for row in cur.fetchall()]
    finally:
        conn.close()


def get_due_tasks() -> list:
    """Get all due plant-care tasks for this single-household Gardener agent."""
    conn = _get_connection()
    if not conn:
        return []
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.id as plant_id, p.name, p.species, p.owner_id,
                       cs.care_type, cs.next_due, cs.base_frequency_days
                FROM gardener_plants p
                JOIN gardener_care_schedules cs ON p.id = cs.plant_id
                WHERE p.archived_at IS NULL
                  AND cs.next_due <= NOW()
                ORDER BY cs.next_due ASC
            """)
            tasks = []
            for row in cur.fetchall():
                task = _dict_from_row(row)
                tasks.append({
                    "plant_id": task.get("plant_id"),
                    "plant_name": task.get("name"),
                    "species": task.get("species"),
                    "care_type": task.get("care_type"),
                    "next_due": task.get("next_due"),
                    "base_frequency_days": task.get("base_frequency_days"),
                    "owner_id": task.get("owner_id"),
                })
            return tasks
    finally:
        conn.close()


def get_due_tasks_payload() -> dict:
    """Return JSON-ready care tasks and recipients; wording is left to the LLM."""
    return {
        "generated_at": datetime.now().isoformat(),
        "tasks": get_due_tasks(),
        "recipients": get_all_recipients(),
    }


def format_reminder_text(plant: dict, care_type: str) -> str:
    """Legacy helper for interactive/manual use; cron output does not use it."""
    emoji = CARE_EMOJI.get(care_type, "🌿")
    name = plant.get("name", "Unknown Plant")
    species = plant.get("species", "")
    msg = f"{emoji} *{name}* needs {care_type}"
    if species:
        msg += f" ({species})"
    return msg


def main():
    """Print JSON describing due tasks and recipients."""
    db_url = os.environ.get("GARDENER_DB_URL")
    if not db_url:
        print("Gardener: GARDENER_DB_URL not configured")
        return

    payload = get_due_tasks_payload()
    if payload["tasks"]:
        print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
    else:
        print("Gardener: No plants need care today 🌿")


if __name__ == "__main__":
    main()
