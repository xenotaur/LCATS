"""Corpus extractor for the Anderson stories."""

from lcats.gatherers import gatherlib


TARGET_DIRECTORY = "anderson"


ANDERSON_GUTENBERG = "https://www.gutenberg.org/cache/epub/1597/pg1597-images.html"


ANDERSON_HEADINGS = [
    (
        "emperor's_new_clothes",
        "THE EMPEROR'S NEW CLOTHES",
        "Anderson - The Emperor's New Clothes",
    ),
    ("swineherd", "THE SWINEHERD", "Anderson - The Swineherd"),
    ("real_princess", "THE REAL PRINCESS", "Anderson - The Real Princess"),
    ("shoes_of_fortune", "THE SHOES OF FORTUNE", "Anderson - The Shoes Of Fortune"),
    ("fir_tree", "THE FIR TREE", "Anderson - The Fir Tree"),
    ("snow_queen", "THE SNOW QUEEN", "Anderson - The Snow Queen"),
    ("leap-frog", "THE LEAP-FROG", "Anderson - The Leap-frog"),
    ("elderbush", "THE ELDERBUSH", "Anderson - The Elderbush"),
    ("bell", "THE BELL", "Anderson - The Bell"),
    ("old_house", "THE OLD HOUSE", "Anderson - The Old House"),
    ("happy_family", "THE HAPPY FAMILY", "Anderson - The Happy Family"),
    ("story_of_a_mother", "THE STORY OF A MOTHER", "Anderson - The Story Of a Mother"),
    ("false_collar", "THE FALSE COLLAR", "Anderson - The False Collar"),
    ("shadow", "THE SHADOW", "Anderson - The Shadow"),
    ("little_match_girl", "THE LITTLE MATCH GIRL", "Anderson - The Little Match Girl"),
    (
        "dream_of_little_tuk",
        "THE DREAM OF LITTLE TUK",
        "Anderson - The Dream Of Little Tuk",
    ),
    ("naughty_boy", "THE NAUGHTY BOY", "Anderson - The Naughty Boy"),
    ("red_shoes", "THE RED SHOES", "Anderson - The Red Shoes"),
]


def gather():
    """Extract the Anderson stories from the Gutenberg Project."""
    gatherlib.gather(
        corpus="Anderson",
        target_directory=TARGET_DIRECTORY,
        description="Anderson stories from the Gutenberg Project.",
        license_text="Public domain, from Project Gutenberg.",
        author="Anderson",
        year=1911,
        headings=ANDERSON_HEADINGS,
        gutenberg_url=ANDERSON_GUTENBERG,
    )


if __name__ == "__main__":
    gather()
