"""Corpus extractor for the london stories."""

from bs4 import BeautifulSoup

import lcats.gatherers.downloaders as downloaders


TARGET_DIRECTORY = "london"


LONDON_GUTENBERG = 'https://www.gutenberg.org/cache/epub/710/pg710-images.html'


LONDON_HEADINGS = [
    ("love_of_life", "LOVE OF LIFE", "London - Love Of Life"),
    ("day's_lodging", "A DAYâS LODGING", "London - A Day's Lodging"),
    ("white_man's_way", "THE WHITE MANâS WAY", "London - The White Man's Way"),
    ("story_of_keesh", "THE STORY OF KEESH", "London - The Story Of Keesh"),
    ("unexpected", "THE UNEXPECTED", "London - The Unexpected"),
    ("brown_wolf", "BROWN WOLF", "London - Brown Wolf"),
    ("sun-dog_trail", "THE SUN-DOG TRAIL", "London - The Sun-dog Trail"),
    ("negore,_the_coward", "NEGORE, THE COWARD", "London - Negore, the Coward")
]


def find_paragraphs_london(soup, start_heading_text):
    """Find paragraphs following a specific heading in a BeautifulSoup object."""
    # Find the start heading - this is brittle and may need to be adjusted for different stories

    start_heading = soup.find(
        lambda tag: tag.name in ('h2', 'h3') and start_heading_text in tag.get_text(strip=True))

    if start_heading is None:
        return None

    # If we got the heading, try to return the paragraphs following it
    paragraphs = []
    # current_element = start_heading.find_next_sibling()
    current_element = start_heading.find_next()

    # Iterate through sibling elements until the next heading or the end of the siblings is reached.
    while current_element and current_element.name not in ('h2', 'div'):
        # print(current_element.name)
        if current_element.name == 'p' or current_element.name == 'pre':
            paragraphs.append(current_element.get_text(strip=False))
        current_element = current_element.find_next_sibling()

    return '\n'.join(paragraphs)


def create_download_callback(story_name, url, start_heading_text, description):
    """Create a download callback function for a specific story."""
    def story_download_callback(contents):
        """Download a specific london story from the Gutenberg Project."""

        if contents is None:
            raise ValueError(f"Failed to download {url}")

        story_soup = BeautifulSoup(contents, "lxml")

        story_text = find_paragraphs_london(story_soup, start_heading_text)
        if story_text is None:
            raise ValueError(
                f"Failed to find text for {story_name} given {start_heading_text} in {url}")

        story_data = {
            "author": "london",
            "year": 0,
            "url": url,
            "name": story_name,
        }

        return description, story_text, story_data

    return story_download_callback


def gather():
    """Run DataGatherers for the london corpus."""
    gatherer = downloaders.DataGatherer(
        TARGET_DIRECTORY,
        description="london stories from the Gutenberg Project.",
        license="Public domain, from Project Gutenberg.")
    for filename, heading, title in LONDON_HEADINGS:
        gatherer.download(
            filename,
            LONDON_GUTENBERG,
            create_download_callback(
                story_name=filename,
                url=LONDON_GUTENBERG,
                start_heading_text=heading,
                description=title))
    return gatherer.downloads


def main():
    """Extract the london stories from the Gutenberg Project."""
    print("Gathering london stories.")
    downloads = gather()
    print(f" - Total stories in London corpus: {len(downloads)}")


if __name__ == "__main__":
    main()
