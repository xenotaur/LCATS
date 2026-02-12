"""Corpus extractor for the Wodehouse stories."""

from bs4 import BeautifulSoup

import lcats.gatherers.downloaders as downloaders


TARGET_DIRECTORY = "wodehouse"


TWO_LEFT_FEET_GUTENBERG = "https://www.gutenberg.org/cache/epub/7471/pg7471-images.html"


TWO_LEFT_FEET_HEADINGS = [
    ("bill_the_bloodhound", "BILL THE BLOODHOUND", "Wodehouse - Bill the Bloodhound"),
    (
        "extricating_young_gussie",
        "EXTRICATING YOUNG GUSSIE",
        "Wodehouse - Extricating Young Gussie",
    ),
    ("wilton's_holiday", "WILTON'S HOLIDAY", "Wodehouse - Wilton's Holiday"),
    ("mixer", "THE MIXER", "Wodehouse - The Mixer"),
    ("crowned_heads", "CROWNED HEADS", "Wodehouse - Crowned Heads"),
    ("at_geisenheimer's", "AT GEISENHEIMER'S", "Wodehouse - At Geisenheimer's"),
    ("making_of_mac's", "THE MAKING OF MAC'S", "Wodehouse - the Making Of Mac's"),
    ("one_touch_of_nature", "ONE TOUCH OF NATURE", "Wodehouse - One Touch Of Nature"),
    ("black_for_luck", "BLACK FOR LUCK", "Wodehouse - Black For Luck"),
    (
        "romance_of_an_ugly_policeman",
        "THE ROMANCE OF AN UGLY POLICEMAN",
        "Wodehouse - the Romance Of An Ugly Policeman",
    ),
    ("sea_of_troubles", "A SEA OF TROUBLES", "Wodehouse - a Sea Of Troubles"),
    (
        "man_with_two_left_feet",
        "THE MAN WITH TWO LEFT FEET",
        "Wodehouse - the Man With Two Left Feet",
    ),
]


def find_paragraphs_fourmillion(soup, start_heading_text):
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
        if current_element.name == "p":
            paragraphs.append(current_element.get_text(strip=False))
        current_element = current_element.find_next_sibling()

    return "\n".join(paragraphs)


def create_download_callback(story_name, url, start_heading_text, description):
    """Create a download callback function for a specific story."""

    def story_download_callback(contents):
        """Download a specific Wodehouse story from the Gutenberg Project."""

        if contents is None:
            raise ValueError(f"Failed to download {url}")

        story_soup = BeautifulSoup(contents, "lxml")

        story_text = find_paragraphs_fourmillion(story_soup, start_heading_text)
        if story_text is None:
            raise ValueError(
                f"Failed to find text for {story_name} given {start_heading_text} in {url}"
            )

        story_data = {
            "author": "Wodehouse",
            "year": 1917,
            "url": url,
            "name": story_name,
        }

        return description, story_text, story_data

    return story_download_callback


def gather():
    """Run DataGatherers for the Wodehouse corpus."""
    gatherer = downloaders.DataGatherer(
        TARGET_DIRECTORY,
        description="Wodehouse stories from the Gutenberg Project.",
        license="Public domain, from Project Gutenberg.",
    )
    for filename, heading, title in TWO_LEFT_FEET_HEADINGS:
        gatherer.download(
            filename,
            TWO_LEFT_FEET_GUTENBERG,
            create_download_callback(
                story_name=filename,
                url=TWO_LEFT_FEET_GUTENBERG,
                start_heading_text=heading,
                description=title,
            ),
        )
    return gatherer.downloads


def main():
    """Extract the Wodehouse stories from the Gutenberg Project."""
    print("Gathering Wodehouse stories.")
    downloads = gather()
    print(f" - Total stories in Wodehouse corpus: {len(downloads)}")


if __name__ == "__main__":
    main()
