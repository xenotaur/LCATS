"""Gather single Gutenberg stories with explicit publication/review outcomes."""

import pathlib
import collections.abc

from tqdm import tqdm

from lcats.gatherers import downloaders
from lcats.gatherers import gather_result
from lcats.gatherers import parser
from lcats.gatherers import readiness
from lcats.gatherers import review_store
from lcats.gatherers.mass_quantities import storymap
from lcats.gettenberg import resources
from lcats.utils import run_log

DEFAULT_GATHER_LOG_DIR = pathlib.Path("logs") / "gather"
GATHER_LOG_FILENAME = "mass_quantities_gather_run_log.jsonl"


def gather(*, source, review_decisions=None):
    """Return all outcomes for the configured collection, including review needs."""
    return gather_stories(
        storymap.SINGLE_STORIES, source=source, review_decisions=review_decisions
    )


def gather_stories(
    stories, log_dir=DEFAULT_GATHER_LOG_DIR, *, source, review_decisions=None
):
    """Gather a batch and retain distinct, crash-visible per-source outcomes.

    Review candidates are stored below log_dir/review/mass_quantities, outside
    data/corpora. Cleanup refusal is a completed content outcome; operational
    errors and stale review decisions abort, leaving prior outputs/logs intact.
    Existing story outputs are reused, not requalified. The iterable need not
    have a length. Explicit review decisions must all refer to selected IDs.

    Args:
        stories: Iterable of Gutenberg IDs (at most 100000 entries).
        log_dir: Runtime working directory outside accepted data/corpora roots.
        source: Explicit GutenbergStorySource; caller owns its catalog lifetime.
        review_decisions: Optional mapping of ID to validated ReviewDecision.

    Returns:
        BatchResult retaining published, reused, ineligible, needs_review and
        cleanup_refused outcomes. It never labels all these outcomes successful.
    """
    if source is None:
        raise ValueError("an explicit GutenbergStorySource is required")
    # Resolve the full selection before I/O so unused/stale approvals are visible
    # instead of silently ignored. Bound materialization for accidental streams.
    selected = []
    for story in stories:
        if len(selected) >= 100000:
            raise ValueError("gather selection exceeds 100000 entries")
        selected.append(story)
    decisions = {} if review_decisions is None else review_decisions
    if not isinstance(decisions, collections.abc.Mapping):
        raise ValueError("review_decisions must be a mapping")
    if set(decisions) - set(selected):
        raise ValueError("review decisions contain IDs outside the selected collection")
    if any(
        type(key) is not int
        or not isinstance(value, readiness.ReviewDecision)
        or value.gutenberg_id != key
        for key, value in decisions.items()
    ):
        raise ValueError(
            "review decision mapping must match each decision Gutenberg ID"
        )
    gatherer = downloaders.DataGatherer(
        storymap.TARGET_DIRECTORY,
        description="Single stories from Gutenberg",
        license="Public domain, from Project Gutenberg.",
    )
    log_root = review_store.working_root(log_dir, data_root=gatherer.root)
    review_dir = log_root / "review" / "mass_quantities"
    outcomes = []
    # The runtime-root guard above also supports installed wheels without a
    # source pyproject.toml. It deliberately checks the actual output root before
    # opting out of RunLog's source-checkout-based guard; no unvalidated override.
    with run_log.RunLog(
        log_root,
        GATHER_LOG_FILENAME,
        story_count=len(selected),
        allow_protected_root=True,
    ) as log:
        for story in tqdm(selected):
            try:
                outcome = parser.gather_story(
                    gatherer,
                    story,
                    source=source,
                    review_decision=decisions.get(story),
                    review_dir=review_dir,
                )
            except resources.ResourceDecodeError as exc:
                if exc.code != "cleanup_refused":
                    raise
                outcome = gather_result.GatherResult(
                    story, "cleanup_refused", reason=str(exc)
                )
            outcomes.append(outcome)
            log.event("story_" + outcome.status, **outcome.to_dict())
    return gather_result.BatchResult(tuple(outcomes))


def main(*, source):
    """Report a batch without hiding exclusions or review requirements."""
    result = gather(source=source)
    print(f"Single-story gathering outcomes: {result.counts}")
    return result


if __name__ == "__main__":
    import sys
    from lcats import cli

    cli.main(["gather", "mass_quantities", *sys.argv[1:]])
