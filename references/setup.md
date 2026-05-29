# Gardening Skill Setup (Open Source)

This reference covers a portable setup for any Hermes profile.

## 1) Install skill files

Place the skill under your profile (or external skills dir):

- `~/.hermes/profiles/<profile>/skills/gardening/`

Expected structure:

```
skills/gardening/
├── SKILL.md
├── tools/
│   ├── db.py
│   ├── s3.py
│   ├── plantnet.py
│   └── plant_analyzer.py
├── scripts/
│   └── daily_reminders.py
├── references/
└── assets/
    └── example.env
```

## 2) Configure environment

Use `assets/example.env` as template.

Required variables:
- `GARDENER_DB_URL`
- `PLANTNET_API_KEY`

Optional (only for photo storage features):
- S3-compatible storage (either naming scheme):
  - Preferred: `GARDENER_S3_ENDPOINT`, `GARDENER_S3_ACCESS_KEY`, `GARDENER_S3_SECRET_KEY`, `GARDENER_S3_BUCKET`
  - Backward-compatible: `GARDENER_MINIO_ENDPOINT`, `GARDENER_MINIO_ACCESS_KEY`, `GARDENER_MINIO_SECRET_KEY`, `GARDENER_MINIO_BUCKET`

No-S3 mode:
- If S3 vars are unset, core flows still work (plants, schedules, care logs, reminders).
- Photo upload/list/download/delete features are disabled.

Notes:
- Never commit real credentials.
- Keep profile `.env` private.

## 3) Validate runtime basics

- Hermes model/provider is configured (`hermes config show`)
- Gateway is running (`hermes gateway status`)
- Required tools are available: `terminal`, `file`, `web`, `vision`, `send_message`

## 4) Initialize database schema

Run a small smoke check from the profile:

```bash
python3 -c "import sys; sys.path.insert(0, 'skills/gardening/tools'); from bootstrap import setup; setup(); from db import init_schema; print(init_schema())"
```

## 5) Reminder job model

Recommended daily reminder pattern:

- Script: `scripts/daily_reminders.py`
- Script outputs JSON facts only (`tasks`, `recipients`)
- Agent writes natural wording and explicitly fans out with `send_message`
- Avoid broadcast-style delivery for per-user reminders

## 6) Vision routing recommendation

Plant identification must use Pl@ntNet (`gardener_identify_plant`).
`vision_analyze` is for health/context analysis only.

If your default model lacks image input, set an auxiliary vision model in Hermes config.

## 7) Portability checklist

- No hardcoded absolute paths in docs/scripts
- No profile-specific IDs in references
- No communicator-specific assumptions in core flow
- Confirmation workflow is text-based (`ok`, `done`, equivalent)
