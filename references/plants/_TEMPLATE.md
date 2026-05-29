---
species: <slug>                          # lowercase, hyphenated; matches filename
scientific_name: <Genus species>
common_names: [<name1>, <name2>]
origin: <native region>
family: <Botanical family>
mature_size: "<H>x<W> cm indoors"
growth_rate: <"slow" | "moderate" | "fast">
care:
  water_days: <int>                      # base interval; active growing season
  water_days_winter: <int>               # rest-period interval
  light: <"low" | "medium" | "bright-indirect" | "direct-sun">
  light_lux_min: <int>                   # minimum lux for sustained health
  temp_c: "<min>-<max>"                  # tolerated range
  temp_min_survivable: <int>             # below this = tissue damage or death
  humidity: <"low" | "average" | "high">
  humidity_pct: "<min>-<max>"
  soil: "<mix with ratios>"
  soil_ph: "<min>-<max>"
  fertilize: "<months>"
  fertilize_npk: "<balanced | high-N | bloom>"
  repot_years: <int>
  propagation: [<method1>, <method2>]
toxic_to_pets: <true | false>
toxicity_detail: "<active compound — symptoms>"
dormancy: <"winter-rest" | "none" | "summer-rest">
---

# <Common Name>

*<Scientific name>* — <one-sentence: difficulty tier + signature trait or #1 killer>.

## Care at a glance

- **Light:** <intensity + best window orientation>. Min <lux> lux. Too much: <symptom>. Too little: <symptom>.
- **Water:** every <N> days / <N-winter> days winter; <soak-and-dry | evenly moist>. Avoid watering into the crown. <tap OK | filtered water preferred>.
- **Temperature:** ideal <X–Y>°C; min survivable <Z>°C. Avoid <drafts/AC vents/cold glass>. Cold damage: <symptom>.
- **Humidity:** <level>, <min>–<max>%. <Any boosting method needed, or "standard indoor air is fine">. No misting — it doesn't raise ambient humidity and fosters rot/spotting.
- **Soil:** <mix + ratios>. pH <range>. Must drain freely; refresh top 2–3 cm annually.
- **Fertilize:** <months>, <NPK type> at half strength. None during dormancy. Flush soil with plain water every 3 months to prevent salt buildup.
- **Repotting:** every <N> years or when rootbound. Up-pot 2–3 cm only. Best: early spring.
- **Propagation:** <method + season + medium + weeks to root>.
- **Toxic to pets:** <yes/no — compound + key symptoms, or "non-toxic">.

## Common issues

Format: **symptom** → most-likely cause first → action.

- **Yellowing leaves** → overwatering (wet soil, multiple leaves at once): let dry, inspect roots for rot. / Natural ageing (one old leaf at a time): remove at base, normal.
- **Brown crispy tips** → low humidity or tap-water fluoride/chlorine: raise humidity, switch to filtered water. / Salt buildup: flush soil.
- **Wilting** → dry soil = thirsty, bottom-soak, recovers in hours. / Wet soil = root rot: unpot, cut rotten roots, repot in fresh dry mix.
- **Soft mushy tissue** → overwatering or fungal rot. Remove affected parts, improve airflow, reduce watering.
- **Leggy / pale / small new leaves** → insufficient light. Relocate or add grow light; rotate weekly.
- **<species-specific symptom>** → <cause> → <action>.

## Pest playbook

- **Spider mites** — fine webbing, stippled leaves. 70% isopropyl on cotton to leaf undersides; repeat every 4 days × 3 cycles. Raise humidity.
- **Mealybugs** — white cottony tufts in joints. Isopropyl swab per colony; heavy: systemic imidacloprid drench.
- **Fungus gnats** — flies near soil, larvae eat roots. Let top 3 cm dry; BTI drench; yellow sticky traps.
- **Scale** — brown bumps on stems. Scrape, then weekly neem oil. Severe: imidacloprid.
- **Thrips** — silver streaks, black frass. Spinosad spray every 5 days × 3 weeks; blue sticky traps.
- **Aphids** — clusters on new growth. Strong water jet; insecticidal soap.

## Seasonal calendar

- **Spring (Mar–May):** <key actions — repot window, resume fertiliser, propagation>.
- **Summer (Jun–Aug):** <peak care — watering cadence, outdoor move if applicable, pest watch>.
- **Autumn (Sep–Nov):** <taper — reduce water and fertiliser, move indoors if applicable>.
- **Winter (Dec–Feb):** <rest — extended watering interval, no fertiliser, light watch>.

## Species-specific notes

<2–4 sentences covering quirks that a generalist guide would miss: normal-but-alarming behaviours, propagation gotchas, cultivar differences, dormancy triggers, or toxicity caveats.>
