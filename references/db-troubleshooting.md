# Gardening DB Troubleshooting

## Quick health check

Run from profile root:

```bash
python3 -c "import sys; sys.path.insert(0, 'skills/gardening/tools'); from bootstrap import setup; setup(); from db import init_schema, gardener_get_plants; print(init_schema()); print(gardener_get_plants('demo-user'))"
```

Expected:
- `init_schema()` returns success
- `gardener_get_plants(...)` returns `{ "success": true, ... }`

## Common failures

### 1) Authentication failed

Symptom:
- `password authentication failed`

Cause:
- stale/rotated DB credentials

Fix:
- update `GARDENER_DB_URL` in profile env
- rerun quick health check

### 2) DSN parsing errors

Symptom:
- `invalid dsn` or connection option parsing issues

Fix:
- verify URL is complete and URL-encoded correctly
- compare against your provider's canonical connection string

### 3) Missing tables/columns after upgrade

Symptom:
- errors like `relation does not exist` or `column does not exist`

Fix:
- run `init_schema()` from latest `tools/db.py`
- if upgrading from old schema, follow `references/ownership-migration.md`

### 4) Zero due tasks unexpectedly

Symptom:
- reminders show no work despite expected watering

Checks:
- plant not archived
- care schedules exist and are active
- `next_due` is in the past/current time
- timezone assumptions are correct in your environment

### 5) User identity mismatch

Symptom:
- no plants returned for active user

Fix:
- inspect session identity with `gardener_get_current_identity()`
- ensure `gardener_upsert_user(...)` and routing identifiers were created for that communicator

## Safe debugging rules

- Do not print secrets in logs.
- Do not hardcode profile paths.
- Prefer minimal smoke calls over broad destructive SQL.
- Back up database before manual schema changes.