"""Corpus extractor for the Jack London stories."""

from lcats.gatherers import gatherlib


TARGET_DIRECTORY = "london"


LONDON_GUTENBERG = "https://www.gutenberg.org/cache/epub/710/pg710-images.html"


LONDON_HEADINGS = [
    ("love_of_life", "LOVE OF LIFE", "London - Love Of Life"),
    ("day's_lodging", "A DAYâS LODGING", "London - A Day's Lodging"),
    ("white_man's_way", "THE WHITE MANâS WAY", "London - The White Man's Way"),
    ("story_of_keesh", "THE STORY OF KEESH", "London - The Story Of Keesh"),
    ("unexpected", "THE UNEXPECTED", "London - The Unexpected"),
    ("brown_wolf", "BROWN WOLF", "London - Brown Wolf"),
    ("sun-dog_trail", "THE SUN-DOG TRAIL", "London - The Sun-dog Trail"),
    ("negore,_the_coward", "NEGORE, THE COWARD", "London - Negore, the Coward"),
]


def find_paragraphs_london(soup, start_heading_text):
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
    # current_element = start_heading.find_next_sibling()
    current_element = start_heading.find_next()

    # Iterate through elements until the next heading or the end of the siblings is reached.
    while current_element and current_element.name not in ("h2", "div"):
        # print(current_element.name)
        if current_element.name == "p" or current_element.name == "pre":
            paragraphs.append(current_element.get_text(strip=False))
        current_element = current_element.find_next_sibling()

    return "\n".join(paragraphs)


def gather():
    """Extract the Jack London stories from the Gutenberg Project."""
    gatherlib.gather(
        corpus="london",
        target_directory=TARGET_DIRECTORY,
        description="london stories from the Gutenberg Project.",
        license_text="Public domain, from Project Gutenberg.",
        author="london",
        year=0,
        headings=LONDON_HEADINGS,
        gutenberg_url=LONDON_GUTENBERG,
        paragraph_finder=find_paragraphs_london,
    )


if __name__ == "__main__":
    gather()
