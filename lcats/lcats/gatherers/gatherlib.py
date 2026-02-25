"""Gathering functions for files typical of Gutenberg corpora."""

from bs4 import BeautifulSoup
from lcats.gatherers import downloaders


DEFAULT_DIVISION_TAGS = ["h2", "div"]
DEFAULT_HEADING_TAGS = ["h2", "h3"]


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
):
    """Run DataGatherers for the a corpus."""
    if verbose:
        print(f"Gathering {corpus} stories from Gutenberg...")
    gatherer = downloaders.DataGatherer(
        target_directory,
        description=description,
        license=license_text,
    )
    for filename, heading, title in headings:
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
    if verbose:
        print(f" - Total stories in {corpus} corpus: {len(gatherer.downloads)}")
    return gatherer.downloads
