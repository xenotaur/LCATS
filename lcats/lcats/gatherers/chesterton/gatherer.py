"""Corpus extractor for the Chesterton stories."""

from lcats.gatherers import gatherlib


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


def gather():
    """Extract the Chesterton stories from the Gutenberg Project."""
    gatherlib.gather(
        corpus="Chesterton",
        target_directory=TARGET_DIRECTORY,
        description="Chesterton stories from the Gutenberg Project.",
        license_text="Public domain, from Project Gutenberg.",
        author="Chesterton",
        year=0,
        headings=CHESTERTON_HEADINGS,
        gutenberg_url=CHESTERTON_GUTENBERG,
    )


if __name__ == "__main__":
    gather()
