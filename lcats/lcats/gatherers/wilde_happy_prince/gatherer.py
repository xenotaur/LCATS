"""Corpus extractor for the Wilde stories."""

from bs4 import BeautifulSoup

import lcats.gatherers.downloaders as downloaders


TARGET_DIRECTORY = "wilde_happy_prince"


THE_HAPPY_PRINCE_GUTENBERG = (
    "https://www.gutenberg.org/cache/epub/902/pg902-images.html"
)


THE_HAPPY_PRINCE_HEADINGS = [
    ("happy_prince", "The Happy Prince", "Wilde - the Happy Prince"),
    (
        "nightingale_and_the_rose",
        "The Nightingale and the Rose",
        "Wilde - the Nightingale And the Rose",
    ),
    ("selfish_giant", "The Selfish Giant", "Wilde - the Selfish Giant"),
    ("devoted_friend", "The Devoted Friend", "Wilde - the Devoted Friend"),
    ("remarkable_rocket", "The Remarkable Rocket", "Wilde - the Remarkable Rocket"),
]


def find_paragraphs_happyprince(soup, start_heading_text):
    """Find paragraphs following a specific heading in a BeautifulSoup object."""

    # Find the start heading - this is brittle and may need to be adjusted for different stories
    start_heading = soup.find(
        lambda tag: tag.name in ("h2", "h3")
        and (start_heading_text + ".") in tag.get_text(strip=True)
    )

    if start_heading is None:
        return None

    # If we got the heading, try to return the paragraphs following it
    paragraphs = []
    current_element = start_heading.find_next_sibling()

    # Iterate through sibling elements until the next heading or the end of the siblings is reached.
    while current_element and current_element.name not in ("h2", "div"):
        if current_element.name == "p" or current_element.name == "table":
            paragraphs.append(current_element.get_text(strip=False))
        current_element = current_element.find_next_sibling()

    return "\n".join(paragraphs)


def create_download_callback(story_name, url, start_heading_text, description):
    """Create a download callback function for a specific story."""

    def story_download_callback(contents):
        """Download a specific Wilde story from the Gutenberg Project."""

        if contents is None:
            raise ValueError(f"Failed to download {url}")

        story_soup = BeautifulSoup(contents, "lxml")

        story_text = find_paragraphs_happyprince(story_soup, start_heading_text)
        if story_text is None:
            raise ValueError(
                f"Failed to find text for {story_name} given {start_heading_text} in {url}"
            )

        story_data = {
            "author": "Wilde",
            "year": 1888,
            "url": url,
            "name": story_name,
        }

        return description, story_text, story_data

    return story_download_callback


def gather():
    """Run DataGatherers for the Wilde corpus."""
    gatherer = downloaders.DataGatherer(
        TARGET_DIRECTORY,
        description="Wilde stories from the Gutenberg Project.",
        license="Public domain, from Project Gutenberg.",
    )
    for filename, heading, title in THE_HAPPY_PRINCE_HEADINGS:
        gatherer.download(
            filename,
            THE_HAPPY_PRINCE_GUTENBERG,
            create_download_callback(
                story_name=filename,
                url=THE_HAPPY_PRINCE_GUTENBERG,
                start_heading_text=heading,
                description=title,
            ),
        )
    return gatherer.downloads


def main():
    """Extract the Wilde stories from the Gutenberg Project."""
    print("Gathering Wilde stories.")
    downloads = gather()
    print(f" - Total stories in Wilde corpus: {len(downloads)}")


if __name__ == "__main__":
    main()
