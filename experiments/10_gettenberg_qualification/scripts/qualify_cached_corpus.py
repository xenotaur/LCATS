"""Compare cleanup/extraction on the existing decoded Gutenberg text cache.

From lcats/: python ../experiments/10_gettenberg_qualification/scripts/qualify_cached_corpus.py CATALOG_CACHE TEXT_CACHE COLLECTION OUTPUT_JSON
Inputs are read-only. Legacy .txt.gz files contain UTF-8 re-encoded text, not
verified original HTTP representations. This runner deliberately does not seed
ResourceStore or invent retrieval receipts. It compares old/new cleanup followed
by the same extraction/normalization on identical decoded inputs and current
catalog metadata, then separately compares retained corpus bodies. It is not a
replay of the broken legacy metadata wrapper or proof of original wire encoding.
No network; no corpus writes; output must be new. POSIX alarm: 600 seconds.
"""

import argparse
import collections
import contextlib
import gzip
import hashlib
import io
import json
import pathlib
import resource
import signal
import socket
import sys
import time
from unittest import mock

from lcats.analysis.corpus import discovery
from lcats.gatherers import gutenberg_source
from lcats.gatherers import normalization
from lcats.gatherers import parser
from lcats.gettenberg import cleanup
from lcats.gettenberg import identifiers
from lcats.gettenberg import lifecycle
from lcats.gettenberg import resources

MAX_BYTES = 32 * 1024**2


def digest(data):
    """Identify exact evidence bytes or decoded strings without normalization."""
    return hashlib.sha256(
        data.encode("utf-8") if isinstance(data, str) else data
    ).hexdigest()


def cached_text(directory, book_id):
    """Read a bounded legacy gzip entry; preserve absence rather than fetching."""
    path = directory / f"{book_id}.txt.gz"
    if not path.is_file():
        return None
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("compressed text exceeds bound")
    compressed = path.read_bytes()
    with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("expanded text exceeds bound")
    return raw.decode("utf-8"), digest(compressed), digest(raw)


def extract(text, metadata):
    """Use the actual shared story extractor after physical-newline conversion."""
    return parser.body_of_text(
        text.replace("\r\n", "\n").replace("\r", "\n").strip(),
        list(metadata.authors),
        list(metadata.aliases),
        list(metadata.titles),
    )


def normalized_body(body, metadata, story_id):
    """Apply current replayable corpus repairs without publishing any output."""
    data = {
        "name": metadata.titles[0],
        "author": list(metadata.authors),
        "body": body,
        "metadata": {},
    }
    normalization.normalize_story_dict(
        data, collection="mass_quantities", story_id=story_id
    )
    return data["body"]


def compare(path, text_cache, source, legacy_clean):
    """Return one fully attributed comparison, including explicit refusals/gaps."""
    raw = path.read_bytes()
    story = json.loads(raw)
    book_id = identifiers.ebook_id_from_url(story["metadata"]["url"])
    row = {"path": str(path), "id": book_id, "corpus_sha256": digest(raw)}
    cached = cached_text(text_cache, book_id)
    if cached is None:
        return {**row, "status": "missing_cached_text"}
    text, compressed_sha, decoded_sha = cached
    row.update(
        cache_sha256=compressed_sha,
        decoded_utf8_sha256=decoded_sha,
        decoded_characters=len(text),
    )
    metadata = source.metadata(book_id)
    if metadata is None or not metadata.titles:
        return {**row, "status": "missing_catalog_metadata"}
    row["metadata_rejection"] = parser._metadata_rejection(metadata, book_id)
    row["titles"] = list(metadata.titles)
    row["authors"] = list(metadata.authors)
    cleaned = cleanup.strip_boilerplate(text)
    row["cleanup_diagnostics"] = [d.code for d in cleaned.diagnostics]
    row["cleanup_slice"] = [cleaned.content_start, cleaned.content_end]
    old_cleaned = legacy_clean(text.encode("utf-8")).decode("utf-8")
    old_body = extract(old_cleaned, metadata)
    row["legacy_extracted_sha256"] = digest(old_body)
    if not cleaned.changed and any(d.code != "no_markers" for d in cleaned.diagnostics):
        # The actual source adapter refuses these cases before heuristic parsing.
        # Reporting a conservative refusal is not equivalent to matching output.
        return {**row, "status": "cleanup_refused", "body_equal": None}
    new_body = extract(cleaned.text, metadata)
    before = normalized_body(old_body, metadata, path.parent.name)
    after = normalized_body(new_body, metadata, path.parent.name)
    row.update(
        status="compared",
        body_equal=before == after,
        new_extracted_sha256=digest(new_body),
        normalized_before_sha256=digest(before),
        normalized_after_sha256=digest(after),
        retained_corpus_body_sha256=digest(story["body"]),
        retained_corpus_matches=after == story["body"],
        legacy_matches_retained=before == story["body"],
        new_body_characters=len(after),
        old_body_characters=len(before),
        new_rejection=(
            "chapters"
            if parser.chaptered(new_body)
            else "short" if len(new_body.split("\n\n")) <= 10 else None
        ),
    )
    if before != after:
        # Keep a bounded first-difference excerpt, not copies of complete stories.
        index = next(
            (i for i, pair in enumerate(zip(before, after)) if pair[0] != pair[1]),
            min(len(before), len(after)),
        )
        row["first_difference"] = {
            "offset": index,
            "before": before[max(0, index - 60) : index + 180],
            "after": after[max(0, index - 60) : index + 180],
        }
    return row


def timeout(*_):
    """Bound the complete corpus comparison, including parsing and input reads."""
    raise TimeoutError("cached corpus qualification exceeded 600 seconds")


def main(argv=None):
    """Record all comparisons; gaps remain data rather than false passes."""
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("catalog_cache", "text_cache", "collection", "output"):
        ap.add_argument(name, type=lambda value: pathlib.Path(value).resolve())
    args = ap.parse_args(argv)
    if args.output.exists():
        ap.error("output exists")
    if not hasattr(signal, "SIGALRM"):
        ap.error("POSIX SIGALRM required")
    from gutenbergpy import textget

    result = {
        "scope": __doc__,
        "completed": False,
        "network_bytes": 0,
        "rows": [],
        "legacy_cleaner_sha256": digest(pathlib.Path(textget.__file__).read_bytes()),
        "source_sha256": {
            str(p): digest(p.read_bytes())
            for p in sorted(pathlib.Path("src/lcats").rglob("*.py"))
        },
    }
    start = time.monotonic()
    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(600)
    try:
        manager = lifecycle.CatalogManager(args.catalog_cache)
        with (
            manager.open() as catalog,
            mock.patch.object(
                socket, "socket", side_effect=AssertionError("network forbidden")
            ),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            source = gutenberg_source.GutenbergStorySource(
                catalog,
                resources.ResourceStore(args.catalog_cache),
                routes=resources.GutenbergRoutes(
                    "https://www.gutenberg.org/files/",
                    "https://www.gutenberg.org/cache/epub/",
                ),
            )
            result["catalog_archive_sha256"] = catalog.info["report"]["archive_sha256"]
            paths = sorted(discovery.iter_collection_story_files(args.collection))
            if len(paths) > 10000:
                raise ValueError("collection exceeds 10000-story bound")
            for path in paths:
                result["rows"].append(
                    compare(path, args.text_cache, source, textget.strip_headers)
                )
        result["summary"] = dict(
            collections.Counter(r["status"] for r in result["rows"])
        )
        result["body_differences"] = sum(
            r.get("body_equal") is False for r in result["rows"]
        )
        result["retained_corpus_differences"] = sum(
            r.get("retained_corpus_matches") is False for r in result["rows"]
        )
        result["completed"] = True
    except BaseException as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        signal.alarm(0)
        result["seconds"] = time.monotonic() - start
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        result["peak_rss_bytes"] = rss if sys.platform == "darwin" else rss * 1024
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")


if __name__ == "__main__":
    main()
