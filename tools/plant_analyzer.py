"""
Gardener Plant Analyzer — vision prompts for plant identification & health.

Plant identification is handled by Pl@ntNet (see `plantnet.py`). This module
provides the canonical vision-LLM fallback prompt (`IDENTIFICATION_PROMPT` /
`get_identification_prompt`) used when Pl@ntNet fails and for species-targeted
health passes.
"""
from typing import List, Optional


# ─── Vision Prompts ────────────────────────────────────────────────────

IDENTIFICATION_PROMPT = """You are a botanist specialising in indoor houseplants. Identify the plant in the image and report your confidence honestly.

# Method (think step-by-step, then output JSON only)

1. **Observe visible features** — describe what you actually see: leaf shape (cordate, lanceolate, pinnate, fenestrated, etc.), leaf arrangement (alternate/opposite/whorled/rosette), leaf size and texture (waxy, matte, fuzzy, succulent), margin (entire, serrated, lobed), venation, colouration and variegation pattern, stem/petiole (woody, herbaceous, trailing, climbing), growth habit (upright, vining, rosette, tree-form), visible flowers/inflorescence, pot/substrate, approximate size relative to surroundings. Do NOT skip this step.
2. **Shortlist candidates** — list the 2–4 species most consistent with the observed features. For each, note which observations support it and which contradict it.
3. **Pick the best match** — choose the candidate with strongest support and fewest contradictions. Prefer common indoor houseplants (Monstera, Pothos, Sansevieria, Ficus spp., Spathiphyllum, ZZ, Calathea, Philodendron, Peperomia, succulents) when features fit, but do not force-fit.
4. **Calibrate confidence honestly** using this scale:
   - `0.95–1.00` — unmistakable, diagnostic features clearly visible (e.g. Monstera fenestrations, Sansevieria sword leaves)
   - `0.80–0.94` — strong match, all visible features fit, no contradictions
   - `0.60–0.79` — likely match but some features ambiguous or partially obscured
   - `0.40–0.59` — best guess; multiple plausible candidates remain
   - `<0.40` — cannot identify reliably (poor photo, atypical specimen, or unfamiliar species)
   Do not inflate confidence. If the photo is blurry, dark, shows only part of the plant, or lacks diagnostic features, say so and lower the score.
5. **Quick health pass** — note any visible problems: yellowing, browning tips/edges, leaf spots, wilting, etiolation, mushy/translucent leaves, visible pests (webbing, white fluff, scale), root issues if visible, soil condition.
6. **Recommend next step** — if confidence is below 0.80, list the specific photos or details that would disambiguate (e.g. "close-up of leaf underside", "photo of the stem/sap when broken", "is there milky latex?").

# Output

Return ONLY a JSON object, no prose before or after:

```json
{
  "observed_features": "<one paragraph describing what you actually see>",
  "candidates": [
    {"species": "<Genus species>", "common_name": "<name>", "supports": "<features matching>", "contradicts": "<features against>"},
    ...
  ],
  "best_match": {
    "species": "<Genus species or 'unknown'>",
    "common_name": "<common name or null>",
    "confidence": 0.0,
    "reasoning": "<why this is the best match>"
  },
  "image_quality": "good | partial | poor",
  "health": {
    "status": "healthy | warning | critical | unclear",
    "observations": ["<symptom 1>", "<symptom 2>"],
    "notes": "<short interpretation, or empty>"
  },
  "needs_more_info": ["<what additional photo or detail would raise confidence>"]
}
```

Rules:
- If you genuinely cannot tell, set `best_match.species` to `"unknown"` and `confidence` below 0.40. Do NOT guess to seem helpful.
- Use binomial scientific names (`Monstera deliciosa`, not just `Monstera`) when confidence ≥ 0.60.
- `observations` must be empty `[]` if the plant looks healthy; do not invent symptoms.
"""


def get_identification_prompt(suspected_species: Optional[str] = None,
                              known_issues: Optional[List[str]] = None) -> str:
    """Return the plant identification prompt, optionally augmented with prior beliefs.

    Pass `suspected_species` when the agent already has a hypothesis (e.g. from user
    text or a prior turn) so the model can verify rather than start from scratch.
    Pass `known_issues` (from references/plants/<species>.md) to direct the
    health pass at species-specific failure modes.
    """
    prompt = IDENTIFICATION_PROMPT
    if suspected_species:
        prompt += (
            f"\n# Prior hypothesis\n"
            f"The agent suspects this is **{suspected_species}**. "
            f"Verify or refute by checking diagnostic features. "
            f"If you disagree, say so explicitly in `best_match.reasoning` and lower confidence.\n"
        )
    if known_issues:
        issues_list = "\n".join(f"- {issue}" for issue in known_issues)
        prompt += (
            f"\n# Species-specific health checks\n"
            f"For this species, specifically check for:\n{issues_list}\n"
        )
    return prompt

