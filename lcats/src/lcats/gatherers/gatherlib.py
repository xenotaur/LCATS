"""Gathering functions for files typical of Gutenberg corpora."""

import pathlib

from bs4 import BeautifulSoup
from lcats.gatherers import downloaders
from lcats.utils import names
from lcats.utils import run_log

DEFAULT_DIVISION_TAGS = ["h2", "div"]
DEFAULT_HEADING_TAGS = ["h2", "h3"]

# Outside data/ and corpora/ (both protected by run_log.RunLog's own
# re-validation) - "logs" is a plain sibling directory, relative to the
# current working directory like every other env-overridable root in
# lcats.utils.env (WI-RUNLOG-0082).
DEFAULT_GATHER_LOG_DIR = pathlib.Path("logs") / "gather"


def find_paragraphs(
    soup, start_heading_text, start_heading_tags=None, division_tags=None
):
    """Find paragraphs following a specific heading in a BeautifulSoup object."""
    # Use default tags if not provided
    start_heading_tags = (
        DEFAULT_HEADING_TAGS if start_heading_tags is None else start_heading_tags
    )
    division_tags = DEFAULT_DIVISION_TAGS if division_tags is None else division_tags

    # Find the start heading - this is brittle and may need to be adjusted for different stories
    start_heading = soup.find(
        lambda tag: tag.name in start_heading_tags
        and start_heading_text in tag.get_text(strip=True)
    )

    if start_heading is None:
        return None

    # If we got the heading, try to return the paragraphs following it
    paragraphs = []
    current_element = start_heading.find_next_sibling()

    # Iterate through sibling elements until the next heading or the end of the siblings is reached.
    while current_element and current_element.name not in division_tags:
        if current_element.name == "p" or current_element.name == "pre":
            paragraphs.append(current_element.get_text(strip=False))
        current_element = current_element.find_next_sibling()

    return "\n".join(paragraphs)


def create_download_callback(
    author,
    year,
    story_name,
    url,
    start_heading_text,
    description,
    paragraph_finder=find_paragraphs,
):
    """Create a download callback function for a specific story."""

    def story_download_callback(contents):
        """Download a specific  story from the Gutenberg Project."""

        if contents is None:
            raise ValueError(f"Failed to download {url}")

        story_soup = BeautifulSoup(contents, "lxml")

        story_text = paragraph_finder(story_soup, start_heading_text)
        if story_text is None:
            raise ValueError(
                f"Failed to find text for {story_name} given {start_heading_text} in {url}"
            )

        story_data = {
            "author": author,
            "year": year,
            "url": url,
            "name": story_name,
        }

        return description, story_text, story_data

    return story_download_callback


def gather(
    corpus,
    target_directory,
    description,
    license_text,
    author,
    year,
    headings,
    gutenberg_url,
    paragraph_finder=find_paragraphs,
    verbose=True,
    log_dir=DEFAULT_GATHER_LOG_DIR,
):
    """Run DataGatherers for a corpus.

    Wraps the download loop in a run_log.RunLog scope (log path
    ``<log_dir>/<corpus>_gather_run_log.jsonl``, outside the protected
    data/ tree that target_directory itself lives under) - a crash
    mid-run leaves a readable partial log of every story downloaded so
    far, closing the gap the other audited run-log sites shared before
    WI-RUNLOG-0078 (WI-RUNLOG-0082). No per-story exception isolation
    existed here before this change and none is added now (Non-Goal) -
    an unhandled download() failure still aborts the whole gather() call,
    now surfacing as run_aborted_unexpected via RunLog's own __exit__
    rather than a bare, unexplained traceback.
    """
    if verbose:
        print(f"Gathering {corpus} stories from Gutenberg...")
    gatherer = downloaders.DataGatherer(
        target_directory,
        description=description,
        license=license_text,
    )
    log_filename = f"{names.normalize_basename(corpus)[0]}_gather_run_log.jsonl"
    with run_log.RunLog(
        log_dir,
        log_filename,
        corpus=corpus,
        story_count=len(headings),
    ) as log:
        for raw_filename, heading, title in headings:
            filename = names.normalize_basename(raw_filename)[0]

            gatherer.download(
                filename,
                gutenberg_url,
                create_download_callback(
                    author=author,
                    year=year,
                    story_name=filename,
                    url=gutenberg_url,
                    start_heading_text=heading,
                    description=title,
                    paragraph_finder=paragraph_finder,
                ),
            )
            # download() only adds to gatherer.downloads when it actually
            # performed a fresh download (downloaders.py:239-279) - not
            # when the canonical file already existed and it skipped -
            # so this distinguishes the two without needing download()
            # itself to change its return contract (review finding, PR
            # #404).
            event = (
                "story_downloaded"
                if filename in gatherer.downloads
                else "story_skipped"
            )
            log.event(event, filename=filename, corpus=corpus)
    if verbose:
        print(f" - Total stories in {corpus} corpus: {len(gatherer.downloads)}")
    return gatherer.downloads
