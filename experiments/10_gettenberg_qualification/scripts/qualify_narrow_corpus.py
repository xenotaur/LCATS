"""Reproduce narrow delivery bodies on the frozen 1,659-source cohort.

From lcats/: PYTHONPATH="$PWD/src" python ../experiments/10_gettenberg_qualification/scripts/qualify_narrow_corpus.py CATALOG_CACHE TEXT_CACHE NEW_OUTPUT_JSON
Uses existing decoded UTF-8 gzip sources (not original wire receipts), a pinned
catalog and immutable prior comparisons. No downloads, cache writes or story
publication. Derives context from actual resource selection, then runs production
cleanup/extraction/normalization. This is body qualification, not actual gather
yield, corpus acceptance, or an editorial judgment. Requires a committed product
tree and POSIX alarm; 600s total, gzip32MiB, Git30s. Output is exclusive outside
repository/cache roots. Input/pin errors produce no completed report; outcome
mismatches produce a completed nonqualified report and exit1. Helpers use no legacy
runtime imports. Historical results are never overwritten.
"""

import argparse
import collections
import contextlib
import io
import json
import pathlib
import signal
import socket
import subprocess
import time
from unittest import mock

from lcats.gatherers import gutenberg_source, parser
from lcats.gettenberg import cleanup, identifiers, lifecycle, resources
import audit_cleanup_causality
import audit_terminal_notice

EVIDENCE_REF = "b1254805c85bc34c0924e112732822c5e1436df5"


def timeout(*_):
    """Stop the finite census before exhausting the bounded run."""
    raise TimeoutError("600-second narrow census ceiling")


def main(argv=None):
    """Bind inputs and product bytes, then report every controlled outcome."""
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("catalog_cache", "text_cache", "output"):
        ap.add_argument(name, type=lambda value: pathlib.Path(value).resolve())
    args = ap.parse_args(argv)
    root = audit_terminal_notice.ROOT
    require, sha = audit_terminal_notice.require, audit_terminal_notice.sha
    require(not args.output.exists(), "output exists")
    for protected in (root, args.catalog_cache, args.text_cache):
        require(not args.output.is_relative_to(protected), "protected output")
    require(args.catalog_cache.is_dir() and args.text_cache.is_dir(), "missing caches")
    require(hasattr(signal, "SIGALRM"), "POSIX alarm required")
    old_handler = signal.signal(signal.SIGALRM, timeout)
    signal.alarm(600)
    started = time.monotonic()
    try:
        ref = (
            subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, timeout=30)
            .decode()
            .strip()
        )
        hashes = audit_cleanup_causality.product_tree_guard(root, ref)
        audit_cleanup_causality.product_import_guard(root, hashes)
        previous = {}
        prior_hashes = {}
        for kind in ("numeric", "terminal"):
            relative = f"experiments/10_gettenberg_qualification/results/gettenberg-{kind}-notice-audit-20261022/corpus-comparison.json.gz"
            compressed, raw = audit_terminal_notice.read_gzip(root / relative)
            require(
                compressed == audit_terminal_notice.git_source(EVIDENCE_REF, relative),
                "prior evidence changed",
            )
            data = json.loads(raw)
            require(
                data["completed"] and len(data["rows"]) == 1659,
                "incomplete prior cohort",
            )
            previous[kind] = {row["id"]: row for row in data["rows"]}
            require(len(previous[kind]) == 1659, "duplicate input ID")
            prior_hashes[kind] = sha(compressed)
        require(set(previous["numeric"]) == set(previous["terminal"]), "cohort changed")
        counts, rows = collections.Counter(), []
        routes = resources.GutenbergRoutes(
            "https://www.gutenberg.org/files/", "https://www.gutenberg.org/cache/epub/"
        )
        with mock.patch.object(
            socket, "socket", side_effect=AssertionError("network forbidden")
        ), lifecycle.CatalogManager(
            args.catalog_cache
        ).open() as catalog, contextlib.redirect_stdout(
            io.StringIO()
        ):
            archive = catalog.info["report"]["archive_sha256"]
            require(archive == data["catalog_archive_sha256"], "catalog changed")
            source = gutenberg_source.GutenbergStorySource(
                catalog, resources.ResourceStore(args.catalog_cache), routes=routes
            )
            for identifier, prior in previous["numeric"].items():
                compressed, raw = audit_terminal_notice.read_gzip(
                    args.text_cache / f"{identifier}.txt.gz"
                )
                require(
                    sha(compressed) == prior["cache_sha256"]
                    and sha(raw) == prior["decoded_utf8_sha256"],
                    "source changed",
                )
                corpus = pathlib.Path(previous["terminal"][identifier]["corpus_path"])
                require(
                    corpus.is_relative_to(root / "corpora/mass_quantities")
                    and sha(corpus.read_bytes()) == prior["corpus_sha256"],
                    "corpus changed",
                )
                meta = source.metadata(identifier)
                require(
                    meta is not None and meta.ebook.gutenberg_id == identifier,
                    "metadata identity changed",
                )
                for field in ("titles", "authors", "aliases"):
                    require(
                        list(getattr(meta, field)) == prior[field],
                        "metadata projection changed",
                    )
                # Use the same route/preferences as the production source adapter;
                # this is selection from metadata, not a cache hit or HTTP claim.
                selected = resources.select_routable_resource(
                    meta.ebook, routes=routes, preferences=gutenberg_source._PLAIN
                )
                require(selected.request is not None, "no routable resource")
                uri = meta.ebook.resources[selected.selection.source_index].uri
                try:
                    source_id = identifiers.ebook_id_from_url(uri)
                except ValueError:
                    context = None
                else:
                    context = cleanup.CleanupContext(source_id, identifier, meta.titles)
                result = cleanup.strip_boilerplate(raw.decode("utf8"), context=context)
                diagnostics = [d.code for d in result.diagnostics]
                refused = not result.changed and any(
                    code != "no_markers" for code in diagnostics
                )
                row = {
                    "id": identifier,
                    "resource_uri": uri,
                    "source_id": None if context is None else context.source_id,
                    "decoded_utf8_sha256": sha(raw),
                    "cache_sha256": sha(compressed),
                    "corpus_sha256": prior["corpus_sha256"],
                    "slice": [result.content_start, result.content_end],
                    "diagnostics": diagnostics,
                    "cleanup_refused": refused,
                }
                row["cleanup_matches_experiment"] = (
                    row["slice"] == prior["candidate_slice"]
                    and diagnostics == prior["diagnostics"]
                    and refused == prior["cleanup_refused"]
                )
                counts["inputs"] += 1
                counts["cleanup_matches_experiment"] += row[
                    "cleanup_matches_experiment"
                ]
                counts["context_available"] += context is not None
                counts["refused"] += refused
                if not refused:
                    body = parser.body_of_text(
                        audit_terminal_notice.norm(result.text),
                        list(meta.authors),
                        list(meta.aliases),
                        list(meta.titles),
                    )
                    cell = audit_terminal_notice.body_result(
                        body, meta, corpus.parent.name, parser, None
                    )
                    row["body"] = cell
                    row["body_matches_experiment"] = all(
                        cell[key] == prior.get("candidate", {}).get(key) for key in cell
                    )
                    row["legacy_equal"] = cell["normalized_sha256"] == prior.get(
                        "legacy_sha256"
                    )
                    counts["compared"] += 1
                    counts["body_matches_experiment"] += row["body_matches_experiment"]
                    counts["legacy_differences"] += not row["legacy_equal"]
                    counts["body_eligible"] += cell["baseline_body_rejection"] is None
                rows.append(row)
        require(
            audit_cleanup_causality.product_tree_guard(root, ref) == hashes,
            "product changed during run",
        )
        origins = audit_cleanup_causality.product_import_guard(root, hashes)
        qualified = (
            counts["cleanup_matches_experiment"] == 1659
            and counts["body_matches_experiment"] == counts["compared"] == 1646
            and counts["refused"] == 13
        )
        report = {
            "scope": __doc__,
            "completed": True,
            "qualified_reproduction": qualified,
            "release_accepted": False,
            "product_ref": ref,
            "product_tree_sha256": hashes,
            "loaded_modules": origins,
            "evidence_ref": EVIDENCE_REF,
            "prior_sha256": prior_hashes,
            "catalog_archive_sha256": archive,
            "runner_sha256": sha(pathlib.Path(__file__).read_bytes()),
            "helper_sha256": {
                m.__name__: sha(pathlib.Path(m.__file__).read_bytes())
                for m in (audit_terminal_notice, audit_cleanup_causality)
            },
            "summary": dict(counts),
            "rows": rows,
            "seconds": round(time.monotonic() - started, 3),
        }
        with args.output.open("x", encoding="utf8") as stream:
            json.dump(report, stream, indent=2)
            stream.write("\n")
        print(
            json.dumps({"qualified_reproduction": qualified, "summary": dict(counts)})
        )
        return 0 if qualified else 1
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


if __name__ == "__main__":
    raise SystemExit(main())
