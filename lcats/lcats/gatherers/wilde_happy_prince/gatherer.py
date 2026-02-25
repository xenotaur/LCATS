"""Corpus extractor for the Wilde stories."""

from lcats.gatherers import gatherlib


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


def gather():
    """Extract the Wilde stories from the Gutenberg Project."""
    gatherlib.gather(
        corpus="Wilde",
        target_directory=TARGET_DIRECTORY,
        description="Wilde stories from the Gutenberg Project.",
        license_text="Public domain, from Project Gutenberg.",
        author="Wilde",
        year=1888,
        headings=THE_HAPPY_PRINCE_HEADINGS,
        gutenberg_url=THE_HAPPY_PRINCE_GUTENBERG,
        paragraph_finder=find_paragraphs_happyprince,
    )


if __name__ == "__main__":
    gather()
