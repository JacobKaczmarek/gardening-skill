"""
Gardener Database Tools — PostgreSQL operations for plant care.
"""
import json
import os
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any

import psycopg2
from psycopg2.extras import RealDictCursor

# Database connection from environment
DB_URL = os.environ.get("GARDENER_DB_URL")


def _get_connection():
    """Get a database connection."""
    if not DB_URL:
        return None
    return psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)


def _dict_from_row(row) -> Optional[Dict]:
    """Convert psycopg2 RealDictRow to plain dict."""
    if row is None:
        return None
    return dict(row)


# ─── Schema Initialization ──────────────────────────────────────────────

def init_schema() -> dict:
    """Create all gardener tables if they don't exist.
    
    Platform-agnostic design:
    - hermes_user_id: local canonical identifier for a Gardener user
    - platform_identifiers: JSONB storing Hermes-sendable target mappings
    - one Gardener profile acts as one household boundary
    - plants can have multiple owners via gardener_plant_owners
    """
    conn = _get_connection()
    if not conn:
        return {"success": False, "error": "GARDENER_DB_URL not set"}
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                -- Users table (platform-agnostic)
                CREATE TABLE IF NOT EXISTS gardener_users (
                    id SERIAL PRIMARY KEY,
                    hermes_user_id VARCHAR(255) UNIQUE NOT NULL,
                    name VARCHAR(255),
                    timezone VARCHAR(100) DEFAULT 'Europe/Warsaw',
                    platform_identifiers JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT NOW()
                );

                -- Plants table
                CREATE TABLE IF NOT EXISTS gardener_plants (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    species VARCHAR(255) NOT NULL,
                    owner_id INTEGER REFERENCES gardener_users(id),
                    photo_url TEXT,
                    baseline_photo_url TEXT,
                    archived_at TIMESTAMP,
                    archived_reason TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                );

                -- Plant owners (many-to-many)
                CREATE TABLE IF NOT EXISTS gardener_plant_owners (
                    plant_id INTEGER REFERENCES gardener_plants(id) ON DELETE CASCADE,
                    user_id INTEGER REFERENCES gardener_users(id) ON DELETE CASCADE,
                    is_primary BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    PRIMARY KEY (plant_id, user_id)
                );

                -- Care schedules
                CREATE TABLE IF NOT EXISTS gardener_care_schedules (
                    id SERIAL PRIMARY KEY,
                    plant_id INTEGER REFERENCES gardener_plants(id) ON DELETE CASCADE,
                    care_type VARCHAR(50) NOT NULL,
                    base_frequency_days INTEGER NOT NULL,
                    seasonal_adjustments JSONB DEFAULT '{}',
                    last_completed TIMESTAMP,
                    next_due TIMESTAMP,
                    UNIQUE(plant_id, care_type)
                );

                -- Care events log
                CREATE TABLE IF NOT EXISTS gardener_care_events (
                    id SERIAL PRIMARY KEY,
                    plant_id INTEGER REFERENCES gardener_plants(id) ON DELETE CASCADE,
                    care_type VARCHAR(50) NOT NULL,
                    completed_at TIMESTAMP DEFAULT NOW(),
                    performed_by INTEGER REFERENCES gardener_users(id),
                    notes TEXT,
                    photo_url TEXT
                );

                -- Health checkups
                CREATE TABLE IF NOT EXISTS gardener_health_checkups (
                    id SERIAL PRIMARY KEY,
                    plant_id INTEGER REFERENCES gardener_plants(id) ON DELETE CASCADE,
                    checked_at TIMESTAMP DEFAULT NOW(),
                    photo_url TEXT,
                    status VARCHAR(20) DEFAULT 'healthy',
                    issues JSONB DEFAULT '[]',
                    recommendations TEXT,
                    resolved_at TIMESTAMP
                );

                -- Plant guides (species-specific care info)
                CREATE TABLE IF NOT EXISTS gardener_plant_guides (
                    id SERIAL PRIMARY KEY,
                    species VARCHAR(255) UNIQUE NOT NULL,
                    content TEXT,
                    common_issues JSONB DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT NOW()
                );

                -- Vacation mode
                CREATE TABLE IF NOT EXISTS gardener_vacation_mode (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES gardener_users(id) ON DELETE CASCADE,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    active BOOLEAN DEFAULT TRUE
                );

                -- Care reminders (for tracking pending care)
                CREATE TABLE IF NOT EXISTS gardener_care_reminders (
                    id SERIAL PRIMARY KEY,
                    plant_id INTEGER REFERENCES gardener_plants(id) ON DELETE CASCADE,
                    care_type VARCHAR(50) NOT NULL,
                    message_id VARCHAR(255),
                    sent_at TIMESTAMP DEFAULT NOW(),
                    watering_confirmed BOOLEAN DEFAULT FALSE,
                    confirmed_by INTEGER REFERENCES gardener_users(id),
                    escalated BOOLEAN DEFAULT FALSE
                );

                -- Indexes
                CREATE INDEX IF NOT EXISTS idx_plants_owner ON gardener_plants(owner_id);
                CREATE INDEX IF NOT EXISTS idx_plant_owners_user ON gardener_plant_owners(user_id);
                CREATE INDEX IF NOT EXISTS idx_care_schedules_next_due ON gardener_care_schedules(next_due);
                CREATE INDEX IF NOT EXISTS idx_care_reminders_pending ON gardener_care_reminders(watering_confirmed) WHERE NOT watering_confirmed;
            """)
            conn.commit()
        return {"success": True, "message": "Schema initialized"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


# ─── User / Session Identity Operations ─────────────────────────────────

def _get_session_value(name: str, default: str = "") -> str:
    """Read Hermes gateway session context with an env fallback for tests/CLI."""
    try:
        from gateway.session_context import get_session_env
        return get_session_env(name, default)
    except Exception:
        return os.environ.get(name, default)


def gardener_get_current_identity() -> dict:
    """Return the current Hermes gateway identity as a Gardener routing record.

    This is the inbound bridge that keeps Gardener communicator-agnostic: tools
    can resolve the current sender without parsing IDs out of LLM prompt text.
    """
    platform = _get_session_value("HERMES_SESSION_PLATFORM", "") or None
    user_id = _get_session_value("HERMES_SESSION_USER_ID", "") or None
    chat_id = _get_session_value("HERMES_SESSION_CHAT_ID", "") or None
    thread_id = _get_session_value("HERMES_SESSION_THREAD_ID", "") or None
    user_name = _get_session_value("HERMES_SESSION_USER_NAME", "") or None

    target = None
    if platform and chat_id:
        target = f"{platform}:{chat_id}"
        if thread_id:
            target = f"{target}:{thread_id}"

    return {
        "platform": platform,
        "user_id": user_id,
        "chat_id": chat_id,
        "thread_id": thread_id,
        "user_name": user_name,
        "target": target,
    }


# ─── User Operations ────────────────────────────────────────────────────

def gardener_upsert_user(
    hermes_user_id: str,
    name: str = None,
    timezone: str = "Europe/Warsaw",
    platform: str = "telegram",
    platform_id: str = None
) -> dict:
    """Create or update a user by hermes_user_id (platform-agnostic).
    
    platform_identifiers stores {platform: id} mappings so we know which
    platform identifiers (telegram, discord, etc.) map to this user.
    """
    conn = _get_connection()
    if not conn:
        return {"success": False, "error": "DB not configured"}
    try:
        with conn.cursor() as cur:
            # Build platform_identifiers update
            platform_update = {}
            if platform and platform_id:
                platform_update = {platform: platform_id}
            
            if platform_update:
                cur.execute("""
                    INSERT INTO gardener_users (hermes_user_id, name, timezone, platform_identifiers)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (hermes_user_id) DO UPDATE SET
                        name = COALESCE(NULLIF(EXCLUDED.name, NULL), gardener_users.name),
                        timezone = COALESCE(NULLIF(EXCLUDED.timezone, NULL), gardener_users.timezone),
                        platform_identifiers = gardener_users.platform_identifiers || %s
                    RETURNING id, hermes_user_id, name, timezone, platform_identifiers
                """, (hermes_user_id, name, timezone, json.dumps(platform_update), json.dumps(platform_update)))
            else:
                cur.execute("""
                    INSERT INTO gardener_users (hermes_user_id, name, timezone)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (hermes_user_id) DO UPDATE SET
                        name = COALESCE(NULLIF(EXCLUDED.name, NULL), gardener_users.name),
                        timezone = COALESCE(NULLIF(EXCLUDED.timezone, NULL), gardener_users.timezone)
                    RETURNING id, hermes_user_id, name, timezone, platform_identifiers
                """, (hermes_user_id, name, timezone))
            row = cur.fetchone()
            conn.commit()
            return {"success": True, "user": _dict_from_row(row)}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def gardener_get_user(hermes_user_id: str) -> dict:
    """Get user by hermes_user_id."""
    conn = _get_connection()
    if not conn:
        return {"success": False, "error": "DB not configured"}
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, hermes_user_id, name, timezone, platform_identifiers
                FROM gardener_users WHERE hermes_user_id = %s
            """, (hermes_user_id,))
            row = cur.fetchone()
            return {"success": True, "user": _dict_from_row(row)}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def gardener_get_household_users(household_id: int = None) -> dict:
    """Compatibility alias: return all registered users for this Gardener profile."""
    conn = _get_connection()
    if not conn:
        return {"success": False, "error": "DB not configured"}
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, hermes_user_id, name, timezone, platform_identifiers
                FROM gardener_users
                ORDER BY id ASC
            """)
            rows = cur.fetchall()
            return {"success": True, "users": [_dict_from_row(r) for r in rows]}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


# ─── Plant Operations ──────────────────────────────────────────────────

def gardener_add_plant(
    name: str,
    species: str,
    owner_id: int,
    photo_url: str = None,
    baseline_photo_url: str = None,
    owner_ids: list = None,
    auto_schedule_water_days: int = None,
    auto_schedule_fertilize_days: int = None,
    last_watered_days_ago: int = None,
) -> dict:
    """Add a new plant for a user, optionally auto-create care schedules.

    owner_id is the gardener_users.id — not a telegram ID. Use gardener_upsert_user
    first to get the owner_id if you only have a hermes_user_id.

    Names come from the user — there is no auto-naming.

    If auto_schedule_water_days is provided, creates a watering schedule. Its
    next_due is anchored to `last_watered_days_ago` if given (so a plant already
    overdue at registration is correctly flagged), otherwise to now.

    If last_watered_days_ago is provided, also writes a backdated 'water' event
    so the plant's care history starts truthfully from day one. Pass 0 for
    "watered today".

    If auto_schedule_fertilize_days is provided, creates a fertilizing schedule.
    """
    conn = _get_connection()
    if not conn:
        return {"success": False, "error": "DB not configured"}
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO gardener_plants (name, species, owner_id, photo_url, baseline_photo_url)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, name, species, owner_id, photo_url, baseline_photo_url, archived_at, created_at
            """, (name, species, owner_id, photo_url, baseline_photo_url or photo_url))
            row = cur.fetchone()
            plant = _dict_from_row(row)

            # Plant ownership (many-to-many): owner_id is always included as primary
            owner_set = set(owner_ids or [])
            owner_set.add(owner_id)
            for uid in sorted(owner_set):
                cur.execute("""
                    INSERT INTO gardener_plant_owners (plant_id, user_id, is_primary)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (plant_id, user_id) DO UPDATE SET
                        is_primary = gardener_plant_owners.is_primary OR EXCLUDED.is_primary
                """, (plant["id"], uid, uid == owner_id))
            # Auto-create watering schedule if requested
            if auto_schedule_water_days is not None:
                from datetime import datetime, timedelta
                now = datetime.now()
                if last_watered_days_ago is not None:
                    last_watered_at = now - timedelta(days=last_watered_days_ago)
                    next_due = last_watered_at + timedelta(days=auto_schedule_water_days)
                else:
                    last_watered_at = None
                    next_due = now + timedelta(days=auto_schedule_water_days)
                cur.execute("""
                    INSERT INTO gardener_care_schedules (plant_id, care_type, base_frequency_days, seasonal_adjustments, next_due, last_completed)
                    VALUES (%s, 'water', %s, %s, %s, %s)
                    ON CONFLICT (plant_id, care_type) DO UPDATE SET
                        base_frequency_days = EXCLUDED.base_frequency_days,
                        seasonal_adjustments = EXCLUDED.seasonal_adjustments,
                        next_due = EXCLUDED.next_due,
                        last_completed = EXCLUDED.last_completed
                """, (plant["id"], auto_schedule_water_days,
                      '{"multiplier": {"winter": 1.5, "spring": 1.0, "summer": 0.7, "autumn": 1.0}}',
                      next_due, last_watered_at))

                # Backdate the initial watering event if the user reported one
                if last_watered_at is not None:
                    cur.execute("""
                        INSERT INTO gardener_care_events (plant_id, care_type, completed_at, notes)
                        VALUES (%s, 'water', %s, %s)
                    """, (plant["id"], last_watered_at, "Initial event recorded at plant registration"))
            
            # Auto-create fertilizing schedule if requested (monthly during growing season)
            if auto_schedule_fertilize_days is not None:
                from datetime import datetime, timedelta
                next_due = datetime.now() + timedelta(days=auto_schedule_fertilize_days)
                cur.execute("""
                    INSERT INTO gardener_care_schedules (plant_id, care_type, base_frequency_days, seasonal_adjustments, next_due)
                    VALUES (%s, 'fertilize', %s, %s, %s)
                    ON CONFLICT (plant_id, care_type) DO UPDATE SET
                        base_frequency_days = EXCLUDED.base_frequency_days,
                        seasonal_adjustments = EXCLUDED.seasonal_adjustments,
                        next_due = EXCLUDED.next_due
                """, (plant["id"], auto_schedule_fertilize_days,
                      '{"disabled_seasons": ["winter"]}',
                      next_due))
            
            conn.commit()
            return {"success": True, "plant": plant}
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def gardener_get_plants(hermes_user_id: str, include_archived: bool = False) -> dict:
    """Get all plants tracked by this Gardener agent.

    A Gardener profile represents one household, so plant visibility is profile-wide
    rather than filtered through a separate household_id.
    """
    conn = _get_connection()
    if not conn:
        return {"success": False, "error": "DB not configured"}

    result = gardener_get_user(hermes_user_id)
    if not result.get("success"):
        return result

    try:
        with conn.cursor() as cur:
            archived_filter = "" if include_archived else "WHERE p.archived_at IS NULL"
            cur.execute(f"""
                SELECT p.*, u.name as owner_name, u.hermes_user_id as owner_hermes_user_id,
                       COALESCE(array_agg(po.user_id) FILTER (WHERE po.user_id IS NOT NULL), '{{}}') AS owner_ids
                FROM gardener_plants p
                JOIN gardener_users u ON p.owner_id = u.id
                LEFT JOIN gardener_plant_owners po ON po.plant_id = p.id
                {archived_filter}
                GROUP BY p.id, u.name, u.hermes_user_id
                ORDER BY p.created_at DESC
            """)
            rows = cur.fetchall()
            return {"success": True, "plants": [_dict_from_row(r) for r in rows]}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def gardener_archive_plant(plant_id: int, reason: str) -> dict:
    """Archive a plant with a reason."""
    conn = _get_connection()
    if not conn:
        return {"success": False, "error": "DB not configured"}
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE gardener_plants 
                SET archived_at = NOW(), archived_reason = %s
                WHERE id = %s
                RETURNING id, name, archived_at, archived_reason
            """, (reason, plant_id))
            row = cur.fetchone()
            conn.commit()
            return {"success": True, "plant": _dict_from_row(row)} if row else {"success": False, "error": "Plant not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def gardener_update_plant_photos(
    plant_id: int,
    photo_url: str = None,
    baseline_photo_url: str = None,
    set_baseline_from_photo: bool = False,
) -> dict:
    """Update plant photo fields after photo upload."""
    conn = _get_connection()
    if not conn:
        return {"success": False, "error": "DB not configured"}

    if photo_url is None and baseline_photo_url is None and not set_baseline_from_photo:
        return {"success": False, "error": "Provide photo_url and/or baseline_photo_url"}

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, photo_url, baseline_photo_url FROM gardener_plants WHERE id = %s", (plant_id,))
            existing = cur.fetchone()
            if not existing:
                return {"success": False, "error": "Plant not found"}

            # existing is a dict row (RealDictCursor), not a positional tuple
            next_photo_url = photo_url if photo_url is not None else existing.get("photo_url")
            if baseline_photo_url is not None:
                next_baseline = baseline_photo_url
            elif photo_url and (set_baseline_from_photo or existing.get("baseline_photo_url") is None):
                # Auto-seed baseline from first persisted photo when baseline is empty.
                next_baseline = photo_url
            else:
                next_baseline = existing.get("baseline_photo_url")

            cur.execute("""
                UPDATE gardener_plants
                SET photo_url = %s,
                    baseline_photo_url = %s
                WHERE id = %s
                RETURNING id, name, species, owner_id, photo_url, baseline_photo_url, archived_at, created_at
            """, (next_photo_url, next_baseline, plant_id))
            row = cur.fetchone()
            conn.commit()
            return {"success": True, "plant": _dict_from_row(row)}
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def gardener_set_plant_owners(plant_id: int, owner_ids: list, primary_owner_id: int = None) -> dict:
    """Replace owners for a plant using the normalized ownership table."""
    conn = _get_connection()
    if not conn:
        return {"success": False, "error": "DB not configured"}

    if not owner_ids:
        return {"success": False, "error": "owner_ids cannot be empty"}

    owner_set = sorted(set(int(x) for x in owner_ids))
    if primary_owner_id is None:
        primary_owner_id = owner_set[0]
    if primary_owner_id not in owner_set:
        owner_set.append(int(primary_owner_id))
        owner_set = sorted(set(owner_set))

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM gardener_plants WHERE id = %s", (plant_id,))
            if not cur.fetchone():
                return {"success": False, "error": "Plant not found"}

            cur.execute("DELETE FROM gardener_plant_owners WHERE plant_id = %s", (plant_id,))
            for uid in owner_set:
                cur.execute("""
                    INSERT INTO gardener_plant_owners (plant_id, user_id, is_primary)
                    VALUES (%s, %s, %s)
                """, (plant_id, uid, uid == primary_owner_id))

            cur.execute("UPDATE gardener_plants SET owner_id = %s WHERE id = %s", (primary_owner_id, plant_id))
            conn.commit()
            return {
                "success": True,
                "plant_id": plant_id,
                "primary_owner_id": primary_owner_id,
                "owner_ids": owner_set,
            }
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


# ─── Care Schedule Operations ─────────────────────────────────────────

def gardener_set_care_schedule(
    plant_id: int,
    care_type: str,
    frequency_days: int,
    seasonal_adjustments: dict = None,
    start_date: datetime = None
) -> dict:
    """Set or update a care schedule for a plant."""
    conn = _get_connection()
    if not conn:
        return {"success": False, "error": "DB not configured"}
    
    adjustments = seasonal_adjustments or {
        "water": {"multiplier": {"winter": 1.5, "spring": 1.0, "summer": 0.7, "autumn": 1.0}},
        "fertilize": {"disabled_seasons": ["winter"]}
    }
    
    next_due = start_date or datetime.now()
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO gardener_care_schedules (plant_id, care_type, base_frequency_days, seasonal_adjustments, next_due)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (plant_id, care_type) DO UPDATE SET
                    base_frequency_days = EXCLUDED.base_frequency_days,
                    seasonal_adjustments = EXCLUDED.seasonal_adjustments,
                    next_due = EXCLUDED.next_due
                RETURNING *
            """, (plant_id, care_type, frequency_days, json.dumps(adjustments), next_due))
            row = cur.fetchone()
            conn.commit()
            return {"success": True, "schedule": _dict_from_row(row)}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def gardener_get_due_care(hermes_user_id: str, care_type: str = None) -> dict:
    """Get plants needing care today for this Gardener agent.

    A Gardener profile represents one household, so due-care lookup is global
    across all tracked plants instead of filtered by household_id.
    """
    conn = _get_connection()
    if not conn:
        return {"success": False, "error": "DB not configured"}

    result = gardener_get_user(hermes_user_id)
    if not result.get("success"):
        return result
    user = result["user"]

    try:
        with conn.cursor() as cur:
            # Vacation mode is still per user: if the requesting/owning agent user
            # is away, suppress reminders for this run.
            cur.execute("""
                SELECT COUNT(*) as count FROM gardener_vacation_mode
                WHERE user_id = %s AND active = TRUE
                  AND CURRENT_DATE BETWEEN start_date AND end_date
            """, (user["id"],))
            vacation = cur.fetchone()
            if vacation and vacation["count"] > 0:
                return {"success": True, "plants": [], "vacation": True}

            params = []
            type_filter = ""
            if care_type:
                type_filter = "AND cs.care_type = %s"
                params.append(care_type)
            cur.execute(f"""
                SELECT p.id, p.name, p.species, cs.care_type, cs.next_due, cs.base_frequency_days,
                       COALESCE(array_agg(po.user_id) FILTER (WHERE po.user_id IS NOT NULL), '{{}}') AS owner_ids,
                       cr.id as reminder_id, cr.message_id, cr.sent_at
                FROM gardener_plants p
                JOIN gardener_care_schedules cs ON p.id = cs.plant_id
                LEFT JOIN gardener_plant_owners po ON po.plant_id = p.id
                LEFT JOIN gardener_care_reminders cr ON cr.plant_id = p.id
                    AND cr.care_type = cs.care_type AND cr.watering_confirmed = FALSE
                WHERE p.archived_at IS NULL
                  AND cs.next_due <= NOW()
                  {type_filter}
                GROUP BY p.id, p.name, p.species, cs.care_type, cs.next_due, cs.base_frequency_days, cr.id, cr.message_id, cr.sent_at
                ORDER BY cs.next_due ASC
            """, params)
            rows = cur.fetchall()
            return {"success": True, "plants": [_dict_from_row(r) for r in rows], "vacation": False}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def gardener_log_care_event(
    plant_id: int,
    care_type: str,
    notes: str = None,
    photo_url: str = None,
    performed_by: int = None
) -> dict:
    """Log a care event and update schedule.
    
    performed_by is the gardener_users.id of who performed the care action.
    """
    conn = _get_connection()
    if not conn:
        return {"success": False, "error": "DB not configured"}
    
    try:
        with conn.cursor() as cur:
            # Get schedule to recalculate next_due
            cur.execute("""
                SELECT * FROM gardener_care_schedules 
                WHERE plant_id = %s AND care_type = %s
            """, (plant_id, care_type))
            schedule = cur.fetchone()
            
            if schedule:
                # Calculate next due with seasonal adjustment
                multiplier = 1.0
                season = _get_current_season()
                if schedule["seasonal_adjustments"]:
                    adj = schedule["seasonal_adjustments"]
                    if care_type in adj and "multiplier" in adj[care_type]:
                        multiplier = adj[care_type]["multiplier"].get(season.lower(), 1.0)
                
                next_due = datetime.now() + timedelta(days=int(schedule["base_frequency_days"] * multiplier))
                
                # Update schedule
                cur.execute("""
                    UPDATE gardener_care_schedules
                    SET last_completed = NOW(), next_due = %s
                    WHERE plant_id = %s AND care_type = %s
                """, (next_due, plant_id, care_type))
            
            # Log event with performer tracking
            cur.execute("""
                INSERT INTO gardener_care_events (plant_id, care_type, performed_by, notes, photo_url)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING *
            """, (plant_id, care_type, performed_by, notes, photo_url))
            row = cur.fetchone()
            conn.commit()
            
            # Mark reminder as confirmed
            if schedule:
                cur.execute("""
                    UPDATE gardener_care_reminders
                    SET watering_confirmed = TRUE, confirmed_by = %s
                    WHERE plant_id = %s AND care_type = %s AND watering_confirmed = FALSE
                """, (performed_by, plant_id, care_type))
                conn.commit()
            
            return {"success": True, "event": _dict_from_row(row)}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def gardener_create_reminder(plant_id: int, care_type: str, message_id: str) -> dict:
    """Create a care reminder for reaction tracking."""
    conn = _get_connection()
    if not conn:
        return {"success": False, "error": "DB not configured"}
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO gardener_care_reminders (plant_id, care_type, message_id)
                VALUES (%s, %s, %s)
                RETURNING *
            """, (plant_id, care_type, message_id))
            row = cur.fetchone()
            conn.commit()
            return {"success": True, "reminder": _dict_from_row(row)}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def gardener_confirm_reminder(message_id: str) -> dict:
    """Confirm a care reminder by message_id."""
    conn = _get_connection()
    if not conn:
        return {"success": False, "error": "DB not configured"}
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE gardener_care_reminders
                SET watering_confirmed = TRUE
                WHERE message_id = %s
                RETURNING plant_id, care_type
            """, (message_id,))
            row = cur.fetchone()
            conn.commit()
            
            if row:
                # Log care event
                return gardener_log_care_event(row["plant_id"], row["care_type"])
            return {"success": False, "error": "Reminder not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


# ─── Health Checkup Operations ─────────────────────────────────────────

def gardener_save_checkup(
    plant_id: int,
    photo_url: str,
    status: str,
    issues: list = None,
    recommendations: str = None
) -> dict:
    """Save a health checkup result."""
    conn = _get_connection()
    if not conn:
        return {"success": False, "error": "DB not configured"}
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO gardener_health_checkups (plant_id, photo_url, status, issues, recommendations)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING *
            """, (plant_id, photo_url, status, json.dumps(issues or []), recommendations))
            row = cur.fetchone()
            conn.commit()
            return {"success": True, "checkup": _dict_from_row(row)}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def gardener_resolve_checkup(checkup_id: int) -> dict:
    """Mark a health checkup as resolved."""
    conn = _get_connection()
    if not conn:
        return {"success": False, "error": "DB not configured"}
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE gardener_health_checkups
                SET resolved_at = NOW()
                WHERE id = %s
                RETURNING *
            """, (checkup_id,))
            row = cur.fetchone()
            conn.commit()
            return {"success": True, "checkup": _dict_from_row(row)}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def gardener_get_checkup_history(plant_id: int) -> dict:
    """Get health checkup history for a plant."""
    conn = _get_connection()
    if not conn:
        return {"success": False, "error": "DB not configured"}
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM gardener_health_checkups
                WHERE plant_id = %s
                ORDER BY checked_at DESC
            """, (plant_id,))
            rows = cur.fetchall()
            return {"success": True, "checkups": [_dict_from_row(r) for r in rows]}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


# ─── Plant Guide Operations ───────────────────────────────────────────

def gardener_save_plant_guide(species: str, content: str, common_issues: list = None) -> dict:
    """Save or update a plant care guide."""
    conn = _get_connection()
    if not conn:
        return {"success": False, "error": "DB not configured"}
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO gardener_plant_guides (species, content, common_issues)
                VALUES (%s, %s, %s)
                ON CONFLICT (species) DO UPDATE SET
                    content = EXCLUDED.content,
                    common_issues = EXCLUDED.common_issues
                RETURNING *
            """, (species, content, json.dumps(common_issues or [])))
            row = cur.fetchone()
            conn.commit()
            return {"success": True, "guide": _dict_from_row(row)}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def gardener_get_plant_guide(species: str) -> dict:
    """Get a plant care guide by species."""
    conn = _get_connection()
    if not conn:
        return {"success": False, "error": "DB not configured"}
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM gardener_plant_guides WHERE species = %s", (species,))
            row = cur.fetchone()
            return {"success": True, "guide": _dict_from_row(row)} if row else {"success": False, "error": "Guide not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


# ─── Vacation Mode Operations ─────────────────────────────────────────

def gardener_set_vacation(hermes_user_id: str, start_date: str, end_date: str) -> dict:
    """Set vacation mode for a user."""
    conn = _get_connection()
    if not conn:
        return {"success": False, "error": "DB not configured"}
    
    result = gardener_get_user(hermes_user_id)
    if not result.get("success"):
        return result
    user_id = result["user"]["id"]
    
    try:
        with conn.cursor() as cur:
            # Deactivate any existing vacation
            cur.execute("""
                UPDATE gardener_vacation_mode 
                SET active = FALSE
                WHERE user_id = %s AND active = TRUE
            """, (user_id,))
            
            # Create new vacation
            cur.execute("""
                INSERT INTO gardener_vacation_mode (user_id, start_date, end_date, active)
                VALUES (%s, %s, %s, TRUE)
                RETURNING *
            """, (user_id, start_date, end_date))
            row = cur.fetchone()
            conn.commit()
            return {"success": True, "vacation": _dict_from_row(row)}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def gardener_end_vacation(hermes_user_id: str) -> dict:
    """End vacation mode for a user."""
    conn = _get_connection()
    if not conn:
        return {"success": False, "error": "DB not configured"}
    
    result = gardener_get_user(hermes_user_id)
    if not result.get("success"):
        return result
    user_id = result["user"]["id"]
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE gardener_vacation_mode 
                SET active = FALSE
                WHERE user_id = %s AND active = TRUE
                RETURNING *
            """, (user_id,))
            row = cur.fetchone()
            conn.commit()
            return {"success": True, "vacation": _dict_from_row(row)} if row else {"success": True, "message": "No active vacation"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


# ─── Helper Functions ──────────────────────────────────────────────────

def _get_current_season() -> str:
    """Get current season for Warsaw."""
    month = datetime.now().month
    if month in [12, 1, 2]:
        return "winter"
    elif month in [3, 4, 5]:
        return "spring"
    elif month in [6, 7, 8]:
        return "summer"
    else:
        return "autumn"


# ─── Tool Registration ─────────────────────────────────────────────────

def register_tools():
    """Register all gardener tools with the Hermes tool registry."""
    from tools.registry import registry
    
    tools = [
        ("gardener_init_schema", {"schema": "object"}, init_schema),
        ("gardener_upsert_user", {"schema": "object"}, gardener_upsert_user),
        ("gardener_get_user", {"schema": "object"}, gardener_get_user),
        ("gardener_add_plant", {"schema": "object"}, gardener_add_plant),
        ("gardener_get_plants", {"schema": "object"}, gardener_get_plants),
        ("gardener_archive_plant", {"schema": "object"}, gardener_archive_plant),
        ("gardener_update_plant_photos", {"schema": "object"}, gardener_update_plant_photos),
        ("gardener_set_care_schedule", {"schema": "object"}, gardener_set_care_schedule),
        ("gardener_get_due_care", {"schema": "object"}, gardener_get_due_care),
        ("gardener_log_care_event", {"schema": "object"}, gardener_log_care_event),
        ("gardener_create_reminder", {"schema": "object"}, gardener_create_reminder),
        ("gardener_confirm_reminder", {"schema": "object"}, gardener_confirm_reminder),
        ("gardener_save_checkup", {"schema": "object"}, gardener_save_checkup),
        ("gardener_resolve_checkup", {"schema": "object"}, gardener_resolve_checkup),
        ("gardener_get_checkup_history", {"schema": "object"}, gardener_get_checkup_history),
        ("gardener_save_plant_guide", {"schema": "object"}, gardener_save_plant_guide),
        ("gardener_get_plant_guide", {"schema": "object"}, gardener_get_plant_guide),
        ("gardener_set_vacation", {"schema": "object"}, gardener_set_vacation),
        ("gardener_end_vacation", {"schema": "object"}, gardener_end_vacation),
    ]
    
    for name, meta, handler in tools:
        registry.register(
            name=name,
            toolset="gardener",
            schema={"name": name, "description": f"Gardener: {name}", "parameters": meta["schema"]},
            handler=handler,
            check_fn=lambda: bool(os.environ.get("GARDENER_DB_URL")),
            requires_env=["GARDENER_DB_URL"],
        )


# Auto-register on import
try:
    register_tools()
except Exception:
    pass  # Will be registered when hermes loads