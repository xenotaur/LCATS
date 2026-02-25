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
    )


if __name__ == "__main__":
    gather()
