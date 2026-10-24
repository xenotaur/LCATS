"""Explicit collection requirements, without loading executable gatherers."""

import dataclasses


@dataclasses.dataclass(frozen=True, slots=True)
class CollectionRequirement:
    """Describe source identity and metadata use independently.

    Fixed URLs and local files may optionally need metadata for discovery or
    enrichment. Source type alone never implies catalog setup. These records do
    not load plugins or claim that the selected consumer has been migrated.
    """

    name: str
    source_type: str
    catalog_use: str = "none"

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("collection name must be nonempty")
        if self.source_type not in ("local", "fixed_url", "gutenberg"):
            raise ValueError("unknown source type")
        if self.catalog_use not in ("none", "discovery", "enrichment"):
            raise ValueError("unknown catalog use")

    @property
    def needs_catalog(self):
        """Whether this workflow explicitly depends on metadata."""
        return self.catalog_use != "none"


NAMES = (
    "sherlock",
    "lovecraft",
    "ohenry_four_million",
    "ohenry_whirligigs",
    "hemingway",
    "wilde_happy_prince",
    "wodehouse",
    "grimm",
    "anderson",
    "chesterton",
    "london",
    "mass_quantities",
)
REQUIREMENTS = {
    name: CollectionRequirement(
        name,
        "gutenberg" if name == "mass_quantities" else "fixed_url",
        "enrichment" if name == "mass_quantities" else "none",
    )
    for name in NAMES
}


def select(names=None):
    """Validate the entire selection before any gatherer can execute.

    Preserve caller order and duplicates for compatibility. Empty selection means
    all built-in collections. Counts describe collections, never inferred stories.
    """
    selected = tuple(names) if names else NAMES
    unknown = [name for name in selected if name not in REQUIREMENTS]
    if unknown:
        raise ValueError("Unknown gatherer(s): " + ", ".join(unknown))
    return tuple(REQUIREMENTS[name] for name in selected)
