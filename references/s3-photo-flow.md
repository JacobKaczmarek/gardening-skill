# S3 Photo Flow Verification (communicator-agnostic)

Use this when users report "no photos uploaded" even though storage credentials are configured.

## What to verify

1. Runtime flow order
- Upload must happen before plant persistence:
  - `gardener_upload_photo(...)`
  - for new plants: pass returned URL into `gardener_add_plant(..., photo_url=..., baseline_photo_url=...)`
  - for existing plants: persist returned URL via `gardener_update_plant_photos(plant_id=..., photo_url=...)`
- If upload is skipped in flow logic, bucket remains empty even with healthy storage.
- If DB persist step is skipped, photo appears in bucket but plant record stays unchanged.

2. Storage health vs flow bug
- `gardener_list_photos(plant_id=<id>)` checks object presence.
- A successful direct smoke upload plus empty normal usage usually means flow integration bug, not S3 outage.

3. Minimal smoke pattern
- Upload tiny test image via `gardener_upload_photo(...)`
- Confirm object appears in `gardener_list_photos(...)`
- Delete test object with `gardener_delete_photo(...)`

4. Env naming compatibility
- Deployment may use legacy `GARDENER_MINIO_*` names.
- New `GARDENER_S3_*` aliases can coexist; keep fallback compatibility in tooling.

## Operator conclusion template

- "Storage backend is healthy. Missing photos were caused by add-plant flow not invoking upload before save."
- "Fix is to enforce upload-first sequence and pass returned URL into plant record."
