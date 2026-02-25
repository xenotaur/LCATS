"""Gatherer for single stories from gutenberg"""

from tqdm import tqdm

from lcats.gatherers import downloaders
from lcats.gatherers.mass_quantities import storymap
from lcats.gatherers.mass_quantities import parser


def gather():
    """Extract all the "single stories" we have identified in the Gutenberg Project.

    Relies on the story definitions in storymap.py using the gather_stories function
    to do the actual work of extracting the stories and saving them in the data directory.

        This public-facing API does not return errors; it only returns successful stories
    as the downstream API cannot yet handle errors.

    Returns: A dictionary mapping story IDs to file paths.
    """
    gathered_stories, _ = gather_stories(storymap.SINGLE_STORIES)
    return gathered_stories


def gather_stories(stories):
    """Extract a set of stories from the Gutenberg Project.

    Uses the gather_story function to do the actual work of extracting the story.
    Returns two dictionaries, one for successfully gathered stories and one for errors.
    We will upgrade this to support more meaningful error handling in the future.

    Args:
        stories: A list of story IDs to extract from Gutenberg.
    Returns:
        A tuple of two dictionaries:
        - A dictionary mapping story IDs to file paths for successfully gathered stories.
        - A dictionary mapping story IDs to error messages for failed stories.
    """
    gatherer = downloaders.DataGatherer(
        storymap.TARGET_DIRECTORY,
        description="Single stories from Gutenberg",
        license="Public domain, from Project Gutenberg.",
    )

    gathered_stories = {}
    failed_stories = {}
    # stories = stories[:10]  # Limit to 10 for testing; remove or adjust as needed.
    for story in tqdm(stories):
        print(story)
        story, filename, error = parser.gather_story(gatherer, story)
        if filename:
            gathered_stories[story] = filename
        if error:
            failed_stories[story] = error

    return gathered_stories, failed_stories


def main():
    """Extract the Single stories from the Gutenberg Project."""
    print("Gathering single stories en masse from Gutenberg.")
    downloads, errors = gather_stories(storymap.SINGLE_STORIES)
    print(f" - Total stories in the single corpus: {len(downloads)}")
    print(f" - Total errors encountered: {len(errors)}")


if __name__ == "__main__":
    main()
