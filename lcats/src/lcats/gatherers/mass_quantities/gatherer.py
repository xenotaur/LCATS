"""Gatherer for single stories from gutenberg"""

import pathlib

from tqdm import tqdm

from lcats.gatherers import downloaders
from lcats.gatherers.mass_quantities import storymap
from lcats.gatherers import parser
from lcats.utils import run_log

# Outside data/ and corpora/ (both protected by run_log.RunLog's own
# re-validation) - matches gatherlib.gather()'s own DEFAULT_GATHER_LOG_DIR
# and <corpus>_gather_run_log.jsonl naming convention (WI-GATHER-0105).
DEFAULT_GATHER_LOG_DIR = pathlib.Path("logs") / "gather"
GATHER_LOG_FILENAME = "mass_quantities_gather_run_log.jsonl"


def gather(*, source):
    """Extract all the "single stories" we have identified in the Gutenberg Project.

    Relies on the story definitions in storymap.py using the gather_stories function
    to do the actual work of extracting the stories and saving them in the data directory.

    Returns successful stories; metadata/extraction skips are retained in the
    lower-level result. Operational source failures propagate and abort the run.

    Returns: A dictionary mapping story IDs to file paths.
    """
    if source is None:
        raise ValueError("an explicit GutenbergStorySource is required")
    gathered_stories, _ = gather_stories(storymap.SINGLE_STORIES, source=source)

    return gathered_stories


def gather_stories(stories, log_dir=DEFAULT_GATHER_LOG_DIR, *, source):
    """Extract a set of stories from the Gutenberg Project.

    Uses the gather_story function to do the actual work of extracting the story.
    Returns two dictionaries, one for successfully gathered stories and one for errors.
    We will upgrade this to support more meaningful error handling in the future.

    Wraps the loop in a run_log.RunLog scope (log path
    ``<log_dir>/mass_quantities_gather_run_log.jsonl``, outside the
    protected data/ tree the gathered stories themselves live under) -
    a crash mid-run leaves a readable partial log of every story
    processed so far (WI-GATHER-0105). This is scoped inside
    gather_stories() itself, not around one of its two independent
    callers (gather() and main()), so every invocation -- including
    direct calls, as this function's own tests make -- shares the same
    run-log lifecycle. Operational source failures propagate and record an aborted
    run; metadata/extraction skips retain per-story reasons. story_ready means
    written or reused, never falsely claiming an existing output was downloaded.

    Args:
        stories: A list of story IDs to extract from Gutenberg.
        log_dir: Working root for the run log (default: logs/gather).
        source: Explicit catalog-backed source; caller owns its catalog lifetime.
    Returns:
        A tuple of two dictionaries:
        - A dictionary mapping story IDs to file paths for successfully gathered stories.
        - A dictionary mapping story IDs to error messages for failed stories.
    """
    if source is None:
        raise ValueError("an explicit GutenbergStorySource is required")
    gatherer = downloaders.DataGatherer(
        storymap.TARGET_DIRECTORY,
        description="Single stories from Gutenberg",
        license="Public domain, from Project Gutenberg.",
    )

    gathered_stories = {}
    failed_stories = {}
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
    ) as log:
        # stories = stories[:10]  # Limit to 10 for testing; remove or adjust as needed.
        for story in tqdm(stories):
            # for story in tqdm(range(1, 79061)):
            # print(story)
            story, filename, error = parser.gather_story(gatherer, story, source=source)
            if filename:
                gathered_stories[story] = filename
            if error:
                failed_stories[story] = error
            event = "story_ready" if filename else "story_failed"
            log.event(event, story=story)

    return gathered_stories, failed_stories


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
