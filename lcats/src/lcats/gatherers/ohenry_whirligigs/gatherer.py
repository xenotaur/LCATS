"""Corpus extractor for the OHenry stories."""

from lcats.gatherers import gatherlib

TARGET_DIRECTORY = "ohenry-whirligigs"
WHIRLIGIGS_GUTENBERG = "https://www.gutenberg.org/files/1595/1595-h/1595-h.htm"

# KMM Issues with some of the encodings
WHIRLIGIGS_HEADINGS = [
    ("world_and_the_door", "THE WORLD AND THE DOOR", "OHenry - the World And the Door"),
    (
        "theory_and_the_hound",
        "THE THEORY AND THE HOUND",
        "OHenry - the Theory And the Hound",
    ),
    (
        "hypotheses_of_failure",
        "THE HYPOTHESES OF FAILURE",
        "OHenry - the Hypotheses Of Failure",
    ),
    ("calloway’s_code", "CALLOWAY’S CODE", "OHenry - Calloway’s Code"),
    (
        "matter_of_mean_elevation",
        "A MATTER OF MEAN ELEVATION",
        "OHenry - a Matter Of Mean Elevation",
    ),
    ("“girl”", "“GIRL”", "OHenry - “girl”"),
    (
        "sociology_in_serge_and_straw",
        "SOCIOLOGY IN SERGE AND STRAW",
        "OHenry - Sociology In Serge And Straw",
    ),
    (
        "ransom_of_red_chief",
        "THE RANSOM OF RED CHIEF",
        "OHenry - the Ransom Of Red Chief",
    ),
    ("marry_month_of_may", "THE MARRY MONTH OF MAY", "OHenry - the Marry Month Of May"),
    ("technical_error", "A TECHNICAL ERROR", "OHenry - a Technical Error"),
    (
        "suite_homes_and_their_romance",
        "SUITE HOMES AND THEIR ROMANCE",
        "OHenry - Suite Homes And Their Romance",
    ),
    ("whirligig_of_life", "THE WHIRLIGIG OF LIFE", "OHenry - the Whirligig Of Life"),
    ("sacrifice_hit", "A SACRIFICE HIT", "OHenry - a Sacrifice Hit"),
    ("roads_we_take", "THE ROADS WE TAKE", "OHenry - the Roads We Take"),
    ("blackjack_bargainer", "A BLACKJACK BARGAINER", "OHenry - a Blackjack Bargainer"),
    (
        "song_and_the_sergeant",
        "THE SONG AND THE SERGEANT",
        "OHenry - the Song And the Sergeant",
    ),
    ("one_dollar’s_worth", "ONE DOLLAR’S WORTH", "OHenry - One Dollar’s Worth"),
    ("newspaper_story", "A NEWSPAPER STORY", "OHenry - a Newspaper Story"),
    ("tommy’s_burglar", "TOMMY’S BURGLAR", "OHenry - Tommy’s Burglar"),
    (
        "chaparral_christmas_gift",
        "A CHAPARRAL CHRISTMAS GIFT",
        "OHenry - a Chaparral Christmas Gift",
    ),
    ("little_local_colour", "A LITTLE LOCAL COLOUR", "OHenry - a Little Local Colour"),
    ("georgia’s_ruling", "GEORGIA’S RULING", "OHenry - Georgia’s Ruling"),
    ("blind_man’s_holiday", "BLIND MAN’S HOLIDAY", "OHenry - Blind Man’s Holiday"),
    (
        "madame_bo-peep,_of_the_ranches",
        "MADAME BO-PEEP, OF THE RANCHES",
        "OHenry - Madame Bo-peep, Of the Ranches",
    ),
]


def find_paragraphs_ohenry_whirligigs(soup, start_heading_text):
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
        year=1910,
        headings=WHIRLIGIGS_HEADINGS,
        gutenberg_url=WHIRLIGIGS_GUTENBERG,
        paragraph_finder=find_paragraphs_ohenry_whirligigs,
    )


if __name__ == "__main__":
    gather()
