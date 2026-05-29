# Plant Guides — Filesystem Storage

Per-species care guides live as individual markdown files under `references/plants/`.

## Canonical template

Use **`references/plants/_TEMPLATE.md`** as the starting point for every new guide. Copy it, fill in the fields, save as `<species-slug>.md`. The template is ~150 lines and aims at **expert-level** care — it captures what an experienced grower would actually consult, not a generic intro.

Sections (fixed order — the agent grep-navigates these consistently):
1. **YAML frontmatter** — machine-readable: scientific name, family, origin, mature size, growth rate, full `care` block (water/light/lux/temp/humidity-pct/soil/pH/fertilizer NPK/repot/propagation), toxicity with active compound, dormancy pattern.
2. **Heading + one-sentence personality** — difficulty tier + signature trait or #1 killer.
3. **Care at a glance** — expanded one-liners covering light (with exposures + over/under signs), watering technique and quality, temperature with cold-damage signs, humidity with numeric % and method, soil with ratios and pH, fertilizer with NPK and salt-flush note, repotting cadence and pot-sizing rule, propagation method/season/timing, toxicity detail.
4. **Diagnostic decision tree** — top-down triage (moisture → light → pests → roots). Trains the agent to start with the highest-probability cause.
5. **Common issues** — `symptom → cause → action`, with multiple ranked causes per symptom (a/b/c) where a symptom is ambiguous (e.g. yellowing leaves).
6. **Pest playbook** — six common pests with identification cues + concrete treatment protocol.
7. **Seasonal calendar** — what to do each season (spring/summer/autumn/winter).
8. **Species-specific notes** — quirks, normal-but-alarming behaviors, cultivar differences, cultural triggers. 3-6 sentences.

## Module API (`tools/guides.py`)

```python
gardener_save_plant_guide(species: str, content: str, common_issues: list = None) -> dict
# Writes references/plants/<species-slug>.md.
# Pass the entire filled template as `content` — the function writes it verbatim.
# (The legacy `common_issues` kwarg auto-injects a frontmatter list and is deprecated;
#  fill the template yourself instead so the structure stays consistent.)

gardener_get_plant_guide(species: str) -> dict
# Case-insensitive lookup. Returns {success, guide: {species, content}}.

gardener_list_plant_guides() -> dict
# {success, guides: [name1, name2, ...]}
```

## Existing guides

- `yuca.md` — Yucca elephantipes (canonical example of the template filled in)
- `crassula-ovata.md` — Crassula ovata (Grubosz / Jade plant)
- `spathiphyllum-wallisii.md` — Spathiphyllum wallisii (Skrzydłokwiat / Peace lily)
- `phalaenopsis.md` — Phalaenopsis (Storczyk) — freshly added for "Storczyk Ani" (plant ID 11)

**NOTE for agents:** When adding a new plant via `gardener_add_plant`, check whether a guide for that species exists in `references/plants/`. If not, create it BEFORE confirming the add to the user — do not skip this step.

## Workflow for adding a new guide

1. `cp _TEMPLATE.md <species-slug>.md`
2. Fill frontmatter from Pl@ntNet result + targeted web research. Numeric fields (lux, humidity %, pH, NPK) need real sources — don't invent ranges.
3. Fill "Care at a glance" — every bullet has multiple sub-points; keep them tight but cover all of them. Drop a sub-point only if it genuinely doesn't apply (e.g. propagation for a sterile cultivar).
4. Fill "Diagnostic decision tree" — the universal version in the template is usually fine; customize step 1's moisture-test wording if the species has an unusual root system (e.g. epiphytes).
5. Fill "Common issues" with **ranked** causes (a/b/c) for ambiguous symptoms. Order by probability for *this* species, not in general.
6. Fill "Pest playbook" — keep the six universal pests; add a species-specific entry if there's a known pest magnet (e.g. African violets + cyclamen mites).
7. Fill "Seasonal calendar" — adjust to the plant's actual dormancy. Tropical evergreens without true dormancy still slow down in winter; note that explicitly.
8. Fill "Species-specific notes" with 3-6 sentences of expert tips a generalist guide would miss.

## Why filesystem over DB

DB TEXT columns truncate at ~10K chars; filesystem keeps guides arbitrarily long and lets the agent grep them. DB is reserved for structured records (plants, schedules, care events).
