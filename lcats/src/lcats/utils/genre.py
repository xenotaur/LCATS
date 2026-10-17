# code modified from OpenAI suggested

import re
from lcats.gettenberg import identifiers

GENRE_RULES = [
    (
        "SF",
        [
            "science fiction",
            "space ships",
            "space colonies",
            "time travel",
            "extraterrestrial",
            "human-alien",
            "aliens",
            "robots",
            "mars",
            "venus",
            "interplanetary",
            "telepathy",
        ],
    ),
    (
        "Fantasy",
        [
            "fantasy",
            "fairy tales",
            "fairies",
            "magic",
            "mythical",
        ],
    ),
    (
        "Horror",
        [
            "horror",
            "ghost",
            "supernatural",
            "gothic",
            "paranormal",
            "occult",
            "vampire",
        ],
    ),
    (
        "Mystery",
        [
            "detective",
            "mystery",
        ],
    ),
    (
        "Crime",
        [
            "crime",
            "criminals",
            "murder",
            "thieves",
            "robbery",
            "spy",
            "spies",
            "thriller",
            "fugitives from justice",
            "escaped prisoners",
        ],
    ),
    (
        "Western",
        [
            "western stories",
            "frontier",
            "cowboys",
            "ranch",
            "indians of north america",
        ],
    ),
    (
        "War",
        [
            "war stories",
            "war -- fiction",
            "soldiers",
            "military",
        ],
    ),
    (
        "Adventure",
        [
            "adventure stories",
            "adventure",
            "hunting stories",
            "survival",
        ],
    ),
    (
        "Sea",
        [
            "sea stories",
            "sea",
            "nautical",
            "seafaring",
            "sailors",
            "ship",
            "ships",
            "ship captains",
            "pirates",
            "ocean",
            "maritime",
        ],
    ),
    (
        "Historical",
        [
            "historical fiction",
            "history -- fiction",
        ],
    ),
    (
        "Apocalyptic",
        [
            "apocalyptic",
            "dystopian",
            "utopian",
        ],
    ),
    (
        "Psychological",
        [
            "psychological fiction",
        ],
    ),
    (
        "Romance",
        [
            "love stories",
            "romance",
            "man-woman relationships",
            "courtship",
            "marriage",
        ],
    ),
    (
        "Humor / satire",
        [
            "humorous stories",
            "humor",
            "satire",
            "satirical",
        ],
    ),
    (
        "Epistolary / diary fiction",
        [
            "epistolary fiction",
            "diary fiction",
            "diaries -- fiction",
            "letters -- fiction",
        ],
    ),
    (
        "Political fiction",
        [
            "political fiction",
            "politics -- fiction",
        ],
    ),
    (
        "Children / juvenile",
        [
            "juvenile fiction",
            "children's stories",
            "boys -- fiction",
            "girls -- fiction",
        ],
    ),
    (
        "Medical fiction",
        [
            "medical fiction",
            "physicians -- fiction",
            "doctors -- fiction",
        ],
    ),
    (
        "Short stories only / unspecified genre",
        [
            "short stories",
        ],
    ),
]


def has_phrase(subjects, phrase):
    """
    Args:
        subjects (list[str]):   The metadata subjects
        phrase (str):   The canonical genre identification phrases

    Returns:
        bool:  True if phrase occurs in the subjects list
    """

    text = "; ".join(subjects).lower()
    phrase = phrase.lower()

    # Escape regex characters, then require non-word boundaries
    # around the phrase. This prevents "ships" from matching
    # inside "relationships."
    pattern = r"(?<!\w)" + re.escape(phrase) + r"(?!\w)"
    return re.search(pattern, text) is not None


def classify_exclusive(subjects):
    """
    Args:
        subjects (list[str]):   The metadata subjects
    Returns:
        (str, list):  Assigned exclusive genre, all matching broad genre signals
    """

    matching_genres = []

    for genre, patterns in GENRE_RULES:
        if any(has_phrase(subjects, pattern) for pattern in patterns):
            matching_genres.append(genre)

    if not matching_genres:
        return "Unclassified", []

    return matching_genres[0], matching_genres


def find_all_stories_for_genre(stories, genre, *, catalog):
    """Filter stories using one caller-owned, read-only Catalog session."""
    return [
        story
        for story in stories
        if get_genre_for_story(story, catalog=catalog) == genre
    ]


def get_id_for_story(story):
    """Read a Gutenberg ID from canonical source provenance; never guess a host.

    Raises:
        ValueError: Source URL is missing or not a recognized Gutenberg identity.
    """
    return identifiers.ebook_id_from_url(story.metadata.get("url"))


def get_genre_by_id(book_id, *, catalog):
    """Classify catalog subjects without setup, downloads or global cache state.

    Missing records and records without subjects classify as Unclassified.
    Catalog errors propagate so corruption is not mistaken for absent metadata.
    """
    record = catalog.get(book_id)
    subjects = (
        [] if record is None else [term.value.text for term in record.ebook.subjects]
    )
    return classify_exclusive(subjects)[0]


def get_genre_for_story(story, *, catalog):
    """Classify a story using its source URL and a caller-owned Catalog."""
    return get_genre_by_id(get_id_for_story(story), catalog=catalog)
