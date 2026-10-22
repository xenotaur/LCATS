"""Measure one terminal-notice grammar extension on the frozen 1,659-input cohort.

From lcats/, historical project environment, PYTHONPATH=src:
python ../experiments/10_gettenberg_qualification/scripts/audit_terminal_notice.py CATALOG_CACHE TEXT_CACHE /tmp/NEW_REPORT.json

All three cleanup paths use the SAME pinned pre-repair body extractor and current
metadata/normalization. Existing decoded UTF-8 gzip cache entries are not original
HTTP bytes. No downloads, catalog setup, cache writes or story publication. Socket
creation is forbidden during processing. Requires already-installed historical
Gutenbergpy for comparison only; never adds a product dependency. POSIX alarm 900s,
Git timeout 30s, gzip inputs 32MiB compressed/expanded. Output is exclusive and must
be outside repo/cache roots; failure emits no completed report. Temporary historical
module is removed. Tests and interpretation: terminal-notice results README.
"""

import argparse
import collections
import contextlib
import gzip
import hashlib
import importlib.util
import io
import json
import pathlib
import signal
import socket
import subprocess
import sys
import tempfile
import time
from unittest import mock

from lcats.gatherers import gutenberg_source, normalization
from lcats.gettenberg import cleanup, lifecycle, resources
import terminal_notice_candidate

ROOT = pathlib.Path(__file__).resolve().parents[3]
RESULTS = ROOT / "experiments/10_gettenberg_qualification/results"
BASE = "335855c04cd7ba936815d2635969d94fdd278c71"
PRODUCT = "6a873b611e3958bb9ddad8e84f2ad190831a9da7"
MAX_BYTES = 32 * 1024**2


def sha(data):
    """Identify exact bytes; string encoding does not imply transport provenance."""
    return hashlib.sha256(data.encode() if isinstance(data, str) else data).hexdigest()


def require(condition, message):
    """Keep evidence checks active under optimized Python."""
    if not condition:
        raise ValueError(message)


def read_gzip(path):
    """Bound both compressed input and gzip expansion before decoding."""
    require(path.stat().st_size <= MAX_BYTES, "compressed input exceeds 32 MiB")
    compressed = path.read_bytes()
    with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:
        raw = stream.read(MAX_BYTES + 1)
    require(len(raw) <= MAX_BYTES, "expanded input exceeds 32 MiB")
    return compressed, raw


def git_source(ref, relative):
    """Read a pinned local source without checking out or modifying any branch."""
    return subprocess.check_output(
        ["git", "show", f"{ref}:{relative}"], cwd=ROOT, timeout=30
    )


def norm(text):
    """Apply the historical physical-newline boundary identically on all paths."""
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def trace_extract(module, text, metadata, threshold_line, enabled):
    """Capture the first candidate and author/title selections for two probes.

    The observer never changes frame locals or parser behavior. Chunk counts include
    empty chunks: they must not be described as narrative-paragraph counts. Full
    candidate text stays transient; only hashes, counts and bounded matches persist.
    """
    trace = {"heading_matches": []}

    def observer(frame, event, value):
        if frame.f_code.co_filename != module.__file__:
            return observer
        name = frame.f_code.co_name
        local = frame.f_locals
        if (
            name == "body_of_text"
            and event == "line"
            and frame.f_lineno == threshold_line
        ):
            candidate = local["final_body"]
            trace.update(
                first_candidate_characters=len(candidate),
                first_candidate_sha256=sha(candidate),
                first_candidate_chunks=len(candidate.split("\n\n")),
                first_candidate_tail=candidate[-250:],
                fallback_taken=len(candidate.split("\n\n")) <= 10,
            )
        if event == "return" and name in ("find_author_line", "find_title_line"):
            pieces = local["text_array"]
            trace["heading_matches"].append(
                {
                    "function": name,
                    "triple_newline": local["three_newlines_flag"],
                    "chunk_count": len(pieces),
                    "selected_index": value,
                    "selected_text": pieces[value][:400] if value >= 0 else None,
                }
            )
        return observer

    prior = sys.gettrace()
    if enabled:
        sys.settrace(observer)
    try:
        body = module.body_of_text(
            norm(text),
            list(metadata.authors),
            list(metadata.aliases),
            list(metadata.titles),
        )
    finally:
        if enabled:
            sys.settrace(prior)
    return body, trace if enabled else None


def body_result(body, meta, slug, baseline, narrative):
    """Measure exact extraction, historical eligibility and bucket normalization."""
    data = {
        "name": meta.titles[0],
        "author": list(meta.authors),
        "body": body,
        "metadata": {},
    }
    normalization.normalize_story_dict(
        data, collection="mass_quantities", story_id=slug
    )
    chaptered = baseline.chaptered(body)
    chunks = len(body.split("\n\n"))
    return {
        "extracted_sha256": sha(body),
        "extracted_characters": len(body),
        "normalized_sha256": sha(data["body"]),
        "normalized_characters": len(data["body"]),
        "baseline_chaptered": chaptered,
        "baseline_chunk_count": chunks,
        "baseline_body_rejection": (
            "chapters" if chaptered else "short" if chunks <= 10 else None
        ),
        "exact_anchor_interval_preserved": (
            None if narrative is None else narrative in body
        ),
    }


def timeout(*_):
    """Bound this finite diagnostic without leaving a false completed report."""
    raise TimeoutError("900-second terminal-notice investigation ceiling")


def main():
    """Replay all archived rows; fail on changed inputs or unreproduced baselines."""
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("catalog_cache", "text_cache", "output"):
        ap.add_argument(name, type=lambda value: pathlib.Path(value).resolve())
    args = ap.parse_args()
    # Historical comparison only; normal imports and help must not require it.
    from gutenbergpy import textget

    require(not args.output.exists(), "output exists; evidence is never overwritten")
    for protected in (ROOT, args.catalog_cache, args.text_cache):
        require(
            not args.output.is_relative_to(protected), "output inside protected root"
        )
    require(
        args.catalog_cache.is_dir() and args.text_cache.is_dir(),
        "existing caches required",
    )
    require(hasattr(signal, "SIGALRM"), "POSIX alarm required")
    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(900)
    start = time.monotonic()
    old_path = RESULTS / "gettenberg-qualification-20261018/corpus-after.json.gz"
    old_bytes, old_raw = read_gzip(old_path)
    old = json.loads(old_raw)
    require(
        len(old["rows"]) == len({r["id"] for r in old["rows"]}) == 1659, "wrong cohort"
    )
    cases_path = RESULTS / "gettenberg-narrative-20261018/narrative-cases.json"
    cases = {r["id"]: r for r in json.loads(cases_path.read_bytes())["cases"]}
    baseline_bytes = git_source(BASE, "lcats/src/lcats/gatherers/parser.py")
    require(
        sha(baseline_bytes) == old["source_sha256"]["src/lcats/gatherers/parser.py"],
        "wrong baseline",
    )
    require(
        sha(pathlib.Path(textget.__file__).read_bytes())
        == old["legacy_cleaner_sha256"],
        "wrong legacy cleaner",
    )
    report = {
        "scope": __doc__,
        "baseline_parser_ref": BASE,
        "runtime_product_ref": PRODUCT,
        "baseline_parser_sha256": sha(baseline_bytes),
        "legacy_cleaner_sha256": old["legacy_cleaner_sha256"],
        "archived_comparison_sha256": sha(old_bytes),
        "case_file_sha256": sha(cases_path.read_bytes()),
        "runner_sha256": sha(pathlib.Path(__file__).read_bytes()),
        "candidate_sha256": sha(
            pathlib.Path(terminal_notice_candidate.__file__).read_bytes()
        ),
        "candidate_pattern": terminal_notice_candidate.PATTERN,
        "head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, timeout=30
        ).strip(),
        "network_forbidden": True,
        "runtime_modules": {},
        "rows": [],
    }
    # Hash executing module locations, not just unrelated files in the worktree.
    for relative, module in {
        "gatherers/gutenberg_source.py": gutenberg_source,
        "gatherers/normalization.py": normalization,
        "gettenberg/cleanup.py": cleanup,
        "gettenberg/lifecycle.py": lifecycle,
        "gettenberg/resources.py": resources,
    }.items():
        path = pathlib.Path(module.__file__).resolve()
        require(
            path == ROOT / "lcats/src/lcats" / relative,
            f"wrong imported module: {relative}",
        )
        expected = git_source(PRODUCT, "lcats/src/lcats/" + relative)
        require(path.read_bytes() == expected, f"changed runtime module: {relative}")
        report["runtime_modules"][relative] = {
            "path": str(path),
            "sha256": sha(expected),
        }
    candidate = terminal_notice_candidate.load_candidate()
    threshold_lines = [
        i
        for i, line in enumerate(baseline_bytes.decode().splitlines(), 1)
        if 'if len(final_body.split("\\n\\n")) > 10:' in line
    ]
    require(len(threshold_lines) == 1, "threshold trace anchor changed")
    summary = collections.Counter()
    with tempfile.TemporaryDirectory(prefix="gettenberg-notice-module-") as temp:
        path = pathlib.Path(temp) / "baseline_parser.py"
        path.write_bytes(baseline_bytes)
        spec = importlib.util.spec_from_file_location("notice_baseline_parser", path)
        baseline = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(baseline)
        with mock.patch.object(
            socket, "socket", side_effect=AssertionError("network forbidden")
        ), lifecycle.CatalogManager(
            args.catalog_cache
        ).open() as catalog, contextlib.redirect_stdout(
            io.StringIO()
        ):
            report["catalog_archive_sha256"] = catalog.info["report"]["archive_sha256"]
            require(
                report["catalog_archive_sha256"] == old["catalog_archive_sha256"],
                "catalog identity mismatch",
            )
            source = gutenberg_source.GutenbergStorySource(
                catalog,
                resources.ResourceStore(args.catalog_cache),
                routes=resources.GutenbergRoutes(
                    "https://www.gutenberg.org/files/",
                    "https://www.gutenberg.org/cache/epub/",
                ),
            )
            for previous in old["rows"]:
                identifier = previous["id"]
                compressed, raw = read_gzip(args.text_cache / f"{identifier}.txt.gz")
                require(
                    sha(compressed) == previous["cache_sha256"]
                    and sha(raw) == previous["decoded_utf8_sha256"],
                    f"source changed: {identifier}",
                )
                corpus_path = pathlib.Path(previous["path"])
                require(
                    corpus_path.is_relative_to(ROOT / "corpora/mass_quantities"),
                    "corpus path outside collection",
                )
                require(
                    sha(corpus_path.read_bytes()) == previous["corpus_sha256"],
                    f"corpus changed: {identifier}",
                )
                meta = source.metadata(identifier)
                require(
                    list(meta.titles) == previous["titles"]
                    and list(meta.authors) == previous["authors"],
                    "metadata changed",
                )
                text = raw.decode("utf8")
                actual = cleanup.strip_boilerplate(text)
                proposed = candidate.strip_boilerplate(text)
                diagnostics = [d.code for d in actual.diagnostics]
                proposed_diagnostics = [d.code for d in proposed.diagnostics]
                refused = not actual.changed and any(
                    d != "no_markers" for d in diagnostics
                )
                proposed_refused = not proposed.changed and any(
                    d != "no_markers" for d in proposed_diagnostics
                )
                require(
                    diagnostics == previous["cleanup_diagnostics"],
                    "cleanup diagnostics changed",
                )
                require(
                    ("cleanup_refused" if refused else "compared")
                    == previous["status"],
                    "archived status changed",
                )
                row = {
                    "id": identifier,
                    "corpus_sha256": previous["corpus_sha256"],
                    "corpus_path": str(corpus_path),
                    "cache_sha256": sha(compressed),
                    "decoded_utf8_sha256": sha(raw),
                    "titles": list(meta.titles),
                    "authors": list(meta.authors),
                    "aliases": list(meta.aliases),
                    "cleanup_diagnostics": diagnostics,
                    "candidate_diagnostics": proposed_diagnostics,
                    "cleanup_slice": [actual.content_start, actual.content_end],
                    "candidate_slice": [proposed.content_start, proposed.content_end],
                    "candidate_changed_cleanup": actual.text != proposed.text,
                    "cleanup_refused": refused,
                    "candidate_refused": proposed_refused,
                    "contrasts": {},
                }
                summary["rows"] += 1
                summary["refusal_changes"] += refused != proposed_refused
                summary["candidate_changed_cleanup"] += row["candidate_changed_cleanup"]
                if refused or proposed_refused:
                    summary["refused"] += 1
                    report["rows"].append(row)
                    continue
                narrative = None
                if identifier in cases:
                    case = cases[identifier]
                    require(
                        sha(raw) == case["decoded_utf8_sha256"], "anchor input changed"
                    )
                    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
                    opening, closing = case["opening_anchor"], case["closing_anchor"]
                    require(
                        normalized.count(opening) == normalized.count(closing) == 1,
                        "anchors not unique",
                    )
                    narrative = normalized[
                        normalized.index(opening) : normalized.index(closing)
                        + len(closing)
                    ]
                for label, cleaned in {
                    "legacy": textget.strip_headers(raw).decode("utf8"),
                    "replacement": actual.text,
                    "candidate": proposed.text,
                }.items():
                    body, trace = trace_extract(
                        baseline,
                        cleaned,
                        meta,
                        threshold_lines[0],
                        identifier in (35401, 50103),
                    )
                    cell = body_result(
                        body, meta, corpus_path.parent.name, baseline, narrative
                    )
                    if trace is not None:
                        cell["trace"] = trace
                    row["contrasts"][label] = cell
                cells = row["contrasts"]
                for label, key in (
                    ("legacy", "normalized_before_sha256"),
                    ("replacement", "normalized_after_sha256"),
                ):
                    require(
                        cells[label]["normalized_sha256"] == previous[key],
                        f"unreproduced {label} output: {identifier}",
                    )
                    summary["archived_hashes_reproduced"] += 1
                old_hash, new_hash, candidate_hash = [
                    cells[k]["normalized_sha256"]
                    for k in ("legacy", "replacement", "candidate")
                ]
                row["old_new_equal"] = old_hash == new_hash
                row["old_candidate_equal"] = old_hash == candidate_hash
                row["candidate_changed_body"] = new_hash != candidate_hash
                summary["compared"] += 1
                summary["old_new_differences"] += old_hash != new_hash
                summary["remaining_differences"] += old_hash != candidate_hash
                summary["restored_legacy_equality"] += (
                    old_hash != new_hash and old_hash == candidate_hash
                )
                summary["new_legacy_differences"] += (
                    old_hash == new_hash and old_hash != candidate_hash
                )
                summary["candidate_changed_body"] += new_hash != candidate_hash
                summary["body_eligibility_changes_from_replacement"] += (
                    cells["replacement"]["baseline_body_rejection"]
                    != cells["candidate"]["baseline_body_rejection"]
                )
                summary["body_eligibility_differences_from_legacy"] += (
                    cells["legacy"]["baseline_body_rejection"]
                    != cells["candidate"]["baseline_body_rejection"]
                )
                if row["candidate_changed_cleanup"]:
                    removed = text[proposed.content_end : actual.content_end]
                    row["removed_suffix"] = {
                        "sha256": sha(removed),
                        "characters": len(removed),
                        "text": removed[:1000],
                    }
                report["rows"].append(row)
    report.update(
        summary=dict(summary),
        seconds=round(time.monotonic() - start, 3),
        completed=True,
    )
    signal.alarm(0)
    with args.output.open("x", encoding="utf8") as output:
        output.write(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "summary": report["summary"],
                "seconds": report["seconds"],
            }
        )
    )


if __name__ == "__main__":
    main()
