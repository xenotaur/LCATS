"""Extractors used to get text from web pages or other documents."""

import re


DEFAULT_HEADING_TAGS = ["h2", "h3"]
DEFAULT_END_SECTION_TAGS = ["h2", "div"]
DEFAULT_SECTION_BODY_TAGS = ["p"]

DEFAULT_START_SEPARATOR = "pg-start-separator"
DEFAULT_END_SEPARATOR = "pg-end-separator"
DEFAULT_CONTENT_TAGS = ["p", "h1", "h2", "h3", "h4", "h5", "h6"]
DEFAULT_JOIN_SEPARATOR = "\n\n"


class Extractor:
    """Data structure to encapsulate information needed to extract a story from an URL."""

    def __init__(self, title, url, file=None, author=None, year=None):
        """Create a new Extractor.

        Args:
            title (str): The title of the story.
            url (str): The URL of the story.
            file (str): Optional filename to save the story as; computed if not provided.
            author (str): Optional author of the story.
            year (int): Optional year the story was published
        """
        self.title = title
        self.url = url
        self.file = file or title_to_filename(title)
        self.author = author
        self.year = year

    @property
    def description(self):
        """Short description of the story."""
        if self.author:
            return f"{self.title} by {self.author}"
        return self.title

    def __repr__(self):
        """Return a string representation of the Extractor."""
        return f"Extractor('{self.description}')"


def title_to_filename(title):
    """Convert a title into a canonical, filename-friendly string."""
    # Convert to lowercase
    title = title.lower()

    # Remove any character that is not alphanumeric or a space
    title = re.sub(r"[^a-z0-9\s]", "", title)

    # Replace multiple spaces with a single space, then replace spaces with underscores
    title = re.sub(r"\s+", "_", title.strip())

    return title


def get_section_text_from_headings(
    soup,
    start_heading_text,
    start_heading_tags=None,
    end_section_tags=None,
    section_body_tags=None,
):
    """Find paragraphs following a specific heading in a BeautifulSoup object.

    This function is a generalization of previous corpora-specific functions.

    Args:
        soup (BeautifulSoup): The BeautifulSoup object to search.
        start_heading_text (str): The text to search for in the heading.
        start_heading_tags (list): The tags to consider as headings.
        end_section_tags (list): The tags to consider as the end of a section.
        section_body_tags (list): The tags to consider as the body of a section.

    Returns:
        str: The text of the section following the heading.
    """
    # Try the defaults if specific information is not available.
    start_heading_tags = start_heading_tags or DEFAULT_HEADING_TAGS
    end_section_tags = end_section_tags or DEFAULT_END_SECTION_TAGS
    section_body_tags = section_body_tags or DEFAULT_SECTION_BODY_TAGS

    # Construct lambdas used by the get_section_text function.
    def is_start_heading(tag):
        return tag.name in start_heading_tags and start_heading_text in tag.get_text(
            strip=True
        )

    def is_end_section(tag):
        return tag.name in end_section_tags

    def is_section_body(tag):
        return tag.name in section_body_tags

    # Return the section text.
    return get_section_text(soup, is_start_heading, is_end_section, is_section_body)


def get_section_text(soup, is_section_start, is_section_end, is_section_body):
    """Find paragraphs following a specific heading in a BeautifulSoup object.

    Enables extracting text based on a start heading, an end section, and a section body
    computed by arbitrary text identification functions that work with BeautifulSoup tags.

    Args:
        soup (BeautifulSoup): The BeautifulSoup object to search.
        is_section_start (callable): A function that returns True for the start of the section.
        is_section_end (callable): A function that returns True for the end of the section.
        is_section_body (callable): A function that returns True for the body of the section.

    Returns:
        str: The text of the section following the heading.
    """
    start_heading = soup.find(is_section_start)
    if start_heading is None:
        return None

    # If we got the heading, try to return the paragraphs following it
    paragraphs = []
    current_element = start_heading.find_next_sibling()

    # Iterate through sibling elements until the next heading or the end of the siblings is reached.
    while current_element and not is_section_end(current_element):
        print("current_element:", current_element)
        if is_section_body(current_element):
            print(current_element, "is_section_body:", is_section_body(current_element))
            print(
                "current_element.get_text(strip=False):",
                current_element.get_text(strip=False),
            )
            paragraphs.append(current_element.get_text(strip=False).strip())
        else:
            print(current_element, "is not section body")
        current_element = current_element.find_next_sibling()

    return "\n".join(paragraphs)


def extract_tags_between_ids(
    soup,
    start_id=DEFAULT_START_SEPARATOR,
    end_id=DEFAULT_END_SEPARATOR,
    content_tags=None,
):
    """Extract tags between two HTML elements with specific IDs.

    Args:
        soup (BeautifulSoup): The BeautifulSoup object to search.
        start_id (str): The ID of the starting element.
        end_id (str): The ID of the ending element.
        content_tags (list): The tags to consider as content.

    Returns:
        list: The tags between the two elements.
    """
    # Copy the default content tags to prevent modifying the mutable global variable.
    content_tags = content_tags or DEFAULT_CONTENT_TAGS[:]

    start_tag = soup.find(id=start_id)
    end_tag = soup.find(id=end_id)
    if start_tag is None or end_tag is None:
        return None

    matching_tags = []
    current_tag = start_tag.find_next()
    while current_tag and current_tag != end_tag:
        if current_tag.name in content_tags:
            matching_tags.append(current_tag)
        current_tag = current_tag.find_next()

    return matching_tags


def extract_text_from_tags(tags, separator=DEFAULT_JOIN_SEPARATOR):
    """Extract text from a list of BeautifulSoup tags.

    Args:
        tags (list): The BeautifulSoup tags to extract text from.
        separator (str): The separator to use to stitch text together.

    Returns:
        str: The text extracted from the tags.
    """
    collected_text = []
    for tag in tags:
        tag_text = tag.get_text(" ", strip=True)
        if tag_text:
            collected_text.append(tag_text)

    return separator.join(collected_text)


def extract_text_between_ids(
    soup,
    start_id=DEFAULT_START_SEPARATOR,
    end_id=DEFAULT_END_SEPARATOR,
    content_tags=None,
    separator=DEFAULT_JOIN_SEPARATOR,
):
    """Extract text between two HTML elements with specific IDs.

    Args:
        soup (BeautifulSoup): The BeautifulSoup object to search.
        start_id (str): The ID of the starting element.
        end_id (str): The ID of the ending element.
        content_tags (list): The tags to consider as content.
        separator (str): The separator to use to stitch text together.

    Returns:
        str: The text between the two elements.
    """
    tags = extract_tags_between_ids(soup, start_id, end_id, content_tags)
    return extract_text_from_tags(tags, separator=separator)
