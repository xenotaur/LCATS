"""Inspect and pretty-print story JSON files from the command line."""

from __future__ import annotations

import ast
import json
import pathlib
import sys
import textwrap

from typing import Any, Dict


def inspect(*args: str) -> int:
    """
    Inspect one or more JSON files (args are strings from the CLI).
    Resolves each path relative to the current directory and pretty-prints the story.
    Errors are written to stderr. Returns a non-zero exit code on failure.

    Returns:
        0 if all files printed successfully
        2 if no arguments provided
        1 if any file was missing / invalid / failed to parse
    """
    if not args:
        sys.stderr.write(
            "usage: lcats inspect <file1.json> [file2.json ...]\n")
        return 2

    inspected = 0
    not_found = 0
    errors = 0

    for raw in args:
        p = pathlib.Path(raw).expanduser()
        # resolve(strict=False) to keep non-existent paths as-is for better error messages
        try:
            p = p.resolve(strict=False)
        except Exception:
            # Very rare, but Path.resolve could raise on weird paths; fallback to original
            p = pathlib.Path(raw)

        if not p.exists():
            sys.stderr.write(f"error: not found: {raw} (resolved: {p})\n")
            not_found += 1
            continue

        if not p.is_file():
            sys.stderr.write(f"error: not a file: {raw} (resolved: {p})\n")
            not_found += 1
            continue

        try:
            pretty_print_story(p)
            inspected += 1
        except json.JSONDecodeError as e:
            sys.stderr.write(f"error: invalid JSON in {p}: {e}\n")
            errors += 1
        except UnicodeDecodeError as e:
            sys.stderr.write(f"error: could not decode {p}: {e}\n")
            errors += 1
        except Exception as e:
            # Catch-all so one bad file doesn't stop the rest
            sys.stderr.write(f"error: failed to inspect {p}: {e}\n")
            errors += 1

    message = f"Inspected {inspected} files"
    result = 0
    if not_found > 0:
        message += f", {not_found} not found"
        result = 1
    if errors > 0:
        message += f", {errors} errors"
        result = 1
    message += "."
    return message, result


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
    width: int = 80
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
    snippet = body[:max_body_chars]
    out.extend(textwrap.wrap(snippet, width=width))
    if len(body) > max_body_chars:
        out.append("\n... [truncated] ...")
    out.append(sep)

    return "\n".join(out)


def pretty_print_story(json_path: str | pathlib.Path, *, max_body_chars: int = 1000, width: int = 80) -> None:
    """
    Top-level printer: loads the JSON from file, formats it with `format_story_json`,
    and prints the result.
    """
    path = pathlib.Path(json_path)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    formatted = format_story_json(
        data, max_body_chars=max_body_chars, width=width)
    print(formatted)


# Optional: allow running directly via `python -m lcats.inspect ...`
if __name__ == "__main__":
    # The top-level entrypoint in your app might do:
    #   return lcats.inspect.inspect(*args)
    # but this lets you test it directly.
    sys.exit(inspect(*sys.argv[1:]))
