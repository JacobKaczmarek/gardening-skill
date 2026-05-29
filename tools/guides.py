"""
Gardener Plant Guides — stored as local reference files in the skill directory.
"""
import os
import json
import re

SKILL_GUIDES_DIR = os.path.join(os.path.dirname(__file__), "..", "references", "plants")


def _species_to_filename(species: str) -> str:
    """Convert species name to filename."""
    # Lowercase, spaces to dashes, remove special chars
    name = species.lower().strip()
    name = re.sub(r"[^a-z0-9\s-]", "", name)
    name = re.sub(r"\s+", "-", name)
    return f"{name}.md"


def gardener_save_plant_guide(species: str, content: str, common_issues: list = None) -> dict:
    """Save a plant care guide as a local markdown file in references/plants/."""
    if not species:
        return {"success": False, "error": "Species is required"}

    os.makedirs(SKILL_GUIDES_DIR, exist_ok=True)
    filename = _species_to_filename(species)
    filepath = os.path.join(SKILL_GUIDES_DIR, filename)

    # Build frontmatter
    issues_text = ""
    if common_issues:
        issues_list = "\n".join(f"  - {issue}" for issue in common_issues)
        issues_text = f"\ncommon_issues:\n{issues_list}"

    frontmatter = f"---\nspecies: {species}{issues_text}\n---\n\n"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(frontmatter + content)

    return {"success": True, "guide_path": filepath}


def gardener_get_plant_guide(species: str) -> dict:
    """Read a plant care guide from local file."""
    if not species:
        return {"success": False, "error": "Species is required"}

    filename = _species_to_filename(species)
    filepath = os.path.join(SKILL_GUIDES_DIR, filename)

    if not os.path.exists(filepath):
        return {"success": False, "error": f"Guide not found for species: {species}"}

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Strip frontmatter for content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            content = parts[2].strip()

    return {"success": True, "guide": {"species": species, "content": content}}


def gardener_list_plant_guides() -> dict:
    """List all available plant guides."""
    os.makedirs(SKILL_GUIDES_DIR, exist_ok=True)
    guides = []
    for fname in os.listdir(SKILL_GUIDES_DIR):
        if fname.endswith(".md"):
            species = fname[:-3].replace("-", " ").title()
            guides.append(species)
    return {"success": True, "guides": guides}