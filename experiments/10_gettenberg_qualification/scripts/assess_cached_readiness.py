"""Census publication readiness on immutable historical decoded Gutenberg inputs.

From lcats/: python ../experiments/10_gettenberg_qualification/scripts/assess_cached_readiness.py CATALOG_CACHE TEXT_CACHE COLLECTION OUTPUT_JSON
No downloads, source/cache writes or story publication. Outputs must be new.
Uses the actual inspect_story contract, retaining per-input source/body identities,
readiness evidence and eligibility. Historical gzip UTF-8 is not original wire
bytes. POSIX only: a 600-second alarm bounds the run; <=10000 canonical inputs,
32MiB compressed/expanded text per input via the shared corpus helper. Missing
inputs or operational failures abort nonzero with a partial completed:false report.
Cleanup refusals are explicit rows, never successful story assessments.
"""

import argparse
import collections
import importlib.util
import json
import pathlib
import signal
import socket
import time
from unittest import mock

from lcats.analysis.corpus import discovery
from lcats.gatherers import gutenberg_source
from lcats.gatherers import parser
from lcats.gatherers import readiness
from lcats.gettenberg import cleanup
from lcats.gettenberg import identifiers
from lcats.gettenberg import lifecycle
from lcats.gettenberg import resources


def _helpers():
    path = pathlib.Path(__file__).with_name("qualify_narrative_cases.py")
    spec = importlib.util.spec_from_file_location("readiness_narrative_helpers", path)
    module = importlib.util.module_from_spec(spec)
    # Dataclass introspection needs the module registered before execution.
    import sys

    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


helpers = _helpers()


def assess_path(path, text_cache, source):
    """Assess one real candidate and retain provenance without duplicating bodies."""
    raw = path.read_bytes()
    saved = json.loads(raw)
    book_id = identifiers.ebook_id_from_url(saved["metadata"]["url"])
    cached = helpers.corpus.cached_text(text_cache, book_id)
    if cached is None:
        raise ValueError(f"missing cached source: {book_id}")
    text, compressed_sha, decoded_sha = cached
    row = dict(
        id=book_id,
        path=path.parent.name,
        corpus_sha256=readiness.text_sha256(raw.decode("utf-8")),
        compressed_sha256=compressed_sha,
        decoded_utf8_sha256=decoded_sha,
    )
    cleaned = cleanup.strip_boilerplate(text)
    if not cleaned.changed and any(d.code != "no_markers" for d in cleaned.diagnostics):
        return {
            **row,
            "status": "cleanup_refused",
            "diagnostics": [d.code for d in cleaned.diagnostics],
        }
    replay = helpers.HistoricalSource(
        source, helpers.HistoricalText(book_id, cleaned, compressed_sha, decoded_sha)
    )
    report = parser.inspect_story(book_id, source=replay)
    row.update(
        status=report["status"],
        rejection=report["rejection"],
        metadata=report["metadata"],
        provenance=report["provenance"],
        candidate_characters=None if report["body"] is None else len(report["body"]),
    )
    return row


def timeout(*_):
    raise TimeoutError("readiness census exceeded 600 seconds")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("catalog_cache", "text_cache", "collection", "output"):
        ap.add_argument(name, type=lambda v: pathlib.Path(v).resolve())
    args = ap.parse_args(argv)
    if args.output.exists():
        ap.error("output exists")
    if not hasattr(signal, "SIGALRM"):
        ap.error("POSIX SIGALRM required")
    result = {"completed": False, "network_bytes": 0, "rows": [], "scope": __doc__}
    start = time.monotonic()
    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(600)
    try:
        if not args.collection.is_dir():
            raise ValueError("collection missing")
        paths = sorted(discovery.iter_collection_story_files(args.collection))
        if not 0 < len(paths) <= 10000:
            raise ValueError("collection must have 1–10000 canonical inputs")
        result["source_sha256"] = {
            str(p): readiness.text_sha256(p.read_text(encoding="utf-8"))
            for p in sorted(pathlib.Path("src/lcats").rglob("*.py"))
        }
        result["runner_sha256"] = {
            p.name: readiness.text_sha256(p.read_text(encoding="utf-8"))
            for p in (
                pathlib.Path(__file__),
                pathlib.Path(helpers.__file__),
                pathlib.Path(helpers.corpus.__file__),
            )
        }
        with (
            lifecycle.CatalogManager(args.catalog_cache).open() as catalog,
            mock.patch.object(
                socket, "socket", side_effect=AssertionError("network forbidden")
            ),
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
            for path in paths:
                result["rows"].append(assess_path(path, args.text_cache, source))
        result["counts"] = dict(
            collections.Counter(row["status"] for row in result["rows"])
        )
        result["finding_counts"] = dict(
            collections.Counter(
                finding["kind"]
                for row in result["rows"]
                for finding in (row.get("provenance") or {})
                .get("publication_readiness", {})
                .get("findings", [])
            )
        )
        result["completed"] = True
    except BaseException as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        signal.alarm(0)
        result["elapsed_seconds"] = time.monotonic() - start
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
