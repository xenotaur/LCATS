"""Verify source-anchored narrative spans and actual temporary story publication.

From lcats/: python ../experiments/10_gettenberg_qualification/scripts/qualify_narrative_cases.py CATALOG_CACHE TEXT_CACHE CASES_JSON OUTPUT_JSON
CASES_JSON records reviewed opening/closing anchors and decoded-input hashes.
Read-only historical UTF-8 gzip inputs are not original HTTP representations.
No network or canonical writes: outputs live in an automatically removed temporary
collection. Requires POSIX SIGALRM; 120-second total ceiling. Existing reports are
never overwritten. Missing/ambiguous anchors, mismatched input hashes, publication
rejections or lost narrative fail nonzero with a JSON report. Eligibility
rejections remain per-case failed publication checks; other failures abort. A pass proves
these specific narrative spans survive, not corpus-wide editorial acceptance.
"""

import argparse
import contextlib
import dataclasses
import hashlib
import io
import importlib.util
import json
import pathlib
import signal
import socket
import tempfile
from unittest import mock

from lcats.gatherers import downloaders
from lcats.gatherers import gutenberg_source
from lcats.gatherers import normalization
from lcats.gatherers import parser
from lcats.gatherers import story_body
from lcats.gettenberg import cleanup
from lcats.gettenberg import lifecycle
from lcats.gettenberg import resources


def _load_corpus_helpers():
    """Load the adjacent import-safe runner even when imported through runpy."""
    path = pathlib.Path(__file__).with_name("qualify_cached_corpus.py")
    spec = importlib.util.spec_from_file_location("qualification_corpus_helpers", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


corpus = _load_corpus_helpers()


@dataclasses.dataclass(frozen=True)
class HistoricalText:
    """Duck-typed StoryText with honest decoded-cache provenance, no HTTP receipt."""

    book_id: int
    cleaned: cleanup.CleanupResult
    compressed_sha256: str
    decoded_sha256: str

    def provenance(self):
        return {
            "source_uri": f"https://www.gutenberg.org/ebooks/{self.book_id}",
            "input_kind": "historical_decoded_utf8_cache",
            "compressed_sha256": self.compressed_sha256,
            "decoded_utf8_sha256": self.decoded_sha256,
            "cleanup_policy": self.cleaned.policy_version,
        }


class HistoricalSource:
    """Use real catalog projection and historical text without ResourceStore seeding."""

    def __init__(self, source, text):
        self.source = source
        self.text = text

    def metadata(self, book_id):
        return self.source.metadata(book_id)

    def read(self, metadata):
        if metadata.ebook.gutenberg_id != self.text.book_id:
            raise ValueError("replay source ID mismatch")
        return self.text


def check_case(case, text_cache, source, output_root):
    """Check every character between independently reviewed narrative anchors."""
    book_id = case["id"]
    cached = corpus.cached_text(text_cache, book_id)
    if cached is None:
        raise ValueError(f"missing cached input: {book_id}")
    text, compressed_sha, decoded_sha = cached
    if decoded_sha != case["decoded_utf8_sha256"]:
        raise ValueError(f"source identity mismatch: {book_id}")
    cleaned = cleanup.strip_boilerplate(text)
    if not cleaned.changed and any(d.code != "no_markers" for d in cleaned.diagnostics):
        raise ValueError(f"cleanup refused: {book_id}")
    normalized = cleaned.text.replace("\r\n", "\n").replace("\r", "\n")
    opening, closing = case["opening_anchor"], case["closing_anchor"]
    if normalized.count(opening) != 1 or normalized.count(closing) != 1:
        raise ValueError(f"missing/ambiguous narrative anchor: {book_id}")
    start, end = normalized.index(opening), normalized.index(closing) + len(closing)
    if start >= end:
        raise ValueError(f"reversed narrative anchors: {book_id}")
    narrative = normalized[start:end]
    replay = HistoricalSource(
        source, HistoricalText(book_id, cleaned, compressed_sha, decoded_sha)
    )
    report = parser.inspect_story(book_id, source=replay)
    if report["body"] is None or narrative not in report["body"]:
        raise ValueError(
            f"narrative missing or rejected: {book_id}: {report['rejection']}"
        )
    row = {
        "id": book_id,
        "source_identity_verified": True,
        "narrative_span": [start, end],
        "narrative_characters": len(narrative),
        "narrative_sha256": corpus.digest(narrative),
        "complete_span_preserved": True,
        "publication_preserves_normalized_span": False,
        "existing_output_unchanged": None,
        "rejection": report["rejection"],
        "body_characters": len(report["body"]),
        "provenance": report["provenance"],
    }
    # Preserve rejection as a failed publication check, while still measuring
    # the narrative span and proceeding to the remaining independently selected
    # cases. Completion of the audit is not acceptance of these changed outputs.
    if report["rejection"] is not None:
        return row
    gatherer = downloaders.DataGatherer("mass_quantities", root=output_root)
    pathlib.Path(gatherer.path).mkdir(parents=True, exist_ok=True)
    _, path, rejection = parser.gather_story(gatherer, book_id, source=replay)
    if rejection or path is None:
        raise ValueError(f"publication rejected: {book_id}: {rejection}")
    published_bytes = pathlib.Path(path).read_bytes()
    published = json.loads(published_bytes)
    normalized_narrative, _ = normalization.normalize_body(narrative)
    if normalized_narrative not in published["body"]:
        raise ValueError(f"publication/normalization lost narrative: {book_id}")
    if published["metadata"]["gettenberg"] != report["provenance"]:
        raise ValueError(f"publication provenance differs: {book_id}")
    parser.gather_story(gatherer, book_id, source=replay)
    if pathlib.Path(path).read_bytes() != published_bytes:
        raise ValueError(f"existing temporary output changed: {book_id}")
    return {
        **row,
        "publication_preserves_normalized_span": True,
        "existing_output_unchanged": True,
    }


def timeout(*_):
    raise TimeoutError("narrative-case qualification exceeded 120 seconds")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("catalog_cache", "text_cache", "cases", "output"):
        ap.add_argument(name, type=lambda value: pathlib.Path(value).resolve())
    args = ap.parse_args(argv)
    if args.output.exists():
        ap.error("output exists")
    if not hasattr(signal, "SIGALRM"):
        ap.error("POSIX SIGALRM required")
    result = {"completed": False, "scope": __doc__, "network_bytes": 0, "cases": []}
    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(120)
    try:
        cases_bytes = args.cases.read_bytes()
        cases = json.loads(cases_bytes)["cases"]
        if not cases or len(cases) > 100 or len({c["id"] for c in cases}) != len(cases):
            raise ValueError("cases must contain 1–100 unique ebook IDs")
        result["cases_sha256"] = corpus.digest(cases_bytes)
        result["source_sha256"] = {
            str(path): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (
                pathlib.Path(__file__),
                pathlib.Path(corpus.__file__),
                pathlib.Path(parser.__file__),
                pathlib.Path(story_body.__file__),
                pathlib.Path(normalization.__file__),
            )
        }
        with (
            lifecycle.CatalogManager(args.catalog_cache).open() as catalog,
            tempfile.TemporaryDirectory() as output_directory,
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
            for case in cases:
                result["cases"].append(
                    check_case(
                        case, args.text_cache, source, pathlib.Path(output_directory)
                    )
                )
        result["completed"] = True
        result["all_publication_checks_passed"] = all(
            row["publication_preserves_normalized_span"] for row in result["cases"]
        )
    except BaseException as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        signal.alarm(0)
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")

    return 0 if result.get("all_publication_checks_passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
