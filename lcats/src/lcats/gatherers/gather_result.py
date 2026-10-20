"""Structured gather outcomes; content review is distinct from operational failure."""

import collections
import dataclasses


@dataclasses.dataclass(frozen=True, slots=True)
class GatherResult:
    """One completed source outcome; operational errors propagate separately."""

    gutenberg_id: int
    status: str
    path: str | None = None
    reason: str | None = None
    review_path: str | None = None

    def to_dict(self):
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True, slots=True)
class BatchResult:
    """All completed outcomes, including reused outputs that were not requalified."""

    outcomes: tuple[GatherResult, ...]

    @property
    def counts(self):
        return dict(collections.Counter(item.status for item in self.outcomes))

    @property
    def gathered(self):
        return {
            item.gutenberg_id: item.path
            for item in self.outcomes
            if item.path is not None
        }

    @property
    def requires_attention(self):
        return any(
            item.status in {"needs_review", "cleanup_refused"} for item in self.outcomes
        )

    def to_dict(self):
        return {
            "counts": self.counts,
            "outcomes": [item.to_dict() for item in self.outcomes],
        }
