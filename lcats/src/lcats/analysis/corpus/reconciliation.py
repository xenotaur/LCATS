"""Read-only comparison of story collections, grouped by original source URL.

Notebook 15's reusable comparison lives here. Duplicate URLs remain visible as
lists rather than silently collapsing records or multiplying an outer join.
Only canonical story buckets are read; sidecar JSON files are not stories.
"""

import hashlib
import json
import pathlib

from lcats.analysis.corpus import discovery


def collate_stories(collection):
    """Return deterministic source groups for a single collection directory.

    Each summary preserves path, bucket name, title, author (including missing or
    list-valued authors), body hash and complete file hash. Missing URLs and
    malformed story JSON raise ValueError with the offending path. Nothing is
    written, and no catalog or network access is required.
    """
    root = pathlib.Path(collection)
    if not root.is_dir():
        raise NotADirectoryError(str(root))
    groups = {}
    for path in sorted(discovery.iter_collection_story_files(root)):
        raw = path.read_bytes()
        try:
            data = json.loads(raw)
            url = data["metadata"]["url"]
            body = data["body"]
            if not isinstance(url, str) or not url.strip() or not isinstance(body, str):
                raise ValueError("nonempty source URL and string body required")
        except (ValueError, TypeError, KeyError) as exc:
            raise ValueError(f"invalid story {path}: {exc}") from exc
        groups.setdefault(url, []).append(
            {
                "path": str(path.relative_to(root)),
                "bucket": path.parent.name,
                "title": data.get("name"),
                "author": data.get("author"),
                "body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
                "file_sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return {url: groups[url] for url in sorted(groups)}


def compare_collections(left, right):
    """Return JSON-compatible one/two-sided and duplicate-source comparisons.

    Equality flags are None unless exactly one story occurs on each side. This
    avoids suggesting that duplicate sources were matched unambiguously. Author
    comparison is strict (list order and missing values are preserved). Body
    hashes compare decoded string content, without normalization or corpus edits.
    """
    left_groups, right_groups = collate_stories(left), collate_stories(right)
    result = []
    for url in sorted(left_groups.keys() | right_groups.keys()):
        a, b = left_groups.get(url, []), right_groups.get(url, [])
        unique = len(a) == len(b) == 1
        result.append(
            {
                "url": url,
                "left": a,
                "right": b,
                "appears_in_both": bool(a and b),
                "duplicate_url": len(a) > 1 or len(b) > 1,
                "titles_match": a[0]["title"] == b[0]["title"] if unique else None,
                "authors_match": a[0]["author"] == b[0]["author"] if unique else None,
                "bodies_match": (
                    a[0]["body_sha256"] == b[0]["body_sha256"] if unique else None
                ),
            }
        )
    return result
