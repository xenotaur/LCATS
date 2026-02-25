"""Corpus extractor for the Sherlock Holmes stories."""

from bs4 import BeautifulSoup

import lcats.gatherers.downloaders as downloaders


TARGET_DIRECTORY = "sherlock"


ADVENTURES_GUTENBERG = "https://www.gutenberg.org/files/1661/1661-h/1661-h.htm"
ADVENTURES_HEADINGS = [
    (
        "scandal_in_bohemia",
        "A SCANDAL IN BOHEMIA",
        "Sherlock Holmes - A Scandal in Bohemia",
    ),
    (
        "red_headed_league",
        "THE RED-HEADED LEAGUE",
        "Sherlock Holmes - The Red-Headed League",
    ),
    ("case_of_identity", "A CASE OF IDENTITY", "Sherlock Holmes - A Case of Identity"),
    (
        "boscombe_valley",
        "THE BOSCOMBE VALLEY MYSTERY",
        "Sherlock Holmes - The Boscombe Valley Mystery",
    ),
    (
        "five_orange_pips",
        "THE FIVE ORANGE PIPS",
        "Sherlock Holmes - The Five Orange Pips",
    ),
    (
        "twisted_lip",
        "THE MAN WITH THE TWISTED LIP",
        "Sherlock Holmes - The Man with the Twisted Lip",
    ),
    (
        "blue_carbuncle",
        "THE ADVENTURE OF THE BLUE CARBUNCLE",
        "Sherlock Holmes - The Adventure of the Blue Carbuncle",
    ),
    (
        "speckled_band",
        "THE ADVENTURE OF THE SPECKLED BAND",
        "Sherlock Holmes - The Adventure of the Speckled Band",
    ),
    (
        "engineers_thumb",
        "THE ADVENTURE OF THE ENGINEER’S THUMB",
        "Sherlock Holmes - The Adventure of the Engineer's Thumb",
    ),
    (
        "noble_bachelor",
        "THE ADVENTURE OF THE NOBLE BACHELOR",
        "Sherlock Holmes - The Adventure of the Noble Bachelor",
    ),
    (
        "beryl_coronet",
        "THE ADVENTURE OF THE BERYL CORONET",
        "Sherlock Holmes - The Adventure of the Beryl Coronet",
    ),
    (
        "copper_beeches",
        "THE ADVENTURE OF THE COPPER BEECHES",
        "Sherlock Holmes - The Adventure of the Copper Beeches",
    ),
]


def find_paragraphs_adventures(soup, start_heading_text):
    """Find paragraphs following a specific heading in a BeautifulSoup object."""
    # Find the start heading - this is brittle and may need to be adjusted for different stories.
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
        if current_element.name == "p":
            paragraphs.append(current_element.get_text(strip=False))
        current_element = current_element.find_next_sibling()

    return "\n".join(paragraphs)


def create_download_callback(story_name, url, start_heading_text, description):
    """Create a download callback function for a specific story."""

    def story_download_callback(contents):
        """Download a specific Sherlock story from the Gutenberg Project."""
        if contents is None:
            raise ValueError(f"Failed to download {url}")

        story_soup = BeautifulSoup(contents, "lxml")

        story_text = find_paragraphs_adventures(story_soup, start_heading_text)
        if story_text is None:
            raise ValueError(
                f"Failed to find text for {story_name} given {start_heading_text} in {url}"
            )

        story_data = {
            "author": "Arthur Conan Doyle",
            "year": 1891,
            "url": url,
            "name": story_name,
        }

        return description, story_text, story_data

    return story_download_callback


def gather():
    """Run DataGatherers for the Sherlock Holmes corpus."""
    gatherer = downloaders.DataGatherer(
        TARGET_DIRECTORY,
        description="Sherlock Holmes stories from the Gutenberg Project.",
        license="Public domain, from Project Gutenberg.",
    )
    for filename, heading, title in ADVENTURES_HEADINGS:
        gatherer.download(
            filename,
            ADVENTURES_GUTENBERG,
            create_download_callback(
                story_name=filename,
                url=ADVENTURES_GUTENBERG,
                start_heading_text=heading,
                description=title,
            ),
        )
    return gatherer.downloads


def main():
    """Extract the Sherlock Holmes stories from the Gutenberg Project."""
    print("Gathering Sherlock Holmes stories.")
    downloads = gather()
    print(f" - Total stories in Sherlock corpus: {len(downloads)}")


if __name__ == "__main__":
    main()
