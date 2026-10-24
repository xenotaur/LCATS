"""Gatherer for single stories from gutenberg"""

# - Should change the line to paragraph for accuracy - TODO?

# Several functions now exist with similar functionality; refactor to
#    collapse?    fix_body, in_body, remove_non_text

import os
import difflib
import re

from lcats import constants
from lcats.utils import names
from lcats.gatherers import normalization
from lcats.gatherers import story_output
from lcats.analysis.corpus import discovery
import pathlib
from lcats.gatherers.mass_quantities import storymap


def how_many_titles(text, title):
    """Return the number of times the title appears in the text.

    Args:
        text (str): The full text of the story.
        title (str): The title of the story.
    Returns:
        int: The number of times the title appears in the text.
    """
    text_array = text.split("\n\n")
    number_of_titles = 0

    for paragraph in text_array:
        if line_contains_title(paragraph, title):
            number_of_titles = number_of_titles + 1

    return number_of_titles


def possible_internal_chapter_name(line):
    if line.strip().isupper() and len(line.strip().split(" ")) < 7:
        if line.strip()[0] == '"' and line.strip()[-2:] == '."':
            return False
        if line.strip()[0] == '"' and line.strip()[-1:] == '"':
            return False
        if line.strip()[-1:] == ":":
            return False
        if line.strip()[0] == "\“" and line.strip()[-1:] == "\”":
            return False
        #        if line.strip() == "THE END.":
        #            return False
        if line.strip()[0] == "_" and line.strip()[-1:] == "_":
            return False
        if not any(
            exception == line.strip() for exception in storymap.TITLE_EXCEPTIONS
        ):
            return True

    return False


def chaptered(text):
    """Return True if the text contains chapters, False otherwise.

    Works for chapters in Roman numerals and w/o names.   Needs to be expanded.

    Args:
        text (str): The full text of the story.
    Returns:
        bool: True if the text contains chapters, False otherwise.
    """
    result = 0

    possible_titles = 0

    text_array = text.split("\n\n")

    # if several lines are simply all caps, then it's probably chapter names
    multiple_lines_all_caps = False
    for index, line in enumerate(text_array):
        if possible_internal_chapter_name(line):
            if index < len(text_array) - 2 and text_array[index + 1].isupper():
                multiple_lines_all_caps = True
            elif index > 0 and text_array[index - 1].isupper():
                multiple_lines_all_caps = True
            else:
                multiple_lines_all_caps = False

            # if index < len(text_array) - 2:
            #    multiple_lines_all_caps = True
            # else:
            #    multiple_lines_all_caps = False

            if not multiple_lines_all_caps:
                if index == 0:
                    possible_titles = possible_titles + 1
                else:
                    if (
                        len(text_array[index - 1]) > 0
                        and text_array[index - 1][-1] != ":"
                    ):
                        possible_titles = possible_titles + 1
                    else:
                        possible_titles = possible_titles + 1

        line = line.strip().lower()

        if line in ["table of contents", "contents", "contents.", "contents:"]:
            return True

        if line.startswith("i ~"):
            result = result + 1
        if line.startswith("ii ~"):
            result = result + 1
        if line.startswith("iii ~"):
            result = result + 1

        if line.startswith("i."):
            result = result + 1
        if line.startswith("ii."):
            result = result + 1
        if line.startswith("iii."):
            result = result + 1

        if line.startswith("chapter "):
            result = result + 1

        if line in [
            "i",
            "i.",
            "chapter i",
            "chapter 1",
            "chapter i.",
            "chapter one",
            "chap. i.",
            "part i",
            "part i.",
        ]:
            result = result + 1
        if line in [
            "ii",
            "ii.",
            "chapter ii",
            "chapter 2",
            "chapter two",
            "chapter ii.",
            "chap. ii.",
            "part ii",
            "part ii.",
        ]:
            result = result + 1
        if line in [
            "iii",
            "iii.",
            "chapter iii",
            "chapter 3",
            "chapter three",
            "chapter iii.",
            "chap. iii.",
            "part iii",
            "part iii.",
        ]:
            result = result + 1

    # A single I or II might be an anomoly so this is to see if both exist

    if result == 0 and possible_titles == 2:
        return False
    else:
        return result >= 2 or possible_titles >= 2


def is_number(string):
    """Determine whether a string can be converted into a number.

    Args:
        string (str): The string to check.

    Returns:
       bool: True if the string can be converted to an integer, False otherwise.
    """
    try:
        int(string)
        return True
    except ValueError:
        return False


def only_english(languages, target="en"):
    """Return True if the only language is the target language (default "en" for English).

    Args:
        languages (list or set): A list or set of language codes (e.g., ["en", "fr"])
            presumably from the metadata of a Gutenberg story.
        target (str): The target language code to check against (default is "en").
    Returns:
        bool: True if the only language is the target language, False otherwise.
    """
    if target not in languages:
        return False
    other_languages = set(languages)
    other_languages.remove(target)
    return not other_languages


def pen_names(name):
    """Return a list of pen names for a given author name, including the original name.
    Args:
        name (str): The canonical name of the author.
    Returns:
        list: A list of pen names for the author, including the original name.
    """
    all_names = [name]
    if name in storymap.PEN_NAMES:
        all_names = all_names + storymap.PEN_NAMES[name]
    return all_names


def fiction(subject):
    """Return True if the subject contains fiction
    Args:
        subjects (frozenset): The subject from the gutenberg metadata.
    Returns:
        bool:  True if identified as fiction, False otherwse
    """

    for piece in list(subject):
        if "fiction" in piece.lower().strip():
            return True

    return False


def short_story(subject):
    """Return True if the subject contains a short story tag
    Args:
        subjects (frozenset): The subject from the gutenberg metadata.
    Returns:
        bool:  True if identified as a short story / short stories, False otherwse
    """

    for piece in list(subject):
        if "short stor" in piece.lower().strip():
            return True

    return False


def loc_fiction(subject):
    """Return True if the subject contains a fiction tag via library of congress keys
    Args:
        subjects (frozenset): The subject from the gutenberg metadata.
    Returns:
        bool:  True if identified as a PS or PR library of congress tag, False otherwse
    """

    for piece in list(subject):
        if piece in ["PS", "PR"]:
            return True

    return False


def bad_subjects(subjects):
    """Return True if the subject contains a bad topic (currently just epistolary)
    Args:
        subjects (frozenset): The subject from the gutenberg metadata.
    Returns:
        bool:  True if identified as bad, False otherwse
    """

    for subject in subjects:
        for bad_subject in storymap.EXCLUDED_SUBJECTS:
            if bad_subject in subject.lower():
                return True

    return False


def subject_ok(subject):
    """Return True if the subject is consistent with what we want (short fiction).

    Args:
        subject (frozenset): a string or list of strings representing the subject from the story metadata.
    Returns:
        bool: True if the subject appears to be short fiction, False otherwise.
    """

    if bad_subjects(subject):
        return False

    if loc_fiction(subject) and (short_story(subject) or fiction(subject)):
        return True

    return False


def author_ok(author):
    """Return True if the author is consistent with what we want.

    Args:
        author (frozenset): A frozenset representing the author from the metadata of the story.
    Returns:
        bool: True if the author is consistent with what we want, False otherwise.
    """
    return len(list(author)) > 0


def title_multiple_lines(titles):
    """Return True if the title has multiple lines.   Current legacy code
    Args:
        titles (string): A string representing the title from the metadata of the story.

    Returns:
        bool: True if the title has multiple lines, False otherwise.
    """

    contains = False

    for title in titles:
        if "\n" in title:
            contains = True

    return contains


def title_ok(title):
    """Return True if the title is consistent with a valid story.

    Args:
        title (list[str]): A list of titles to check.

    Returns:
        bool: True if the title is consistent with what we want, False otherwise.
    """

    result = True
    if len(title) > 1:  # multiple titles
        for a_title in title:
            result = result and title_ok([a_title])

        return result

    if "; and" in title[0].strip().lower():
        return False

    if ", and" in title[0].split("\n")[0].strip().lower():
        return False

    if "index of the project gutenberg" in title[0].lower():
        return False

    for part_indicator in storymap.EXCLUDED_TITLE_PART_WORDS:
        if re.search(rf"{part_indicator}\s*\d+", title[0], re.IGNORECASE):
            return False

    for piece in title[0].split(" "):
        piece = piece.lower()

        if piece in storymap.EXCLUDED_TITLE_WORDS:
            return False

    return True


def make_title(title):
    """Return a cleaned-up version of the title.

    Args:
        title (string): A string representing the title from the metadata of the story.
    Returns:
        string: A cleaned-up version of the title.
    """
    # First try splitting by \n and attempt to remove any trailing year.
    title_array = title.split("\n")
    if len(title_array) == 2 and is_number(title_array[1]):
        title_number = int(title_array[1])
        if title_number > 1800 and title_number < 1960:
            return title_array[0]

    # Next try splitting by \r\n and attempt to remove any trailing item.
    title_array = title.split("\r\n")
    if len(title_array) != 1:
        return title_array[0]

    # If both those fail, return the title as is.
    return title


def intrusive_paragraph(paragraph):
    """Return True if we believe the paragraph is intrusive
    Args:
        paragraph (str):  A string representing a paragraph
    Returns:
        book:  True if the paragraph is deemed to be extra textual.
    Note:  The specific things tested should be moved to storymap
    """

    result = True

    if len(paragraph) == 0:
        result = False

    lines = paragraph.split("\n")

    for line in lines:
        stripped = line.strip().lower()
        if stripped.startswith("typographical errors corrected"):
            return True
        if stripped.startswith('"obvious punctuation errors repaired'):
            return True
        if stripped.startswith("this etext was produced"):
            return True
        if stripped.startswith("|this etext was produced"):
            return True
        if stripped.startswith("classic reprint from"):
            return True
        if stripped.startswith("the country life press"):
            return True
        if stripped.startswith("the sentence on page"):
            return True
        if stripped.startswith("printed in u. s. a."):
            return True
        if stripped.startswith("all rights reserved"):
            return True
        if stripped.startswith("printed in the united states of america"):
            return True
        if stripped.startswith("a fragment from the journal"):
            return True
        if stripped == "printed by":
            return True
        if stripped.startswith("reprinted by permission of the author"):
            return True
        if stripped.startswith("copyright,") or stripped.startswith("copyright:"):
            return True
        if stripped.startswith("heading by"):
            return True
        if "copies of this book printed on" in stripped:
            return True
        if stripped.startswith("author of "):
            return True
        if len(line) == 0:
            continue

        result = False

    return result


def chunk_contains_transcriber_info(chunk):
    """Return True if the chunk of story has transcriber info

    Args:
        chunk (string):  A chunk of the story.

    Returns:
        bool: True if the chunk has a transcriber on one of the lines, False otherwise.
    """
    lines = chunk.split("\n")
    if len(lines) > 10:
        return False

    contains = False
    for line in lines:
        contains = contains or line_contains_transcriber_info(line)

    return contains


def line_contains_transcriber_info(line):
    """Return True if the line contains transcriber information.
    Args:
        line (list): A string representing a line of the story.
    Returns:
        bool: True if the line contains transcriber information, False otherwise."""
    stripped = line.strip().lower()

    if len(stripped) == 0:
        return False

    return (
        stripped.startswith("transcriber")
        or stripped.startswith("[transcriber")
        or stripped.startswith("_transcriber")
        or (stripped[0] == "|" and "transcriber's note" in stripped)
    )


def line_contains_footnote(line):
    """Return True if the line contains a footnote
    Args:
        line (str): A string representing a line of the story.
    Returns:
        bool: True if the line contains a footnote, False otherwise."""
    stripped = line.strip().lower()

    return (
        stripped.startswith("footnote")
        or stripped.startswith("[footnote")
        or stripped.startswith("_footnote")
    )


def line_contains_illustration(line):
    """Return True if the line contains illustration information.
    Args:
        line (str): A string representing a line of the story.
    Returns:
        bool: True if the line contains illustration information, False otherwise."""
    stripped = line.strip().lower()
    return (
        stripped.startswith("illustrat")
        or stripped.startswith("[illustrat")
        or stripped.startswith("_illustrat")
    )


def line_contains_frontispiece(line):
    """Return True if the line contains illustration information.
    Args:
        line (str): A string representing a line of the story.
    Returns:
        bool: True if the line contains illustration information, False otherwise."""
    stripped = line.strip().lower()
    return (
        stripped.startswith("frontispiece")
        or stripped.startswith("[frontispiece")
        or stripped.startswith("_frontispiece")
    )


def chunk_contains_sidenote(chunk):
    """Return True if the chunk of story has a publisher in it.

    Args:
        chunk (string):  A chunk of the story.

    Returns:
        bool: True if the chunk has a sidenote on one of the lines, False otherwise.
    """
    lines = chunk.split("\n\n")
    if len(lines) > 10:
        return False

    contains = False
    for line in lines:
        contains = contains or line_contains_sidenote(line)

    return contains


def line_contains_sidenote(line):
    """Return True if the line has a sidenote in it.

    Args:
        line (string):  A line of the story.

    Returns:
        bool: True if the line contains a sidenote, False otherwise.
    """

    stripped = line.strip().lower()

    return (
        stripped.startswith("sidenote")
        or stripped.startswith("[sidenote")
        or stripped.startswith("_sidenote")
    )


def chunk_contains_publisher(chunk):
    """Return True if the chunk of story has a publisher in it.

    Args:
        chunk (string):  A chunk of the story.

    Returns:
        bool: True if the chunk has a publisher on one of the lines, False otherwise.
    """
    lines = chunk.split("\n\n")
    if len(lines) > 10:
        return False

    contains = False
    for line in lines:
        contains = contains or line_contains_publisher(line)

    return contains


def line_contains_publisher(line):
    """Return True if the line has a publisher in it.

    Args:
        line (string):  A line of the story.

    Returns:
        bool: True if the line contains a known publisher, False otherwise.
    """
    result = False

    for publisher in storymap.PUBLISHERS:
        if publisher.lower() in line.strip().lower():
            result = True

    return result


def line_contains_publisher_city(line, publisher):
    """Return True if the line has a publisher in it.

    Args:
        line (string):  A line of the story.

    Returns:
        bool: True if the line contains XXXXXX, False otherwise.
    """

    if publisher is None:
        return False

    city = find_city_for_publisher(publisher)
    if city == line.strip().lower():
        return True

    return False


def find_city_for_publisher(publisher):
    result = None

    for publisher_info in storymap.PUBLISHER_CITIES:
        if publisher_info[0].lower() in publisher.strip().lower():
            result = publisher_info[1]

    return result


def chunk_contains_author(chunk, authors, alias, limit=8):
    """Detect whether the chunk contains the author of the story or other author-like content.

    We limit the size of the chunk so we do not find this in a longer chunk of text.

    Questions:
    - What about folks with more than two names? Or just one name?
    - Do all metadata use LN, FN format?
    - What about pen names? We forgot about pen names :-(
    - The logic for the 'by' case seems off. We should be checking for the names.

    Args:
        chunk (str): A string representing a chunk of the story.
        authors (list): A list of strings representing the author(s) of the story.
        limit (int): An integer representing the maximum number of words in the chunk to consider
            it as an author chunk.
    Returns:
        bool: True if the chunk contains the author, False otherwise.
    """

    # KMM A hack a day keeps the bugs away
    sh_lines = chunk.replace("\n\n", "!KMM").replace("\n", " ").replace("!KMM", "\n\n")

    lines = chunk.split("\n")
    if len(lines) > 10:
        return False

    contains = False
    for line in lines:
        contains = contains or line_contains_author(line, authors, alias)

    if not contains:
        for line in sh_lines.split("\n"):
            contains = contains or line_contains_author(line, authors, alias)

    return contains


def chunk_contains_title(original_chunk, title):
    """Detect whether the chunk contains the title of the story.

    Some things have an extra period.  Some are surrounded by _.   Some leave off the !.

    Args:
        original_chunk (str): A string representing a chunk of the story.
        title (list[str]): A list of titles from metadata.
    Returns:
        bool: True if the chunk contains the title, False otherwise.
    """

    lines = original_chunk.split("\n\n")
    if len(lines) > 10:
        return False

    contains = False
    for line in lines:
        contains = contains or line_contains_title(line, title)

    return contains


def is_subtitle_title(title):
    """Does the title contain a subtitle?
    Args:
        title (list):  Strings representing all known titles.
    Returns:
        bool: True if the title seems to be subtitled, False otherwise.
    """

    multiline = False

    for single_title in title:
        if ":" in single_title:
            multiline = True

    return multiline


def is_multiline_title(title):
    """Does the title cross multiple lines?
    Args:
        title (list):  Strings representing all known titles.
    Returns:
        bool: True if the title seems to be across multiple lines, False otherwise.
    """

    multiline = False

    for single_title in title:
        if "\n" in single_title:
            multiline = True

    return multiline


def split_title(title):
    """Split a multiple title into pieces
    Args:
        title (list):  A string representing a (potential?) multiple element title.
    Returns:
        list:  List of titles pieces.
    """

    if title.find("\n") > -1:
        return title.split("\n")
    elif title.find(":") > -1:
        return title.split(":")
    else:
        return [title]  # ensures all returns are indeed lists


def line_contains_title(original_line, title):
    """Detect whether the line contains the title of the story.

    Some things have an extra period.  Some are surrounded by _.   Some leave off the !.

    Args:
        original_line (str): A string representing a line of the story.
        title (list[str]): A list of known titles from metadata.
    Returns:
        bool: True if the line contains the title, False otherwise.
    """
    multiline_title = is_multiline_title(title) or is_subtitle_title(title)
    multiline_line = is_multiline_title(original_line)

    if multiline_line:
        answer = False
        for line_piece in original_line.split("\n"):
            answer = answer or line_contains_title(line_piece, title)

        if answer:
            return True

    stripped = original_line.strip().lower()
    if stripped.find("rn\n") > -1:
        line = (
            (" ".join([piece.strip() for piece in original_line.split("rn\n")]))
            .lower()
            .removesuffix("printed in the united states of america")
            .strip()
        )
    elif stripped.find("\n") > -1:
        line = (
            (" ".join([piece.strip() for piece in original_line.split("\n")]))
            .lower()
            .removesuffix("printed in the united states of america")
            .strip()
        )
    else:
        line = original_line.strip().lower()

    foundTitle = False
    for single_title in list(title):
        single_title = single_title.lower()

        # Skip titles that are obviously too different in length.
        if abs(len(line) - len(single_title)) > 10:
            foundTitle = foundTitle or False

        if multiline_title:
            # need to check each piece, very hack-y
            for single_title_piece in split_title(single_title):
                foundTitle = foundTitle or line_contains_title_piece(
                    line, single_title_piece
                )
        else:
            foundTitle = foundTitle or line_contains_title_piece(line, single_title)

        if foundTitle:
            return True

        # Handle titles that start with "The ".
        if single_title[:4] == "the ":
            return line_contains_title(line, [single_title[4:]])

        # We didn't find any kind of match.

    return False


def line_contains_title_piece(line, title_piece):
    """Split a multiple title into pieces
    Args:
        line (string):  Current line
        title_piece (list):  A substring from a title.
    Returns:
        bool:  True if line contains a title part
    """

    foundTitle = False

    # Exact matches, with some common variations.
    if (
        line == title_piece
        or line == "_" + title_piece + "_"
        or line == title_piece + "."
        or line[:-1] == title_piece
        or line[1:-1] == title_piece
    ):
        foundTitle = foundTitle or True

    # Fuzzy match for minor variations.
    if (
        max(
            difflib.SequenceMatcher(None, line, title_piece).ratio(),
            difflib.SequenceMatcher(None, title_piece, line).ratio(),
        )
        > 0.89
    ):  # KMM
        foundTitle = foundTitle or True

    return foundTitle


def find_gutenberg_line(text_array):
    """Some stories have the gutenberg footers!
    Args:
        text_array (array):  The broken up story text.
    Returns:
        int:  Element of text array containing the gutenberg flag or -1.
    """
    location = -1

    for index, line in enumerate(text_array):
        if line.strip().startswith("*** END OF THE PROJECT GUTENBERG EBOOK"):
            location = index
            break

    return location


def find_author_line(text_array, authors, alias, title, three_newlines_flag=False):
    """Where does the author occur last?
    Args:
        text_array (array):  The broken up story text.
        authors
        alias
        title
        three_new_lines_flag (bool):

    Returns:
        int:  Final valid location of author in text.
    """

    location = -1

    for index, line in enumerate(text_array):
        if (
            chunk_contains_author(line, authors, alias)
            and index < len(text_array) - 1
            and len(
                remove_non_text(
                    text_array[index + 1 :], authors, alias, title, three_newlines_flag
                )
            )
            > 0
        ):
            location = index

    return location


def find_title_line(text_array, title, authors, alias, three_newlines_flag=False):
    """Where does the title occur last?
        Might make the how many titles function unnecessary.

    Args:
        text_array (array):  The broken up story text.
        authors
        alias
        title
        three_new_lines_flag (bool):

    Returns:
        int:  Final valid location of author in text.
    """

    location = -1

    for index, line in enumerate(text_array):
        if (
            chunk_contains_title(line, title)
            and index < len(text_array) - 1
            and len(
                remove_non_text(
                    text_array[index + 1 :], authors, alias, title, three_newlines_flag
                )
            )
            > 0
        ):
            location = index

    return location


def find_end_line(text_array):
    """Does the story have a line containing an explicit end?
    Args:
        text_array (array):  The broken up story text.

    Returns:
        int:  Final location of explicit end marker or -1.

    """
    location = -1

    for index, line in enumerate(text_array):
        if line.strip().lower() == "the end" or line.strip().lower() == "end":
            location = index

    return location


def line_contains_author(line, authors, alias, limit=6):
    """Detect whether the line contains the author of the story or other author-like content.

    We limit the size of the line so we do not find this in a longer line of text.

    Questions:
    - What about folks with more than two names? Or just one name?
    - Do all metadata use LN, FN format?
    - What about pen names? We forgot about pen names :-(
    - The logic for the 'by' case seems off. We should be checking for the names.

    Args:
        line (str): A string representing a line of the story.
        authors (list): A list of strings representing the author(s) of the story.
        limit (int): An integer representing the maximum number of words in the line to consider
            it as an author line.
    Returns:
        bool: True if the line contains the author, False otherwise.
    """
    if len(authors) == 1:  # only one author, woo hoo!
        # for author in pen_names(authors[0]):
        for author in authors + alias + pen_names(authors[0]):
            author_names = author.split(",")
            last_name = author_names[0].strip().lower()
            if len(author_names) < 2:
                first_name = ""
            else:
                first_name = author_names[1].strip().split(" ")[0].lower()

            # If an author is detected and the line is short enough, return True.
            stripped = line.strip().lower()

            if (
                (first_name in stripped or first_name[0] + "." in stripped)
                and last_name in stripped
                and (stripped.startswith("copyright,") or len(line.split()) < limit)
            ):
                return True

                # Handle lines that just say "by" or "by FN LN" or similar.
                # KMM 06/24/26 MIGHT BREAK, figure this part out.  Do we need the check?
            if (
                stripped == "by"
                or stripped.startswith("by ")
                or stripped.startswith("_by ")
                or stripped.startswith("_by_")
            ):
                # If the line is short enough and starts with by, assume it's the author line.
                if len(line.split()) < limit:
                    return True

                # If the line is longer than the limit, check for both names.
                if first_name in stripped and last_name in stripped:
                    # This should only occur if the line is longer than limit previously.
                    return True

        # If we get here, we didn't find the author and there was only one author
        return False

    # If there are two authors, check for both.
    if len(authors) == 2:
        author1 = [authors[0]]
        author2 = [authors[1]]

        author1_present = line_contains_author(line, author1, alias, limit * 2)
        author2_present = line_contains_author(line, author2, alias, limit * 2)
        return author1_present and author2_present

    # Don't attempt to match more than two authors.
    # print("Multiple authors detected: ", authors)
    return False


def story_excluded(story_id):
    """Return True if OK to try this story, False otherwise"""
    return story_id in storymap.STORIES_TO_EXCLUDE


def is_blank_line(line):
    """Return True if the line is blank, False otherwise.
    Args:
        line (str): A string representing a line of the story.
    Returns:
        bool: True if the line is blank, False otherwise.
    """
    return len(line) == 0 or line[0] == " " or line[:2] == "\n "


def in_body(line, title, author, alias):
    """Return True if the line is in the body of the story, False otherwise.

    Args:
        line (str): A string representing a line of the story.
        title (list[str]): A list of titles.
        author (str): A string representing the author of the story.
    Returns:
        bool: True if the line is in the body of the story, False otherwise.
    """

    # Skip title and author lines.
    if line_contains_title(line, title) or line_contains_author(line, author, alias):
        return False

    # Skip empty lines and indented lines.
    if is_blank_line(line):
        return False

    # Skip lines with illustrator information.
    if line_contains_illustration(line):
        return False

    if line_contains_sidenote(line):
        return False

    return True


def fix_body(text, title, author, alias):
    """Removes extraneous lines from the body of the story.

    Args:
        text (str): A string representing the body of the story.
        title (list[str]):  A list of titles for the story.
        author (str): A string representing the author of the story.
        alias (str): A string representing the alias of the story.
    Returns:
        str: A string representing the cleaned-up body of the story.
    """
    text_array = text.split("\n\n")  # ? 2 or 3   was 3 on 6/22
    fixed_body = []

    #    for paragraph in text_array:
    #        if line_contains_illustration(paragraph):
    #            continue
    #
    #        fixed_body.append(paragraph)

    first_time = True
    for paragraph in text_array:
        if first_time:
            if line_contains_transcriber_info(paragraph):
                continue
            elif line_contains_illustration(paragraph):
                continue
            elif line_contains_sidenote(paragraph):
                continue
            elif line_contains_title(paragraph, title):
                continue
            elif line_contains_author(paragraph, author, alias):
                continue
            elif first_time and intrusive_paragraph(paragraph):
                continue
            elif first_time and len(paragraph) == 0:
                continue
            else:
                first_time = False

        fixed_body.append(paragraph)

    # And now backwards!
    final_fixed_body = []

    first_time = True

    fixed_body_reversed = list(reversed(fixed_body))
    end_location = -1  # find_end_line(fixed_body_reversed)

    if end_location != -1:
        final_fixed_body = list(fixed_body_reversed)[end_location + 1 :]
    else:
        for paragraph in reversed(fixed_body):
            if first_time:
                if line_contains_transcriber_info(paragraph):
                    continue
                elif line_contains_illustration(paragraph):
                    continue
                elif line_contains_footnote(paragraph):
                    final_fixed_body.append(paragraph)
                    continue
                elif line_contains_title(paragraph, title):
                    continue
                elif line_contains_author(paragraph, author, alias):
                    continue
                elif len(paragraph) == 0:
                    continue
                elif first_time and intrusive_paragraph(paragraph):
                    continue
                else:
                    first_time = False

            final_fixed_body.append(paragraph)

    final_fixed_body.reverse()
    final_body = "\n\n".join(final_fixed_body)

    return final_body


def remove_non_text(pieces, author, alias, title, three_newlines_flag=False):
    """Return True if the line is in the body of the story, False otherwise.
    Args:
        text_array (array):  The broken up story text.
        author (string):
        alias (string):
        title (string):
        three_new_lines_flag (bool):

    Returns:
        array:
    """

    story_parts = []

    title_chunk = "NO TITLE"
    first_time = True
    publisher_found = False
    publisher = None
    introduction = False

    for piece in pieces:
        if first_time:
            if not (three_newlines_flag):
                if line_contains_illustration(piece):
                    continue
                if line_contains_sidenote(piece):
                    continue

            # potentially dangerous---only one example?
            if three_newlines_flag and piece.strip().startswith("Introduction by"):
                introduction = True
                continue
            if introduction:
                introduction = False
                continue

            if chunk_contains_transcriber_info(piece):
                continue
            if intrusive_paragraph(piece):
                continue
            if line_contains_frontispiece(piece):
                continue
            if line_contains_publisher(piece):
                publisher = piece
                publisher_found = True
                continue
            if chunk_contains_title(piece, title):
                title_chunk = piece
                continue
            if chunk_contains_author(piece, author, alias):
                if title_chunk == "NO TITLE":
                    title_chunk = piece
                    continue
            if publisher_found and line_contains_publisher_city(piece, publisher):
                publisher_found = False
                continue
            if len(piece) == 0:
                continue

        first_time = False
        story_parts.append(piece)

    return story_parts


def body_of_text(text, author, alias, title, debug=False):
    """Return the body of the story, i.e., the material after the title and author.
    Args:
        text (str): A string representing a story from Gutenberg in plain text.
        author (list[str]): A list of authors of the story.
        alias (list[str]): A list of aliases for the author(s) of the story.
        title (list[str]): A list of titles for the story.
        debug (bool): A boolean indicating whether to print debug information.
    Returns:
        str: A string representing the body of the story.
    """
    number_of_titles_found = 0
    seen_author = False
    seen_title = False
    dont_look_flag = False

    # title = make_title(list(title)[0])
    number_of_titles = how_many_titles(text, title)

    # do a 3 split first
    pieces = text.split("\n\n\n")

    aut = find_author_line(pieces, author, alias, title, True)
    tit = find_title_line(pieces, title, author, alias, True)

    new_text = text

    loc3 = max(aut, tit)
    if aut > -1 and tit > -1:
        # we have found both....
        dont_look_flag = True

    if loc3 > -1:
        pieces = pieces[loc3 + 1 :]
        if len(pieces) == 1:
            new_text = pieces[0]
        else:
            story_parts = remove_non_text(pieces, author, alias, title, True)
            new_text = "\n\n\n".join(story_parts)

    # now, repeat with 2 split
    pieces = new_text.split("\n\n")

    gut = find_gutenberg_line(pieces)
    if gut != -1:  # how did the gutenberg.py miss this???
        pieces = pieces[: gut - 1]

    if not dont_look_flag:
        aut = find_author_line(pieces, author, alias, title)
        tit = find_title_line(pieces, title, author, alias)

        loc2 = max(aut, tit)
        # if loc3 > -1 and loc2 > 0:
        #    loc2 = -1

        if loc2 > -1:
            pieces = pieces[loc2 + 1 :]
            if len(pieces) == 1:
                pieces = pieces[0].split("\n\n")

    story_parts = remove_non_text(pieces, author, alias, title)
    new_text = "\n\n".join(story_parts)

    # fix the separator line
    paragraph_array = new_text.split("\n\n")

    body = "\n\n".join(
        [
            ("" if "*       *       *       *       *" in line else line)
            for line in paragraph_array
        ]
    )

    final_body = fix_body(body.removeprefix("\n"), title, author, alias)

    if len(final_body.split("\n\n")) > 10:
        return final_body

    # too small?
    print("Suspected small text, trying fall back extraction.")

    paragraph_array = text.split("\n\n")

    for index, line in enumerate(paragraph_array):
        #   KMM Useful for debugging
        if debug:
            print(
                str(index)
                + " : "
                + str(number_of_titles)
                + " - "
                + str(seen_title)
                + ", "
                + str(seen_author)
                + " -- "
                + line[:60]
            )
        if (number_of_titles > 1) and (number_of_titles_found == number_of_titles):
            break
        if (number_of_titles == 0) and seen_author:
            break
        # added the n_o_t == 1
        if (
            number_of_titles == 1
            and seen_title
            and seen_author
            and in_body(line, title, author, alias)
        ):
            break
        if line_contains_title(line, title):
            seen_title = True
            number_of_titles_found = number_of_titles_found + 1
        elif line_contains_author(line, author, alias):
            seen_author = True
        elif is_blank_line(line):
            continue
        elif (number_of_titles > 1) and (number_of_titles_found != number_of_titles):
            continue
        elif in_body(line, title, author, alias) and (seen_title or seen_author):
            break  # ???
        else:
            continue

    # should be in the body
    body = "\n\n".join(
        [
            ("" if "*       *       *       *       *" in line else line)
            for line in paragraph_array[index:]
        ]
    )

    return fix_body(body.removeprefix("\n"), title, author, alias)


def make_single_title(title):
    if "\r\n" in title:
        pieces = title.split("\r\n")

        return pieces[0]

    if "\n" in title:
        pieces = title.split("\n")

        return pieces[0]

    return title


def _metadata_rejection(metadata, story):
    """Apply the shared gathering and inspection eligibility rules without I/O."""
    if metadata is None or not metadata.subjects:
        return "No data for this story, skipping"
    if not metadata.titles:
        return "No title for this story, skipping"
    if not all(
        (
            subject_ok(metadata.subjects),
            only_english(metadata.languages),
            title_ok(metadata.titles),
            author_ok(metadata.authors),
        )
    ):
        return "Metadata not suitable, skipping."
    if story_excluded(story):
        return "Story on exclusion list, skipping."
    return None


def _inspect_metadata(story, metadata, source):
    """Build the same deterministic extraction report used by gather_story."""
    report = {
        "gutenberg_id": story,
        "metadata": (
            None
            if metadata is None
            else {
                "titles": list(metadata.titles),
                "authors": list(metadata.authors),
                "aliases": list(metadata.aliases),
                "subjects": list(metadata.subjects),
                "languages": list(metadata.languages),
            }
        ),
        "rejection": _metadata_rejection(metadata, story),
        "body": None,
        "provenance": None,
    }
    if report["rejection"] is not None:
        return report
    prepared = source.read(metadata)
    # Physical newlines remain intact in the original-byte cache. Normalize only
    # at the paragraph parser boundary, matching the historical extraction rules.
    text = prepared.cleaned.text.replace("\r\n", "\n").replace("\r", "\n").strip()
    body = body_of_text(
        text, list(metadata.authors), list(metadata.aliases), list(metadata.titles)
    )
    report["body"] = body
    report["provenance"] = prepared.provenance()
    if chaptered(body):
        report["rejection"] = "Story has chapters, skipping."
    elif len(body.split("\n\n")) <= 10:
        report["rejection"] = "Story is too short, skipping."
    return report


def inspect_story(story, *, source):
    """Return JSON-compatible metadata, body, rejection and source provenance.

    This replaces the notebook/debug helpers that printed partial results and
    silently fetched metadata or text. The caller supplies a GutenbergStorySource
    and owns its catalog lifetime and network policy. Rejected metadata causes no
    acquisition. Eligible text may be cached according to that explicit policy;
    no story output is written. Operational errors propagate, not eligibility
    rejections. A rejected short/chaptered story retains its body for inspection.
    """
    return _inspect_metadata(story, source.metadata(story), source)


def gather_story(gatherer, story, *, source):
    """Extract and atomically publish a story using an explicit source.

    Args:
        gatherer: DataGatherer owning the output collection directory.
        story: Positive Gutenberg ebook ID.
        source: GutenbergStorySource with a pinned catalog and explicit policy.

    Returns:
        Tuple of ebook ID, saved/existing path or None, rejection or None.
        Source, decoding, cleanup and output errors propagate to the run boundary.
        An existing valid output is reused before source acquisition.
    """
    metadata = source.metadata(story)
    rejection = _metadata_rejection(metadata, story)
    if rejection is not None:
        return story, None, rejection
    title = metadata.titles[0]
    author = list(metadata.authors)
    file_name = names.title_and_author_to_filename(
        title, author, ext=constants.FILE_SUFFIX, max_len=50
    )
    story_slug = os.path.splitext(file_name)[0]
    existing = (
        pathlib.Path(gatherer.path) / story_slug / discovery.CANONICAL_STORY_FILENAME
    )
    if story_output.existing(existing):
        return story, str(existing), None
    report = _inspect_metadata(story, metadata, source)
    if report["rejection"] is not None:
        return story, None, report["rejection"]
    data_to_save = {
        "name": title,
        "author": author,
        "body": report["body"],
        "metadata": {
            "author": author,
            "year": "Unknown",
            "url": report["provenance"]["source_uri"],
            "name": file_name,
            "gettenberg": report["provenance"],
        },
    }
    # Reuse the same replayable repairs and bucket slug as previous gathering.
    normalization.normalize_story_dict(
        data_to_save, collection=storymap.TARGET_DIRECTORY, story_id=story_slug
    )
    _, file_path = gatherer.ensure(story_slug)
    story_output.publish(file_path, data_to_save)
    return story, file_path, None
