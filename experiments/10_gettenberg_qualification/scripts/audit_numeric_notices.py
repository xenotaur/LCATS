"""Replay a metadata-corroborated numeric-notice candidate on all 1,659 inputs.

From lcats/, historical project environment, PYTHONPATH=src:
python ../experiments/10_gettenberg_qualification/scripts/audit_numeric_notices.py CATALOG_CACHE TEXT_CACHE /tmp/NEW_REPORT.json

Reuse pinned prior legacy/replacement/title-candidate measurements, then actually
execute the combined candidate for every non-refused input with the SAME historical
extractor. Bind cached source/corpus bytes, metadata and imported module identities.
No catalog setup, downloads, cache/corpus writes or publication. Sockets denied while
processing; POSIX alarm600s, Git30s, gzip32MiB bounds inherited from audit helper.
Output must be new, outside repository/cache roots; failures emit no completed report.
Historical measurement environment requires gutenbergpy via shared helper, never a
production dependency. Progress goes to stderr every200rows; report stores no stories.
"""

import argparse
import collections
import contextlib
import importlib.util
import io
import json
import pathlib
import signal
import socket
import sys
import tempfile
import time
from unittest import mock

from lcats.gatherers import gutenberg_source, normalization
from lcats.gettenberg import cleanup, lifecycle, resources
import audit_terminal_notice
import numeric_notice_candidate
import terminal_notice_candidate

EVIDENCE_REF = "1488c69ab11fad8fcd78361653bbd261a2788680"


def timeout(*_):
    """Keep the full comparison inside the cafe hard-stop reserve."""
    raise TimeoutError("600-second numeric-notice experiment ceiling")


def main():
    """Rebind prior evidence, execute each candidate and report unresolved cases."""
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("catalog_cache", "text_cache", "output"):
        ap.add_argument(name, type=lambda value: pathlib.Path(value).resolve())
    args = ap.parse_args()
    require = audit_terminal_notice.require
    sha = audit_terminal_notice.sha
    root = audit_terminal_notice.ROOT
    require(not args.output.exists(), "output exists")
    for protected in (root, args.catalog_cache, args.text_cache):
        require(
            not args.output.is_relative_to(protected), "output inside protected root"
        )
    require(
        args.catalog_cache.is_dir() and args.text_cache.is_dir(),
        "existing caches required",
    )
    require(hasattr(signal, "SIGALRM"), "POSIX alarm required")
    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(600)
    start = time.monotonic()
    relative = "experiments/10_gettenberg_qualification/results/gettenberg-terminal-notice-audit-20261022/corpus-comparison.json.gz"
    compressed, raw = audit_terminal_notice.read_gzip(root / relative)
    require(
        compressed == audit_terminal_notice.git_source(EVIDENCE_REF, relative),
        "prior comparison changed",
    )
    prior = json.loads(raw)
    require(
        prior["completed"]
        and len(prior["rows"]) == len({r["id"] for r in prior["rows"]}) == 1659,
        "wrong cohort",
    )
    script_dir = root / "experiments/10_gettenberg_qualification/scripts"
    for module in (audit_terminal_notice, terminal_notice_candidate):
        path = pathlib.Path(module.__file__).resolve()
        require(path == script_dir / path.name, "wrong helper import")
        require(
            path.read_bytes()
            == audit_terminal_notice.git_source(
                EVIDENCE_REF, str(path.relative_to(root))
            ),
            "helper changed",
        )
    modules = {
        "gatherers/gutenberg_source.py": gutenberg_source,
        "gatherers/normalization.py": normalization,
        "gettenberg/cleanup.py": cleanup,
        "gettenberg/lifecycle.py": lifecycle,
        "gettenberg/resources.py": resources,
    }
    for relative, module in modules.items():
        path = pathlib.Path(module.__file__).resolve()
        require(path == root / "lcats/src/lcats" / relative, "wrong product import")
        require(
            sha(path.read_bytes()) == prior["runtime_modules"][relative]["sha256"],
            "product changed",
        )
    baseline_bytes = audit_terminal_notice.git_source(
        audit_terminal_notice.BASE, "lcats/src/lcats/gatherers/parser.py"
    )
    require(sha(baseline_bytes) == prior["baseline_parser_sha256"], "baseline changed")
    threshold = next(
        i
        for i, line in enumerate(baseline_bytes.decode().splitlines(), 1)
        if 'if len(final_body.split("\\n\\n")) > 10:' in line
    )
    report = {
        "scope": __doc__,
        "evidence_ref": EVIDENCE_REF,
        "prior_comparison_sha256": sha(compressed),
        "baseline_parser_ref": audit_terminal_notice.BASE,
        "baseline_parser_sha256": sha(baseline_bytes),
        "runtime_product_ref": prior["runtime_product_ref"],
        "runtime_modules": prior["runtime_modules"],
        "runner_sha256": sha(pathlib.Path(__file__).read_bytes()),
        "candidate_sha256": sha(
            pathlib.Path(numeric_notice_candidate.__file__).read_bytes()
        ),
        "helper_sha256": sha(pathlib.Path(audit_terminal_notice.__file__).read_bytes()),
        "title_candidate_sha256": sha(
            pathlib.Path(terminal_notice_candidate.__file__).read_bytes()
        ),
        "baseline_reuse": "Prior three cleanup paths reused; combined candidate freshly executed for all1646 accepted inputs.",
        "network_forbidden": True,
        "rows": [],
    }
    title_candidate = terminal_notice_candidate.load_candidate()
    counts = collections.Counter()
    with tempfile.TemporaryDirectory(prefix="gettenberg-numeric-module-") as temp:
        path = pathlib.Path(temp) / "baseline.py"
        path.write_bytes(baseline_bytes)
        spec = importlib.util.spec_from_file_location("numeric_baseline", path)
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
                report["catalog_archive_sha256"] == prior["catalog_archive_sha256"],
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
            for previous in prior["rows"]:
                identifier = previous["id"]
                compressed, raw = audit_terminal_notice.read_gzip(
                    args.text_cache / f"{identifier}.txt.gz"
                )
                require(
                    sha(compressed) == previous["cache_sha256"]
                    and sha(raw) == previous["decoded_utf8_sha256"],
                    "source changed",
                )
                corpus = pathlib.Path(previous["corpus_path"])
                require(
                    corpus.is_relative_to(root / "corpora/mass_quantities")
                    and sha(corpus.read_bytes()) == previous["corpus_sha256"],
                    "corpus changed",
                )
                meta = source.metadata(identifier)
                require(
                    meta.ebook.gutenberg_id == identifier, "metadata identity mismatch"
                )
                for key in ("titles", "authors", "aliases"):
                    require(
                        list(getattr(meta, key)) == previous[key],
                        "metadata projection changed",
                    )
                original = raw.decode("utf8")
                before = title_candidate.strip_boilerplate(original)
                require(
                    [before.content_start, before.content_end]
                    == previous["candidate_slice"]
                    and [d.code for d in before.diagnostics]
                    == previous["candidate_diagnostics"],
                    "title candidate changed",
                )
                after = numeric_notice_candidate.extend(
                    before,
                    source_id=identifier,
                    metadata_id=meta.ebook.gutenberg_id,
                    titles=meta.titles,
                )
                changed = after.content_end != before.content_end
                row = {
                    "id": identifier,
                    "decoded_utf8_sha256": sha(raw),
                    "cache_sha256": sha(compressed),
                    "corpus_sha256": previous["corpus_sha256"],
                    "metadata_id": meta.ebook.gutenberg_id,
                    "titles": list(meta.titles),
                    "authors": list(meta.authors),
                    "aliases": list(meta.aliases),
                    "prior_slice": [before.content_start, before.content_end],
                    "candidate_slice": [after.content_start, after.content_end],
                    "numeric_rule_applied": changed,
                    "diagnostics": [d.code for d in after.diagnostics],
                    "cleanup_refused": previous["candidate_refused"],
                }
                counts["rows"] += 1
                counts["numeric_rule_applied"] += changed
                if row["cleanup_refused"]:
                    require(after is before, "refusal changed")
                    counts["refused"] += 1
                else:
                    body, trace = audit_terminal_notice.trace_extract(
                        baseline,
                        after.text,
                        meta,
                        threshold,
                        identifier in (35401, 50103),
                    )
                    cell = audit_terminal_notice.body_result(
                        body, meta, corpus.parent.name, baseline, None
                    )
                    if trace is not None:
                        cell["trace"] = trace
                    row["candidate"] = cell
                    old = previous["contrasts"]["legacy"]
                    replacement = previous["contrasts"]["replacement"]
                    title = previous["contrasts"]["candidate"]
                    if not changed:
                        require(
                            cell["normalized_sha256"] == title["normalized_sha256"],
                            "unaffected output not reproduced",
                        )
                    row["legacy_sha256"] = old["normalized_sha256"]
                    row["prior_sha256"] = title["normalized_sha256"]
                    equal = cell["normalized_sha256"] == old["normalized_sha256"]
                    counts["compared"] += 1
                    counts["remaining_differences"] += not equal
                    counts["additional_legacy_equalities"] += (
                        not previous["old_candidate_equal"] and equal
                    )
                    counts["new_differences_from_prior_equal"] += (
                        previous["old_candidate_equal"] and not equal
                    )
                    counts["new_differences_from_original_equal"] += (
                        previous["old_new_equal"] and not equal
                    )
                    counts["body_changes_from_title_candidate"] += (
                        cell["normalized_sha256"] != title["normalized_sha256"]
                    )
                    counts["body_eligibility_changes_from_title_candidate"] += (
                        cell["baseline_body_rejection"]
                        != title["baseline_body_rejection"]
                    )
                    counts["body_eligibility_differences_from_legacy"] += (
                        cell["baseline_body_rejection"]
                        != old["baseline_body_rejection"]
                    )
                    counts["unchanged_outputs_reproduced"] += not changed
                    counts["combined_restored_legacy_equalities"] += (
                        replacement["normalized_sha256"] != old["normalized_sha256"]
                        and equal
                    )
                    if changed:
                        removed = original[after.content_end : before.content_end]
                        row["removed_suffix"] = {
                            "text": removed,
                            "characters": len(removed),
                            "sha256": sha(removed),
                        }
                report["rows"].append(row)
                if counts["rows"] % 200 == 0:
                    print(
                        f"verified {counts['rows']}/1659", file=sys.stderr, flush=True
                    )
    signal.alarm(0)
    report.update(
        summary=dict(counts), completed=True, seconds=round(time.monotonic() - start, 3)
    )
    with args.output.open("x", encoding="utf8") as stream:
        stream.write(json.dumps(report, indent=2) + "\n")
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
