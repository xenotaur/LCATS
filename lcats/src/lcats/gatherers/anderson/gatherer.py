"""Corpus extractor for the Anderson stories."""

from lcats.gatherers import gatherlib

TARGET_DIRECTORY = "anderson"


ANDERSON_GUTENBERG = "https://www.gutenberg.org/cache/epub/1597/pg1597-images.html"


ANDERSON_HEADINGS = [
    (
        "the_emperor's_new_clothes",
        "THE EMPEROR'S NEW CLOTHES",
        "Anderson - The Emperor's New Clothes",
    ),
    ("the_swineherd", "THE SWINEHERD", "Anderson - The Swineherd"),
    ("the_real_princess", "THE REAL PRINCESS", "Anderson - The Real Princess"),
    ("the_shoes_of_fortune", "THE SHOES OF FORTUNE", "Anderson - The Shoes Of Fortune"),
    ("the_fir_tree", "THE FIR TREE", "Anderson - The Fir Tree"),
    ("the_snow_queen", "THE SNOW QUEEN", "Anderson - The Snow Queen"),
    ("the_leap-frog", "THE LEAP-FROG", "Anderson - The Leap-frog"),
    ("the_elderbush", "THE ELDERBUSH", "Anderson - The Elderbush"),
    ("the_bell", "THE BELL", "Anderson - The Bell"),
    ("the_old_house", "THE OLD HOUSE", "Anderson - The Old House"),
    ("the_happy_family", "THE HAPPY FAMILY", "Anderson - The Happy Family"),
    (
        "the_story_of_a_mother",
        "THE STORY OF A MOTHER",
        "Anderson - The Story Of a Mother",
    ),
    ("the_false_collar", "THE FALSE COLLAR", "Anderson - The False Collar"),
    ("the_shadow", "THE SHADOW", "Anderson - The Shadow"),
    (
        "the_little_match_girl",
        "THE LITTLE MATCH GIRL",
        "Anderson - The Little Match Girl",
    ),
    (
        "the_dream_of_little_tuk",
        "THE DREAM OF LITTLE TUK",
        "Anderson - The Dream Of Little Tuk",
    ),
    ("the_naughty_boy", "THE NAUGHTY BOY", "Anderson - The Naughty Boy"),
    ("the_red_shoes", "THE RED SHOES", "Anderson - The Red Shoes"),
]


def gather(*, offline=False, cache_dir=None):
    """Extract the Anderson stories from the Gutenberg Project."""
    gatherlib.gather(
        offline=offline,
        cache_dir=cache_dir,
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
