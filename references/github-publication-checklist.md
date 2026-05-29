# GitHub Publication Checklist (Gardening Skill)

Use this checklist before sharing the skill repository publicly.

## 1) Secrets and private data

- Replace all real credentials in examples with placeholders.
- Ensure `assets/example.env` contains only dummy values.
- Scan docs/references for household-specific identifiers (names, chat IDs, cron IDs, hostnames).

## 2) Portability

- Remove hardcoded absolute user paths (e.g. `/Users/<name>/...`).
- Prefer module-relative path discovery (`Path(__file__)`) and optional env overrides.
- Avoid machine-specific Python binary recommendations.

Recommended optional overrides:
- `GARDENER_ENV_PATH` for explicit env-file location.
- `GARDENING_SKILL_ROOT` when scripts are copied outside the skill tree.

## 3) No-S3 compatibility

- Keep core flows usable without object storage:
  - users, plants, schedules, care logs, reminders.
- Treat photo operations as optional when S3 vars are absent.
- Mark S3 env vars as optional in plugin metadata/docs if no-S3 mode is supported.

## 4) Plugin metadata consistency

- `plugin.json` examples must be generic (no private endpoints).
- If no-S3 mode exists, set S3 fields to `required: false`.
- Verify JSON parses cleanly.

## 5) Quick verification

- Run `py_compile` for edited Python files.
- Run a regex scan for sensitive markers (`/Users/`, token-like strings, private domains).
- Confirm docs and examples match runtime behavior (especially optional-vs-required env vars).
