"""Corpus extractor for the Chesterton stories."""

from bs4 import BeautifulSoup

import lcats.gatherers.downloaders as downloaders


TARGET_DIRECTORY = "chesterton"


CHESTERTON_GUTENBERG = "https://www.gutenberg.org/files/204/204-h/204-h.htm"


CHESTERTON_HEADINGS = [
    ("blue_cross", "The Blue Cross", "Chesterton - The Blue Cross"),
    ("secret_garden", "The Secret Garden", "Chesterton - The Secret Garden"),
    ("queer_feet", "The Queer Feet", "Chesterton - The Queer Feet"),
    ("flying_stars", "The Flying Stars", "Chesterton - The Flying Stars"),
    ("invisible_man", "The Invisible Man", "Chesterton - The Invisible Man"),
    (
        "honour_of_israel_gow",
        "The Honour of Israel Gow",
        "Chesterton - The Honour Of Israel Gow",
    ),
    ("wrong_shape", "The Wrong Shape", "Chesterton - The Wrong Shape"),
    (
        "sins_of_prince_saradine",
        "The Sins of Prince Saradine",
        "Chesterton - The Sins Of Prince Saradine",
    ),
    ("hammer_of_god", "The Hammer of God", "Chesterton - The Hammer Of God"),
    ("eye_of_apollo", "The Eye of Apollo", "Chesterton - The Eye Of Apollo"),
    (
        "sign_of_the_broken_sword",
        "The Sign of the Broken Sword",
        "Chesterton - The Sign Of the Broken Sword",
    ),
    (
        "three_tools_of_death",
        "The Three Tools of Death",
        "Chesterton - The Three Tools Of Death",
    ),
]


def find_paragraphs_chesterton(soup, start_heading_text):
    """Find paragraphs following a specific heading in a BeautifulSoup object."""

    # Find the start heading - this is brittle and may need to be adjusted for different stories
    start_heading = soup.find(
        lambda tag: tag.name in ("h2", "h3")
        and start_heading_text in tag.get_text(strip=True)
    )

    if start_heading is None:
        return None

    # If we got the heading, try to return the paragraphs following it
    paragraphs = []
    current_element = start_heading.find_next_sibling()

    # Iterate through sibling elements until the next heading or the end of the siblings is reached.
    while current_element and current_element.name not in ("h2", "div"):
        if current_element.name == "p" or current_element.name == "pre":
            paragraphs.append(current_element.get_text(strip=False))
        current_element = current_element.find_next_sibling()

    return "\n".join(paragraphs)


def create_download_callback(story_name, url, start_heading_text, description):
    """Create a download callback function for a specific story."""

    def story_download_callback(contents):
        """Download a specific Chesterton story from the Gutenberg Project."""

        if contents is None:
            raise ValueError(f"Failed to download {url}")

        story_soup = BeautifulSoup(contents, "lxml")

        story_text = find_paragraphs_chesterton(story_soup, start_heading_text)
        if story_text is None:
            raise ValueError(
                f"Failed to find text for {story_name} given {start_heading_text} in {url}"
            )

        story_data = {
            "author": "Chesterton",
            "year": 0,
            "url": url,
            "name": story_name,
        }

        return description, story_text, story_data

    return story_download_callback


def gather():
    """Run DataGatherers for the Chesterton corpus."""
    gatherer = downloaders.DataGatherer(
        TARGET_DIRECTORY,
        description="Chesterton stories from the Gutenberg Project.",
        license="Public domain, from Project Gutenberg.",
    )
    for filename, heading, title in CHESTERTON_HEADINGS:
        gatherer.download(
            filename,
            CHESTERTON_GUTENBERG,
            create_download_callback(
                story_name=filename,
                url=CHESTERTON_GUTENBERG,
                start_heading_text=heading,
                description=title,
            ),
        )
    return gatherer.downloads


def main():
    """Extract the Chesterton stories from the Gutenberg Project."""
    print("Gathering Chesterton stories.")
    downloads = gather()
    print(f" - Total stories in Chesterton corpus: {len(downloads)}")


if __name__ == "__main__":
    main()
