"""Corpus extractor for the OHenry stories."""

from lcats.gatherers import gatherlib

TARGET_DIRECTORY = "ohenry-four_million"
FOUR_MILLION_GUTENBERG = "https://www.gutenberg.org/cache/epub/2776/pg2776-images.html"


# KMM Issues with some of the encodings
FOUR_MILLION_HEADINGS = [
    ("tobin's_palm", "TOBINâS PALM", "OHenry - Tobin’s Palm"),
    ("gift_of_the_magi", "THE GIFT OF THE MAGI", "OHenry - the Gift Of the Magi"),
    (
        "cosmopolite_in_a_cafe",
        "A COSMOPOLITE IN A CAFÃ",
        "OHenry - a Cosmopolite In a Café",
    ),
    ("between_rounds", "BETWEEN ROUNDS", "OHenry - Between Rounds"),
    ("skylight_room", "THE SKYLIGHT ROOM", "OHenry - the Skylight Room"),
    ("service_of_love", "A SERVICE OF LOVE", "OHenry - a Service Of Love"),
    (
        "coming-out_of_maggie",
        "THE COMING-OUT OF MAGGIE",
        "OHenry - the Coming-out Of Maggie",
    ),
    ("man_about_town", "MAN ABOUT TOWN", "OHenry - Man About Town"),
    ("cop_and_the_anthem", "THE COP AND THE ANTHEM", "OHenry - the Cop And the Anthem"),
    (
        "adjustment_of_nature",
        "AN ADJUSTMENT OF NATURE",
        "OHenry - An Adjustment Of Nature",
    ),
    (
        "memoirs_of_a_yellow_dog",
        "MEMOIRS OF A YELLOW DOG",
        "OHenry - Memoirs Of a Yellow Dog",
    ),
    (
        "love-philtre_of_ikey_schoenstein",
        "THE LOVE-PHILTRE OF IKEY SCHOENSTEIN",
        "OHenry - the Love-philtre Of Ikey Schoenstein",
    ),
    (
        "mammon_and_the_archer",
        "MAMMON AND THE ARCHER",
        "OHenry - Mammon And the Archer",
    ),
    (
        "springtime_a_la_carte",
        "SPRINGTIME Ã LA CARTE",
        "OHenry - Springtime À La Carte",
    ),
    ("green_door", "THE GREEN DOOR", "OHenry - the Green Door"),
    ("the_cabby's_seat", "FROM THE CABBYâS SEAT", "OHenry - From the Cabby’s Seat"),
    ("unfinished_story", "AN UNFINISHED STORY", "OHenry - An Unfinished Story"),
    (
        "caliph,_cupid_and_the_clock",
        "THE CALIPH, CUPID AND THE CLOCK",
        "OHenry - the Caliph, Cupid And the Clock",
    ),
    (
        "sisters_of_the_golden_circle",
        "SISTERS OF THE GOLDEN CIRCLE",
        "OHenry - Sisters Of the Golden Circle",
    ),
    (
        "romance_of_a_busy_broker",
        "THE ROMANCE OF A BUSY BROKER",
        "OHenry - the Romance Of a Busy Broker",
    ),
    ("after_twenty_years", "AFTER TWENTY YEARS", "OHenry - After Twenty Years"),
    ("lost_on_dress_parade", "LOST ON DRESS PARADE", "OHenry - Lost On Dress Parade"),
    ("by_courier", "BY COURIER", "OHenry - By Courier"),
    ("furnished_room", "THE FURNISHED ROOM", "OHenry - the Furnished Room"),
    (
        "brief_debut_of_tildy",
        "THE BRIEF DÃBUT OF TILDY",
        "OHenry - the Brief Début Of Tildy",
    ),
]


def find_paragraphs_ohenry_fourmillion(soup, start_heading_text):
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


def gather():
    """Extract the OHenry stories from the Gutenberg Project."""
    gatherlib.gather(
        corpus="OHenry",
        target_directory=TARGET_DIRECTORY,
        description="OHenry stories from the Gutenberg Project.",
        license_text="Public domain, from Project Gutenberg.",
        author="OHenry",
        year=1901,
        headings=FOUR_MILLION_HEADINGS,
        gutenberg_url=FOUR_MILLION_GUTENBERG,
        paragraph_finder=find_paragraphs_ohenry_fourmillion,
    )


if __name__ == "__main__":
    gather()
