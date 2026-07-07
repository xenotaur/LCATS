"""Inspect and pretty-print story JSON files from the command line."""

from __future__ import annotations

import ast
import json
import pathlib
import sys
import textwrap

from typing import Any, Dict


def inspect_files(*args: str) -> int:
    """
    Shows a summary of one or more JSON files (args are strings from the CLI).
    Resolves each path relative to the current directory and pretty-prints the story.
    Errors are written to stderr. Returns a non-zero exit code on failure.

    Returns:
        0 if all files inspected successfully
        2 if no arguments provided
        1 if any file was missing / invalid / failed to parse
    """
    if not args:
        sys.stderr.write("usage: lcats inspect <file1.json> [file2.json ...]\n")
        return 2

    return summarize_process_results(*process_files(args, inspect_story))


def display_files(*args: str) -> int:
    """
    Display full story text of one or more JSON files (args are strings from the CLI).
    Resolves each path relative to the current directory and pretty-prints the story.
    Errors are written to stderr. Returns a non-zero exit code on failure.

    Returns:
        0 if all files displayed successfully
        2 if no arguments provided
        1 if any file was missing / invalid / failed to parse
    """
    if not args:
        sys.stderr.write("usage: lcats display <file1.json> [file2.json ...]\n")
        return 2

    return summarize_process_results(*process_files(args, display_story))


def process_files(filenames, processor) -> tuple[int, int, int]:
    """
    Process a list of filenames with the given processor function.

    Resolves each path relative to the current directory and then applies the processor.
    Errors are written to stderr. Returns a non-zero exit code on failure.

    Returns:
        0 if all files processed successfully
        2 if no arguments provided
        1 if any file was missing / invalid / failed to parse
    """
    files_inspected = 0
    files_not_found = 0
    files_with_errors = 0

    for filename in filenames:
        inspected, not_found, errors = process_file(filename, processor)
        files_inspected += inspected
        files_not_found += not_found
        files_with_errors += errors

    return files_inspected, files_not_found, files_with_errors


def summarize_process_results(
    files_inspected: int, files_not_found: int, files_with_errors: int
) -> tuple[str, int]:
    """
    Summarize the results of processing multiple files into a message and exit code.

    Args:
        inspected: The number of files successfully inspected.
        not_found: The number of files that were not found.
        errors: The number of files that had errors during processing.
    Returns:
        A tuple containing a summary message and an exit code (0 for success, 1 for any issues).
    """
    message = f"Inspected {files_inspected} files"
    result = 0
    if files_not_found > 0:
        message += f", {files_not_found} not found"
        result = 1
    if files_with_errors > 0:
        message += f", {files_with_errors} errors"
        result = 1
    message += "."
    return message, result


def process_file(filename: str, processor) -> tuple[int, int, int]:
    """Inspect a file at a given path and pretty-print it. Returns (inspected, not_found, errors)."""
    p = pathlib.Path(filename).expanduser()
    # resolve(strict=False) to keep non-existent paths as-is for better error messages
    try:
        p = p.resolve(strict=False)
    except Exception:
        # Very rare, but Path.resolve could raise on weird paths; fallback to original
        p = pathlib.Path(filename)

    if not p.exists():
        sys.stderr.write(f"error: not found: {filename} (resolved: {p})\n")
        return 0, 1, 0  # inspected, not_found, errors

    if not p.is_file():
        sys.stderr.write(f"error: not a file: {filename} (resolved: {p})\n")
        return 0, 1, 0  # inspected, not_found, errors

    try:
        processor(p)
        return 1, 0, 0  # inspected, not_found, errors
    except json.JSONDecodeError as e:
        sys.stderr.write(f"error: invalid JSON in {p}: {e}\n")
        return 0, 0, 1  # inspected, not_found, errors
    except UnicodeDecodeError as e:
        sys.stderr.write(f"error: could not decode {p}: {e}\n")
        return 0, 0, 1  # inspected, not_found, errors
    except Exception as e:
        # Catch-all so one bad file doesn't stop the rest
        sys.stderr.write(f"error: failed to inspect {p}: {e}\n")
        return 0, 0, 1  # inspected, not_found, errors


def _decode_possible_bytes_literal(s: str) -> str:
    """Attempt to decode a string that might be a bytes literal.

    If `s` looks like a Python bytes literal (e.g., "b'...'" or "b\"...\""),
    safely decode it to text using UTF-8 with replacement. Otherwise, return s.

    Args:
        s: The input string to check and decode if needed.
    Returns:
        The decoded string if it was a bytes literal, otherwise the original string.
    """
    s = s or ""
    t = s.strip()
    if len(t) >= 3 and t[0] == "b" and t[1] in ("'", '"'):
        try:
            b = ast.literal_eval(t)
            if isinstance(b, (bytes, bytearray)):
                return bytes(b).decode("utf-8", errors="replace")
        except Exception:
            pass
    return s


def format_story_json(
    data: Dict[str, Any],
    *,  # Enforce keyword-only arguments after this point.
    max_body_chars: int = 1000,
    width: int = 80,
) -> str:
    """Low-level formatter: takes a story JSON object and returns a pretty string.

    Parameters:
        data: Parsed JSON dict with keys like 'name', 'author', 'body', 'metadata'.
        max_body_chars: Truncate body preview to this many characters.
        width: Wrap width for body text.

    Returns:
        A formatted string.
    """
    sep = "=" * width

    name = data.get("name", "<Untitled>")
    authors = data.get("author") or []
    metadata = data.get("metadata") or {}

    body = data.get("body", "")
    if isinstance(body, (bytes, bytearray)):
        body = bytes(body).decode("utf-8", errors="replace")
    elif isinstance(body, str):
        body = _decode_possible_bytes_literal(body)
    else:
        body = str(body)

    out: list[str] = []
    out.append(sep)
    out.append(f"📖 Title: {name}")

    if isinstance(authors, list) and authors:
        out.append("✍️  Author(s):")
        out.extend(f"   - {a}" for a in authors)
    elif isinstance(authors, str) and authors.strip():
        out.append("✍️  Author:")
        out.append(f"   - {authors}")

    out.append("")  # blank line

    if isinstance(metadata, dict) and metadata:
        out.append("🗂 Metadata:")
        for k, v in metadata.items():
            out.append(f"   {k}: {v}")
        out.append("")

    out.append("📜 Story:")
    if max_body_chars is not None:
        snippet = body[:max_body_chars]
        out.extend(textwrap.wrap(snippet, width=width))
        if max_body_chars is not None and len(body) > max_body_chars:
            out.append("\n... [truncated] ...")
    else:
        # TODO(centaur): Add support for textwrapping very long lines.
        out.extend(body.splitlines())
    out.append(sep)

    return "\n".join(out)


def pretty_print_story(
    json_path: str | pathlib.Path, *, max_body_chars: int = 1000, width: int = 80
) -> None:
    """
    Top-level printer: loads the JSON from file, formats it with `format_story_json`,
    and prints the result.
    """
    path = pathlib.Path(json_path)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    formatted = format_story_json(data, max_body_chars=max_body_chars, width=width)
    print(formatted)


def inspect_story(
    json_path: str | pathlib.Path, *, max_body_chars: int = 1000, width: int = 80
) -> None:
    """Alias for pretty_print_story which uses its summarization features."""
    pretty_print_story(json_path, max_body_chars=max_body_chars, width=width)


def display_story(
    json_path: str | pathlib.Path, *, max_body_chars: int = None, width: int = 80
) -> None:
    """Alias for pretty_print_story which uses its summarization features."""
    pretty_print_story(json_path, max_body_chars=max_body_chars, width=width)


# Optional: allow running directly via `python -m lcats.inspect ...`
if __name__ == "__main__":
    # The top-level entrypoint in your app might do:
    #   return lcats.inspect.inspect(*args)
    # but this lets you test it directly.
    sys.exit(inspect_files(*sys.argv[1:]))
