# Ownership migration (normalized many-to-many)

Context:
- Goal: remove legacy `household_id` and `shared_with` while allowing multiple owners per plant.
- Runtime model: one Gardener profile = one household boundary.

Applied DB shape:
- Removed: `gardener_users.household_id`
- Removed: `gardener_plants.shared_with`
- Added: `gardener_plant_owners(plant_id, user_id, is_primary, created_at, PK(plant_id,user_id))`

Migration pattern:
1. Create `gardener_plant_owners` if missing.
2. Backfill primary owners from `gardener_plants.owner_id` with `is_primary=TRUE`.
3. If legacy `shared_with` exists, backfill extra owners with `is_primary=FALSE`.
4. Drop legacy index/columns.
5. Keep `gardener_plants.owner_id` as primary-owner compatibility field.

Code-level rules:
- For many owners, always use `gardener_plant_owners` (normalized relation).
- `owner_id` is attribution/primary owner, not visibility boundary.
- Do not reintroduce array-based sharing fields.

Fast validation checklist:
- `py_compile` on db tool file.
- Verify columns via `information_schema.columns`.
- Smoke run `gardener_get_plants` and `gardener_get_due_care`.
