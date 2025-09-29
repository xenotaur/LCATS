"""Utility functions for the LCATS package."""

import json
import re
import textwrap

from typing import Iterable, Callable, Any


def pprint(text, width=80, header=True):
    """Pretty-print text with a given line width."""
    if header:
        print()
    paragraphs = text.split('\n\n')
    for paragraph in paragraphs:
        print(textwrap.fill(paragraph, width=width))
        print()


def sm(text, limit=80, spacer='...'):
    """Show prefix and suffix of text if it is longer than the limit."""
    if len(text) <= limit:
        return text
    prefix = (limit - len(spacer)) // 2
    if prefix <= 0:
        raise ValueError(
            f"Text limit {limit} not long enough for prefix/suffix spacer '{spacer}'.")
    suffix = limit - prefix - len(spacer)
    return text[:prefix] + spacer + text[-suffix:]


def sml(  # pylint: disable=too-many-locals
    items: Iterable[Any],
    limit: int = 10,
    spacer: str = "...{count} items omitted...",
    *,
    item_to_str: Callable[[Any], str] = str,
    indent: str = "  "
) -> str:
    """Summarize a list-like sequence for display.

    - If len(items) <= limit: show all items, one per line, JSON-ish style.
    - If len(items) >  limit: show `head` items, a spacer line with omitted count,
      then `tail` items, where head + 1 (spacer) + tail == limit.

    The spacer string may use `{count}` which will be formatted with the omitted count.

    Args:
        items: Any iterable; will be realized to a list.
        limit: Total number of lines INSIDE the brackets, including the spacer when used.
        spacer: Middle line format when items are omitted (receives `count`).
        item_to_str: Function to turn each item into a string (default: str).
        indent: Indentation for each item line.

    Returns:
        A formatted multi-line string like:
        [
          item1,
          item2,
          ...10 items omitted...
          itemN-1,
          itemN
        ]

    Raises:
        ValueError: if limit < 3 when summarization is needed (len(items) > limit).
    """
    seq = list(items)
    n = len(seq)

    # Open bracket
    lines = ["["]

    if n <= limit:
        # Print all items; comma after each except the last
        for i, x in enumerate(seq):
            s = f"{indent}{item_to_str(x)}"
            if i != n - 1:
                s += ","
            lines.append(s)
    else:
        if limit < 3:
            raise ValueError(
                "limit must be >= 3 when summarizing lists longer than the limit.")
        # Choose head & tail so that head + 1(spacer) + tail == limit.
        # head = ceil((limit-1)/2) simplifies to head = limit // 2
        head = limit // 2
        tail = limit - 1 - head
        omitted = n - (head + tail)

        # Head (always followed by a comma because more lines follow)
        for x in seq[:head]:
            lines.append(f"{indent}{item_to_str(x)},")

        # Spacer (also followed by a comma because more lines follow)
        lines.append(f"{indent}{spacer.format(count=omitted)}")

        # Tail (comma after each except the very last overall line)
        for j, x in enumerate(seq[-tail:]):
            # last printed item in the whole block
            last_overall = (j == tail - 1)
            s = f"{indent}{item_to_str(x)}"
            if not last_overall:
                s += ","
            lines.append(s)

    # Close bracket
    lines.append("] total items: " + str(n))
    return "\n".join(lines)


def extract_fenced_code_blocks(text):
    """
    Finds any ```something ... ``` blocks and returns a list of tuples:
      (language, code_string)
    The `language` might be 'json', 'python', etc. or '' if unspecified.
    """
    # Regex explanation:
    #   ```     matches three backticks
    #   (\w+)?  optionally captures a word (the language name)
    #   [^\n]*  then zero or more non-newline characters until a newline
    #   (.*?)   lazily captures all content (including newlines) up to...
    #   ```     the closing three backticks
    pattern = r'```(\w+)?[^\n]*\n(.*?)```'
    matches = re.findall(pattern, text, flags=re.DOTALL)
    return matches


def extract_json(json_string: str, allow_multiple: bool = False) -> dict:
    """
    Extract JSON from a string that may contain additional text.
    """
    try:
        # Attempt to parse the JSON
        return json.loads(json_string)
    except json.JSONDecodeError as exc:
        code_blocks = extract_fenced_code_blocks(json_string)
        if not code_blocks:
            raise ValueError("No JSON found in the string.") from exc
        if len(code_blocks) > 1 and not allow_multiple:
            raise ValueError(
                "Multiple JSON blocks found, but allow_multiple is False.") from exc
        fmt, content = code_blocks[0]
        if fmt != "json":
            raise ValueError(f"Expected JSON format, but got: {fmt}") from exc
        return json.loads(content)


def make_serializable(result, nonserializable_key="response"):
    """
    Remove a non-serializable key from the result dictionary.

    Args:
        result (dict): The dictionary to clean.
        nonserializable_key (str): The key to remove if present.

    Returns:
        dict: A shallow copy of the dictionary with the specified key removed.
    """
    result = dict(result)  # shallow copy to avoid mutating original
    result.pop(nonserializable_key, None)
    return result
