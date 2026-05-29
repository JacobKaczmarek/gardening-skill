# Gardening Skill for Hermes Agent

A portable Hermes skill for plant care workflows:
- plant identification via Pl@ntNet
- care schedules and care logs
- reminder generation
- optional photo storage on any S3-compatible backend

This package is publication-ready and intended to be shareable across machines/profiles.

## Contents

- `SKILL.md` — runtime behavior and operating rules
- `tools/` — DB, S3, Pl@ntNet, and analysis helpers
- `scripts/daily_reminders.py` — cron-friendly daily reminder payload generator
- `references/` — setup and architecture docs
- `assets/example.env` — safe env template
- `plugin.json` — plugin metadata and env var schema

## Requirements

- Hermes Agent
- Python 3.10+
- PostgreSQL database
- Pl@ntNet API key

Python dependencies used by the tools:
- `psycopg2`
- `requests`
- `boto3` (only needed for photo storage features)

## Install

Copy this folder into your profile skills directory:

`~/.hermes/profiles/<profile>/skills/gardening/`

Then start a new Hermes session or reload skills.

## Configuration

Copy `assets/example.env` values into your profile `.env` and fill placeholders.

Required:
- `GARDENER_DB_URL`
- `PLANTNET_API_KEY`

Optional (photo features):
- `GARDENER_S3_ENDPOINT`
- `GARDENER_S3_ACCESS_KEY`
- `GARDENER_S3_SECRET_KEY`
- `GARDENER_S3_BUCKET`
- `GARDENER_S3_REGION`

Legacy `GARDENER_MINIO_*` aliases are supported.

## No-S3 Mode

Works without S3 for core flows:
- users/plants/schedules
- care logs
- reminders

Unavailable without S3 credentials:
- photo upload/list/download/delete

## Notes

- The skill intentionally avoids hardcoded local absolute paths.
- `tools/bootstrap.py` supports env path overrides via `GARDENER_ENV_PATH`.
- `scripts/daily_reminders.py` supports skill-root override via `GARDENING_SKILL_ROOT`.

## Publish to GitHub

From this directory:

```bash
git init
git add .
git commit -m "feat: initial public gardening skill"
git branch -M main
git remote add origin https://github.com/<you>/gardening-skill.git
git push -u origin main
```
