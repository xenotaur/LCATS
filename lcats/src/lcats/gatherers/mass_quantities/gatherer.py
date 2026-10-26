"""Gatherer for single stories from gutenberg"""

import dataclasses
import pathlib

from tqdm import tqdm

from lcats.gatherers import downloaders
from lcats.gatherers.mass_quantities import storymap
from lcats.gatherers import parser
from lcats.gettenberg import resources
from lcats.utils import env
from lcats.utils import paths
from lcats.utils import run_log

# Outside data/ and corpora/ (both protected by run_log.RunLog's own
# re-validation) - matches gatherlib.gather()'s own DEFAULT_GATHER_LOG_DIR
# and <corpus>_gather_run_log.jsonl naming convention (WI-GATHER-0105).
DEFAULT_GATHER_LOG_DIR = pathlib.Path("logs") / "gather"
GATHER_LOG_FILENAME = "mass_quantities_gather_run_log.jsonl"


def _log_directory(path):
    """Protect runtime data/corpora roots even outside a source checkout.

    The general RunLog guard discovers repository roots. Installed wheels need
    this additional check against the same environment roots used by gathering.
    This safety rule is retained from the separated review-store implementation;
    it does not require its editorial policy or candidate persistence machinery.
    """
    root = pathlib.Path(path).resolve()
    values = [env.data_root(), env.corpora_root()]
    try:
        anchor = paths.find_pyproject_root(__file__)
    except FileNotFoundError:
        pass  # A wheel has runtime roots, but no source checkout to protect.
    else:
        values.extend((anchor / env.data_root(), anchor / env.corpora_root()))
    for value in values:
        protected = pathlib.Path(value).resolve()
        if root == protected or protected in root.parents:
            raise ValueError(f"log directory must be outside data/corpora: {root}")
    return root


@dataclasses.dataclass(frozen=True)
class BatchResult:
    """Completed collection outcomes; ready includes new and reused files.

    Skips are ordinary metadata/body exclusions. Refusals mean cleanup could not
    safely delimit a source; they remain unresolved and make the run incomplete.
    Unavailable means the selected resource returned HTTP 404. Other operational
    exceptions propagate; missing resources are not ordinary eligibility skips.
    """

    ready: dict[int, str]
    skipped: dict[int, str]
    refused: dict[int, str]
    unavailable: dict[int, str] = dataclasses.field(default_factory=dict)

    @property
    def incomplete(self):
        """Whether unresolved content refusals or missing resources remain."""
        return bool(self.refused or self.unavailable)

    @property
    def summary(self):
        """Return counts without implying publication or editorial acceptance."""
        return (
            f"{len(self.ready)} ready (written or reused), "
            f"{len(self.skipped)} skipped, {len(self.refused)} cleanup refused, "
            f"{len(self.unavailable)} unavailable (HTTP 404)"
        )


def gather(*, source):
    """Gather the configured collection, retaining all completed outcomes."""
    return gather_batch(storymap.SINGLE_STORIES, source=source)


def gather_stories(stories, log_dir=DEFAULT_GATHER_LOG_DIR, *, source):
    """Return the historical (ready paths, error reasons) pair.

    Cleanup refusals and resource 404s continue and appear among errors. Use
    gather_batch() to distinguish skips, cleanup refusals and unavailable sources.
    Operational exceptions still propagate after preserving earlier outputs/logs.
    """
    result = gather_batch(stories, log_dir=log_dir, source=source)
    return result.ready, {**result.skipped, **result.refused, **result.unavailable}


def gather_batch(stories, log_dir=DEFAULT_GATHER_LOG_DIR, *, source):
    """Gather independently safe stories, recording refusals and resource 404s.

    Each completed input gets a run-log event. A cleanup_refused or HTTP 404 source
    is not published, but later inputs are attempted. Other source, decoding, integrity
    or filesystem failures propagate, preserving earlier files and an abort log.
    A run_end event means iteration finished, not that every input was accepted;
    the preceding batch_summary counts and returned result retain skips and
    unresolved refusals.

    Args:
        stories: Iterable of Gutenberg IDs, processed in the supplied order.
        log_dir: Log root outside protected data/corpora trees.
        source: Explicit catalog-backed source; caller owns its catalog lifetime.

    Returns:
        BatchResult with ready paths, skips, cleanup refusals and unavailable inputs.
    """
    if source is None:
        raise ValueError("an explicit GutenbergStorySource is required")
    log_dir = _log_directory(log_dir)
    gatherer = downloaders.DataGatherer(
        storymap.TARGET_DIRECTORY,
        description="Single stories from Gutenberg",
        license="Public domain, from Project Gutenberg.",
    )

    gathered_stories = {}
    failed_stories = {}
    refused_stories = {}
    unavailable_stories = {}
    try:
        story_count = len(stories)
    except TypeError:
        # stories may be any iterable (e.g. a generator, as the
        # commented-out range() alternatives below suggest) -- len()
        # only works on sized containers, and this logging addition
        # must not impose a new requirement the loop itself doesn't
        # need (review finding, PR #426).
        story_count = None
    with run_log.RunLog(
        log_dir,
        GATHER_LOG_FILENAME,
        story_count=story_count,
        # Both runtime and available checkout roots were independently checked.
        allow_protected_root=True,
    ) as log:
        # stories = stories[:10]  # Limit to 10 for testing; remove or adjust as needed.
        for story in tqdm(stories):
            # for story in tqdm(range(1, 79061)):
            # print(story)
            try:
                story, filename, error = parser.gather_story(
                    gatherer, story, source=source
                )
            except resources.ResourceTransportError as exc:
                if exc.code != "http_status" or exc.status != 404:
                    raise
                # Only a confirmed missing representation is local to this input.
                # Do not retry it, guess alternatives, or hide other failures.
                unavailable_stories[story] = str(exc)
                log.event(
                    "story_source_unavailable",
                    story=story,
                    reason=str(exc),
                    http_status=exc.status,
                    source_uri=exc.source_uri,
                    request_url=exc.request_url,
                    final_url=exc.final_url,
                )
                continue
            except resources.ResourceDecodeError as exc:
                if exc.code != "cleanup_refused":
                    raise
                # A content refusal is local to this input, not an operational
                # failure of the collection. Never publish or silently retry it.
                refused_stories[story] = str(exc)
                log.event("story_cleanup_refused", story=story, reason=str(exc))
                continue
            if filename:
                gathered_stories[story] = filename
            if error:
                failed_stories[story] = error
            event = "story_ready" if filename else "story_failed"
            log.event(event, story=story)

        log.event(
            "batch_summary",
            ready=len(gathered_stories),
            skipped=len(failed_stories),
            refused=len(refused_stories),
            unavailable=len(unavailable_stories),
            incomplete=bool(refused_stories or unavailable_stories),
        )
    return BatchResult(
        gathered_stories, failed_stories, refused_stories, unavailable_stories
    )


def main(*, source):
    """Extract the Single stories from the Gutenberg Project."""
    print("Gathering single stories en masse from Gutenberg.")
    downloads, errors = gather_stories(storymap.SINGLE_STORIES, source=source)
    # downloads, errors = gather_stories(range(1, 78290))
    print(f" - Total stories in the single corpus: {len(downloads)}")
    print(f" - Total errors encountered: {len(errors)}")


if __name__ == "__main__":
    import sys
    from lcats import cli

    cli.main(["gather", "mass_quantities", *sys.argv[1:]])
