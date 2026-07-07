# code modified from OpenAI suggested

import re

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


def find_all_stories_for_genre (stories, genre):
    """
    Args:
        stories (list[story]):   All the stories we want to genre tag
        genre (str):   String representing the canonical genres
    Returns:
        stories (list[story]):   All the stories that are identified as that genre.   
    """
    return [story for story in stories if get_genre_for_story(story) == genre]

    
def get_id_for_story (story):
    """
    Args:
        story (story):  The story from the corpora we are interested in
    Returns:
        int:   The gutenberg id for that story
    """

    pieces = story.metadata['url'].split("/")

    if pieces[3] == "files":
        return int(pieces[4])
    else:
        return int(pieces[5])
    
def get_genre_by_id (id):
    """
    Args:
        id (int):   gutenberg story id
    Returns:
        string:   Canonical genre 
    """
    
    return genre.classify_exclusive(api.get_metadata("subject", id))[0]


def get_genre_for_story (story):
    """
    Args:
        story (story):   A story we want to genre identify

    Returns:
        string:  Canonical genre
    """
    
    return get_genre_by_id (get_id_for_story (story))
