"""Gatherer for single stories from gutenberg"""

# - Should change the line to paragraph for accuracy - TODO?

import json
import os
import difflib
import re
import csv


from lcats import constants
from lcats.utils import names
from lcats.gettenberg import api
from lcats.gettenberg import headers
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


def title_in_body(text, title):
    """Return the location of the end of the title in the body of the text.

    If the title is not found, it returns -1, but if it is found, it returns
    the location, plus the title length, plus one to account for the newline.

    Args:
        text (str): The full text of the story.
        title (str): The title of the story.
    Returns:
        int: The location of the end of the title in the text, or -1 if not found.
    """
    # Extract just the first title and wrap it in newlines to avoid partial matches.
    title_to_find = "\n" + list(title)[0].upper() + "\n"
    location = text.find(title_to_find)
    if location == -1:
        return location
    return location + len(title_to_find) + 1


def chaptered(text):
    """Return True if the text contains chapters, False otherwise.

    Works for chapters in Roman numerals and w/o names.   Needs to be expanded.

    Args:
        text (str): The full text of the story.
    Returns:
        bool: True if the text contains chapters, False otherwise.
    """
    result = 0

    text_array = text.split("\n")
    for line in text_array:
        line = line.strip().lower()
        if line in ["contents", "contents."]:
            return True
        if line in [
            "i",
            "i.",
            "chapter i",
            "chapter 1",
            "chapter i.",
            "chap. i.",
            "part i",
        ]:
            result = result + 1
        if line in [
            "ii",
            "ii.",
            "chapter ii",
            "chapter 2",
            "chapter ii.",
            "chap. ii.",
            "part ii",
        ]:
            result = result + 1

    # A single I or II might be an anomoly so this is to see if both exist
    return result >= 2


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
        name (str): The name of the author.
    Returns:
        list: A list of pen names for the author, including the original name.
    """
    all_names = [name]
    if name in storymap.PEN_NAMES:
        all_names = all_names + storymap.PEN_NAMES[name]
    return all_names


def fiction(subject):
    for piece in list(subject):
        if "fiction" in piece.lower().strip():
            return True

    return False


def short_story(subject):
    for piece in list(subject):
        if "short stor" in piece.lower().strip():
            return True

    return False


def loc_fiction(subject):
    for piece in list(subject):
        if piece in ["PS", "PR"]:
            return True

    return False


def subject_ok(subject):
    """Return True if the subject is consistent with what we want (short fiction).

    Uses the list of excluded subjects from storymap.py to filter out unwanted subjects.

    Args:
        subject: a string or list of strings representing the subject from the story metadata.
    Returns:
        bool: True if the subject appears to be short fiction, False otherwise.
    """

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


def title_ok(title):
    """Return True if the title is consistent with a valid story.

    Args:
        title (string): A string representing the title from the metadata of the story.

    Returns:
        bool: True if the title is consistent with what we want, False otherwise.
    """

    result = True
    if len(list(title)) > 1:  # multiple titles
        for a_title in list(title):
            result = result and title_ok(a_title)

        return result

    if "index of the project gutenberg" in list(title)[0].lower():
        return False

    for part_indicator in storymap.EXCLUDED_TITLE_PART_WORDS:
        if re.search(rf"{part_indicator}\s*\d+", str(list(title)[0]), re.IGNORECASE):
            return False

    for piece in list(title)[0].split(" "):
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
        book:  True if the paragraph is deemed to be extra textual."""

    result = True

    if len(paragraph) == 0:
        result = False

    lines = paragraph.split("\n")

    for line in lines:
        if len(line) == 0:
            continue
        if line[:4] == "    " and line[4] == "“":
            result = False
        if line[:4] == "    " and line[4] != " ":
            continue

        result = False

    return result


def line_contains_transcriber_info(line):
    """Return True if the line contains transcriber information.
    Args:
        line (str): A string representing a line of the story.
    Returns:
        bool: True if the line contains transcriber information, False otherwise."""
    stripped = line.strip().lower()
    return (
        stripped.startswith("transcriber")
        or stripped.startswith("[transcriber")
        or stripped.startswith("_transcriber")
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


def line_contains_title(original_line, title):
    """Detect whether the line contains the title of the story.

    Some things have an extra period.  Some are surrounded by _.   Some leave off the !.

    Args:
        original_line (str): A string representing a line of the story.
        title (str): A string representing the title of the story.
    Returns:
        bool: True if the line contains the title, False otherwise.
    """
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
    title = title.lower()

    # Skip titles that are obviously too different in length.
    if abs(len(line) - len(title)) > 5:
        return False

    # Exact matches, with some common variations.
    if (
        line == title
        or line == "_" + title + "_"
        or line == title + "."
        or line[:-1] == title
        or line[1:-1] == title
    ):
        return True

    # Fuzzy match for minor variations.
    if (
        max(
            difflib.SequenceMatcher(None, line, title).ratio(),
            difflib.SequenceMatcher(None, title, line).ratio(),
        )
        > 0.90
    ):  # KMM
        return True

    # Handle titles that start with "The ".
    if title[:4] == "the ":
        return line_contains_title(line, title[4:])

    # We didn't find any kind of match.
    return False


def line_contains_author(line, authors, alias, limit=8):
    """Detect whether the line contains the author of the story or other author-like content.

    We limit the size of the line so we don't find this in a longer line of text.

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
        for author in pen_names(authors[0]):
            author_names = author.split(",")
            last_name = author_names[0].strip().lower()
            if len(author_names) < 2:
                first_name = ""
            else:
                first_name = author_names[1].strip().lower()

            # If an author is detected and the line is short enough, return True.
            stripped = line.strip().lower()
            if (
                first_name in stripped
                and last_name in stripped
                and len(line.split()) < limit
            ):
                return True

            # Handle lines that just say "by" or "by FN LN" or similar.
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


def names_match(name1, name2):
    name1 = name1.strip().lower()
    name2 = name2.strip().lower().replace(", ", " ").replace(",", " ")

    matches = 0
    for namelet in name2.split():
        if namelet in name1:
            matches = matches + 1

    if matches == len(name2.split()):  # all match!
        return True
    elif matches == 0:
        return False
    elif matches > len(name2.split()):  # more matches?
        return False
    elif len(name2.split()) > 2 and matches >= 2:
        return True
    else:
        return False


def line_contains_author2(line, authors, limit=8):
    """Detect whether the line contains the author of the story or other author-like content.

    We limit the size of the line so we don't find this in a longer line of text.

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

    result = False
    for author in authors:
        result = result or names_match(line, author)

    if not result:  # check the by special case?
        stripped = line.strip().lower()
        # if (first_name in stripped and last_name in stripped and len(line.split()) < limit):
        #    return True

        # Handle lines that just say "by" or "by FN LN" or similar.
        if (
            stripped == "by"
            or stripped.startswith("by ")
            or stripped.startswith("_by ")
            or stripped.startswith("_by_")
        ):

            # If the line is short enough and starts with by, assume it's the author line.
            if len(line.split()) < limit:
                result = True
            else:
                result = False

    return result


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
        title (str): A string representing the title of the story.
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

    return True


def fix_body(text, author, alias):
    """Removes extraneous lines from the body of the story.

    Args:
        text (str): A string representing the body of the story.
        author (str): A string representing the author of the story.
        alias (str): A string representing the alias of the story.
    Returns:
        str: A string representing the cleaned-up body of the story.
    """
    text_array = text.split("\n\n")
    fixed_body = []

    firstTime = True

    for paragraph in text_array:
        if firstTime:
            if line_contains_transcriber_info(paragraph):
                continue
            elif line_contains_illustration(paragraph):
                continue
            elif "This etext was produced" in paragraph:
                continue
            elif line_contains_author(paragraph, author, alias):
                continue
            elif firstTime and intrusive_paragraph(paragraph):
                continue
            else:
                firstTime = False

        fixed_body.append(paragraph)

    return "\n\n".join(fixed_body)


def body_of_text(text, author, alias, title, debug=False):
    """Return the body of the story, i.e., the material after the title and author.
    Args:
        text (str): A string representing a story from Gutenberg in plain text.
        author (str): A string representing the author of the story.
        title (str): A string representing the title of the story.
        debug (bool): A boolean indicating whether to print debug information.
    Returns:
        str: A string representing the body of the story.
    """
    number_of_titles_found = 0
    seen_author = False
    seen_title = False

    title = make_title(title)
    number_of_titles = how_many_titles(text, title)

    paragraph_array = text.split("\n\n")

    for index, line in enumerate(paragraph_array):
        #   KMM Useful for debugging
        if debug:
            print(
                str(index)
                + " : "
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
        if seen_title and seen_author and in_body(line, title, author, alias):
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
    # print("In body " + str(seen_author) + " " + str(author))

    body = "\n\n".join(
        [
            ("" if "*       *       *       *       *" in line else line)
            for line in paragraph_array[index:]
        ]
    )

    return fix_body(body.removeprefix("\n"), author, alias)


def gather_story(gatherer, story):
    """Extract a single story from the Gutenberg Project.
    Args:
        gatherer: An instance of DataGatherer to use for downloading and saving the story.
        story: An integer representing the Gutenberg story ID to extract.
    Returns:
        A tuple of three elements:
        - The story ID (int).
        - The file path where the story was saved (str) or None if not saved.
        - An error message (str) or None if no error occurred.
    """
    # Extract metadata and filter out stories that don't meet our criteria.
    subject = api.get_metadata("subject", story)
    if len(subject) == 0:
        return story, None, "No data for this story, skipping"

    is_subject_ok = subject_ok(subject)
    language = api.get_metadata("language", story)
    is_language_ok = only_english(language)
    title = api.get_metadata("title", story)
    is_title_ok = title_ok(title)
    author = list(api.get_metadata("author", story))
    is_author_ok = author_ok(author)
    alias = list(api.get_metadata("alias", story))
    if not (is_subject_ok and is_language_ok and is_title_ok and is_author_ok):
        print(f"Metadata not OK, skipping story: {story}")
        print(f" - Subject: {subject}: {is_subject_ok}")
        print(f" - Language: {language}: {is_language_ok}")
        print(f" - Title: {title}: {is_title_ok}")
        print(f" - Author: {author}: {is_author_ok}")
        return story, None, "Metadata not suitable, skipping."

    # Extract the text and remove stories that have chapters.
    try:
        etext = api.load_etext(story)
    except Exception:
        return story, None, "Failed to retrieve a story, skipping."

    stripped_text = headers.strip_headers(etext.strip()).strip()
    clean_text = stripped_text.decode("utf-8", errors="replace").strip()
    if chaptered(clean_text):
        return story, None, "Story has chapters, skipping."

    # print("DEBUG " + str(story) + " " + str(how_many_titles(clean_text, list(title)[0])))

    # Extract the title and body of the story.
    short = True
    for single_title in list(title):
        body = body_of_text(clean_text, author, alias, single_title)
        if len(body.split("\n\n")) > 10:
            short = False
            title = single_title  # wow this is bad style
            break

    if short:
        print("Story is too short, skipping: " + str(story))
        return story, None, "Story is too short, skipping."

    # if we get here, we have the pieces of the story, so let's save
    # file_name = names.title_to_filename(title, ext=constants.FILE_SUFFIX, max_len=50)
    file_name = names.title_and_author_to_filename(
        title, author, ext=constants.FILE_SUFFIX, max_len=50
    )

    # print("DESUB " + str(file_name) + " " + str(subject))

    print(f"Gathering story {story}: {title}")
    print(f" - File name: {file_name}")

    # Structure the data into a dictionary
    url = (
        "https://www.gutenberg.org/cache/epub/"
        + str(story)
        + "/pg"
        + str(story)
        + ".txt"
    )
    data_to_save = {
        "name": title,
        "author": author,
        "body": body,
        "metadata": {
            "author": author,
            "year": "Unknown",
            "url": url,
            "name": file_name,
        },
    }

    # Move all of this code up into the API so it is done consistently.
    # Ensure the data directory exists
    path = os.path.join(constants.DATA_ROOT, storymap.TARGET_DIRECTORY)

    # Ensure the file path exists.
    file_path = os.path.join(path, file_name)
    gatherer.ensure(file_name)

    # Write data to JSON file
    with open(file_path, "w", encoding="utf-8") as json_file:
        json.dump(data_to_save, json_file, indent=4)

    return story, file_path, None


def test_stories(stories):
    for story in stories:
        test_story_get(story)


def test_story_get(story):
    # Extract metadata and filter out stories that don't meet our criteria.
    subject = api.get_metadata("subject", story)
    is_subject_ok = subject_ok(subject)
    language = api.get_metadata("language", story)
    is_language_ok = only_english(language)
    title = api.get_metadata("title", story)
    is_title_ok = title_ok(title)
    author = list(api.get_metadata("author", story))
    is_author_ok = author_ok(author)
    alias = list(api.get_metadata("alias", story))

    if True or not (is_subject_ok and is_language_ok and is_title_ok and is_author_ok):
        # print(f"Metadata not OK, skipping story: {story}")
        print(f" - Subject: {subject}: {is_subject_ok}")
        print(f" - Language: {language}: {is_language_ok}")
        print(f" - Title: {title}: {is_title_ok}")
        print(f" - Author: {author}: {is_author_ok}")
        # return story, None, "Metadata not suitable, skipping."

    # Extract the text and remove stories that have chapters.
    etext = api.load_etext(story)
    stripped_text = headers.strip_headers(etext.strip()).strip()
    clean_text = stripped_text.decode("utf-8", errors="replace").strip()
    if chaptered(clean_text):
        print("Story has chapters, skipping: " + str(story))
        return story, None, "Story has chapters, skipping."

    # Extract the title and body of the story.
    title = list(title)[0]
    print(story)
    body = body_of_text(clean_text, author, alias, title)
    if len(body) < 10:
        print("Story is too short, skipping: " + str(story))
        return story, None, "Story is too short, skipping."

    # if we get here, we have the pieces of the story, so let's save
    file_name = names.title_and_author_to_filename(
        title, ext=constants.FILE_SUFFIX, max_len=50
    )

    print(f"Gathering story {story}: {title}")
    print(f" - File name: {file_name}")

    return body


def show_data_not_corpora():
    file_path = "notebooks/output/stories_comparison.csv"  # Replace with the actual path to your CSV file

    try:
        with open(file_path, "r", newline="") as csvfile:
            reader = csv.reader(csvfile)
            # Iterate over each row in the CSV file
            for row in reader:
                if (
                    row[3] == "False" and row[7] == "False"
                ):  # appears in data and NOT in corpora
                    # print(row)
                    id = row[0].split("/")
                    subs = api.get_metadata("subject", int(id[5]))
                    title = api.get_metadata("title", int(id[5]))

                    print(id[5] + " , '" + str(title) + "' , " + str(subs))

    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")


def show_corpora_not_data():
    file_path = "notebooks/output/stories_comparison.csv"  # Replace with the actual path to your CSV file

    try:
        with open(file_path, "r", newline="") as csvfile:
            reader = csv.reader(csvfile)
            # Iterate over each row in the CSV file
            for row in reader:
                if (
                    row[3] == "False" and row[7] == "True"
                ):  # appears in corpora and NOT in data
                    # print(row)
                    id = row[0].split("/")
                    subs = api.get_metadata("subject", int(id[5]))
                    title = api.get_metadata("title", int(id[5]))

                    print(id[5] + " , '" + str(title) + "' , " + str(subs))

    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")


def grab_story(story):
    etext = api.load_etext(story)
    stripped_text = headers.strip_headers(etext.strip()).strip()
    clean_text = stripped_text.decode("utf-8", errors="replace").strip()

    return clean_text
