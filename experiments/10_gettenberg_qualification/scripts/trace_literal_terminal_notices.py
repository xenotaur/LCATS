"""Replay two explicitly keyed footer-removal counterfactuals, not a general rule.

From LCATS/lcats, historical project environment:
PYTHONPATH=src python ../experiments/10_gettenberg_qualification/scripts/trace_literal_terminal_notices.py CATALOG_CACHE TEXT_CACHE /tmp/NEW_OUTPUT.json
Reads local cached decoded text/catalog and immutable archive. No acquisition or
publication. POSIX alarm 120s. Only a fresh output outside protected roots and a temporary module are written.
Output parent must exist; failures emit no completed report. Inputs are bounded
to32MiB by the shared helper, Git reads to30seconds; POSIX platform required.
Uses existing audit helpers but checks actual imported source bytes against Git.
"""

import argparse
import contextlib
import importlib.util
import io
import json
import pathlib
import signal
import socket
import tempfile
from unittest import mock
import audit_terminal_notice as audit
from lcats.gatherers import gutenberg_source, normalization
from lcats.gettenberg import cleanup, lifecycle, resources

# Reuse the corpus diagnostic's byte bounds, pinned-source reader and trace observer.
root = audit.ROOT
arguments = argparse.ArgumentParser(description=__doc__)
for name in ("catalog_cache", "text_cache", "output"):
    arguments.add_argument(name, type=lambda value: pathlib.Path(value).resolve())
args = arguments.parse_args()
output = args.output
for protected in (root, args.catalog_cache, args.text_cache):
    audit.require(not output.is_relative_to(protected), "output inside protected root")
audit.require(
    args.catalog_cache.is_dir() and args.text_cache.is_dir(), "existing caches required"
)
audit.require(not output.exists(), "output exists")


def timeout(*_):
    """Bound the exact two-input diagnostic without partial output."""
    raise TimeoutError("120-second literal-notice diagnostic ceiling")


signal.signal(signal.SIGALRM, timeout)
signal.alarm(120)
base = audit.git_source(audit.BASE, "lcats/src/lcats/gatherers/parser.py")
line = next(
    i
    for i, s in enumerate(base.decode().splitlines(), 1)
    if 'if len(final_body.split("\\n\\n")) > 10:' in s
)
archive_path = (
    root
    / "experiments/10_gettenberg_qualification/results/gettenberg-qualification-20261018/corpus-after.json.gz"
)
archive_bytes, archive_raw = audit.read_gzip(archive_path)
archive = json.loads(archive_raw)
old = {r["id"]: r for r in archive["rows"]}
audit.require(
    audit.sha(base) == archive["source_sha256"]["src/lcats/gatherers/parser.py"],
    "baseline changed",
)
# These two reviewed literal suffixes are diagnostic interventions, not a matcher.
# In particular, the numeric-marker case has NOT passed the candidate rule.
notes = {
    35401: "End of the Project Gutenberg EBook of Friend Island, by Francis Stevens",
    50103: "End of the Project Gutenberg EBook of The Dwindling Years, by Lester Del Rey",
}
report = {
    "scope": __doc__,
    "semantic_authority": "Two literal known-source diagnostic counterfactuals; not candidate grammar or product policy. No general rule, publication or story approval.",
    "baseline_parser_ref": audit.BASE,
    "baseline_parser_sha256": audit.sha(base),
    "runtime_product_ref": audit.PRODUCT,
    "helper_sha256": audit.sha(pathlib.Path(audit.__file__).read_bytes()),
    "runner_sha256": audit.sha(pathlib.Path(__file__).read_bytes()),
    "archived_comparison_sha256": audit.sha(archive_bytes),
    "runtime_modules": {},
    "rows": [],
}
for relative, module in {
    "gatherers/gutenberg_source.py": gutenberg_source,
    "gatherers/normalization.py": normalization,
    "gettenberg/cleanup.py": cleanup,
    "gettenberg/lifecycle.py": lifecycle,
    "gettenberg/resources.py": resources,
}.items():
    path = pathlib.Path(module.__file__).resolve()
    audit.require(path == root / "lcats/src/lcats" / relative, "wrong module path")
    expected = audit.git_source(audit.PRODUCT, "lcats/src/lcats/" + relative)
    audit.require(path.read_bytes() == expected, "changed module")
    report["runtime_modules"][relative] = {
        "path": str(path),
        "sha256": audit.sha(expected),
    }

with tempfile.TemporaryDirectory(prefix="notice-review-explicit-") as temporary:
    path = pathlib.Path(temporary) / "historical.py"
    path.write_bytes(base)
    spec = importlib.util.spec_from_file_location("notice_review_explicit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with mock.patch.object(
        socket, "socket", side_effect=AssertionError("no network")
    ), lifecycle.CatalogManager(
        args.catalog_cache
    ).open() as catalog, contextlib.redirect_stdout(
        io.StringIO()
    ):
        report["catalog_archive_sha256"] = catalog.info["report"]["archive_sha256"]
        audit.require(
            report["catalog_archive_sha256"] == archive["catalog_archive_sha256"],
            "catalog changed",
        )
        source = gutenberg_source.GutenbergStorySource(
            catalog,
            resources.ResourceStore(args.catalog_cache),
            routes=resources.GutenbergRoutes(
                "https://www.gutenberg.org/files/",
                "https://www.gutenberg.org/cache/epub/",
            ),
        )
        for book, note in notes.items():
            compressed, raw = audit.read_gzip(args.text_cache / f"{book}.txt.gz")
            audit.require(
                audit.sha(raw) == old[book]["decoded_utf8_sha256"],
                "decoded source changed",
            )
            audit.require(
                audit.sha(compressed) == old[book]["cache_sha256"], "cache changed"
            )
            text = raw.decode()
            meta = source.metadata(book)
            audit.require(
                list(meta.titles) == old[book]["titles"]
                and list(meta.authors) == old[book]["authors"],
                "metadata changed",
            )
            cleaned = cleanup.strip_boilerplate(text)
            audit.require(cleaned.text.count(note) == 1, "literal notice not unique")
            # Terminal uniqueness is required even for an explicitly named probe.
            offset = cleaned.text.index(note)
            audit.require(
                not cleaned.text[offset + len(note) :].strip(), "notice not terminal"
            )
            body, trace = audit.trace_extract(
                module, cleaned.text[:offset], meta, line, True
            )
            cell = audit.body_result(
                body, meta, pathlib.Path(old[book]["path"]).parent.name, module, None
            )
            audit.require(
                cell["normalized_sha256"] == old[book]["normalized_before_sha256"],
                "legacy output not reproduced",
            )
            report["rows"].append(
                {
                    "id": book,
                    "decoded_utf8_sha256": audit.sha(raw),
                    "cache_sha256": audit.sha(compressed),
                    "titles": list(meta.titles),
                    "authors": list(meta.authors),
                    "aliases": list(meta.aliases),
                    "note": note,
                    "removed_raw_span": [
                        cleaned.content_start + offset,
                        cleaned.content_end,
                    ],
                    "removed_suffix_sha256": audit.sha(cleaned.text[offset:]),
                    "removed_suffix_characters": len(cleaned.text[offset:]),
                    "restores_archived_legacy_normalized_hash": True,
                    "result": cell,
                    "trace": trace,
                }
            )
signal.alarm(0)
report["completed"] = True
with output.open("x") as stream:
    json.dump(report, stream, indent=2)
    stream.write("\n")
print(json.dumps({"output": str(output), "sha256": audit.sha(output.read_bytes())}))
