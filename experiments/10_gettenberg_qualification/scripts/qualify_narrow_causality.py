"""Account for the 67 narrow-cleaner contrasts and 13 explicit refusals.

From lcats/, historical LCATS experiment environment with absolute PYTHONPATH=src:
python ../experiments/10_gettenberg_qualification/scripts/qualify_narrow_causality.py CATALOG_CACHE TEXT_CACHE /tmp/NEW_REPORT.json

This offline experiment requires the already-installed, SHA-pinned gutenbergpy
cleaner ONLY as a historical comparator. It does not add a product dependency.
Both cleaners receive identical decoded historical cache bytes, catalog metadata,
current parser and normalization. It is not a replay of historical HTTP acquisition
or historical catalog selection. It changes no product code, cache or corpus.

For each residual it records source/metadata/body identities and exact change
intervals. Diagnostic counterfactuals change only cleanup boundaries in memory;
they are neither a proposed cleanup rule nor publication/acceptance authorization.
The report distinguishes causal accounting from editorial and delivery acceptance.
The other 1,579 equal cases are accounted for by the pinned prior full census.

Inputs are pinned Git evidence, the existing catalog and <=32MiB gzip sources.
POSIX alarm:900s, Git:30s. Socket creation is forbidden during input processing.
New output must be outside repository/cache roots and is created exclusively only
on success. Failures produce no completed report. Test with the sibling unittest
file; format/lint this experiment explicitly. No original transport claims.
"""

import argparse
import collections
import contextlib
import dataclasses
import difflib
import inspect
import io
import json
import pathlib
import re
import signal
import socket
import subprocess
import sys
import time
from unittest import mock

from lcats.gatherers import gutenberg_source, normalization, parser
from lcats.gettenberg import cleanup, lifecycle, resources
import audit_cleanup_causality
import audit_terminal_notice

ROOT = audit_terminal_notice.ROOT
RESULTS = ROOT / "experiments/10_gettenberg_qualification/results"
PRODUCT = "91f1b42281418d613bc1744b77ada73b42405bfc"
EVIDENCE = "95ad5afddc6841c6f7946c7ae43fd98b6f39b25f"
BASE_PARSER = "335855c04cd7ba936815d2635969d94fdd278c71"
NOTICE = re.compile(r"^End of (?:the |The )?Project Gutenberg", re.MULTILINE)
sha = audit_terminal_notice.sha
require = audit_terminal_notice.require


def timeout(*_):
    """Leave no successful-looking result after the bounded experiment expires."""
    raise TimeoutError("900-second causal-ledger ceiling")


def describe(text, limit=700):
    """Keep exact identities and lengths with a bounded human-readable excerpt."""
    return {
        "characters": len(text),
        "sha256": sha(text),
        "excerpt": text[:limit],
        "excerpt_truncated": len(text) > limit,
    }


def delta(before, after):
    """Return one exact replacement interval, without fuzzy text alignment.

    Common prefix/suffix removal is linear and lossless. A mixed interval may
    contain unchanged text; it is not represented as a minimal semantic diff.
    Empty bodies cannot establish narrative preservation by substring vacuity.
    """
    prefix = 0
    while prefix < min(len(before), len(after)) and before[prefix] == after[prefix]:
        prefix += 1
    suffix = 0
    bound = min(len(before), len(after)) - prefix
    while suffix < bound and before[-suffix - 1] == after[-suffix - 1]:
        suffix += 1
    old_end, new_end = len(before) - suffix, len(after) - suffix
    old_piece, new_piece = before[prefix:old_end], after[prefix:new_end]
    if before == after:
        shape = "equal"
    elif before and after.startswith(before):
        shape = "suffix_extension"
    elif before and after.endswith(before):
        shape = "prefix_extension"
    else:
        shape = "mixed"
    return {
        "shape": shape,
        "before_span": [prefix, old_end],
        "after_span": [prefix, new_end],
        "removed": describe(old_piece),
        "added": describe(new_piece),
        "equal_after_strip": before.strip() == after.strip(),
        "whole_before_preserved": bool(before) and before in after,
    }


def source_excerpt(text, start, end):
    """Bind a measured physical-source interval and show its boundary context."""
    return {
        "span": [start, end],
        **describe(text[start:end]),
        "preceding": text[max(0, start - 100) : start],
        "following": text[end : end + 100],
    }


def legacy_clean(textget, raw):
    """Observe the pinned cleaner's actual resets/footer without changing locals.

    The counter follows bytes.splitlines(), exactly the cleaner's iteration.
    Python text.splitlines() has additional Unicode boundaries and is therefore
    deliberately not substituted. Character offsets are derived after each
    original UTF-8 byte prefix is decoded, not guessed from byte positions.
    """
    lines, first = inspect.getsourcelines(textget.strip_headers)
    anchors = {}
    for key, line in {
        "iteration": "reset = False",
        "reset": "if reset:",
        "footer": "if footer_found:",
    }.items():
        hits = [first + i for i, value in enumerate(lines) if value.strip() == line]
        require(len(hits) == 1, f"legacy trace anchor changed: {key}")
        anchors[key] = hits[0]
    physical = raw.splitlines(keepends=True)
    offsets, position = [], 0
    for line in physical:
        offsets.append(position)
        position += len(line)
    records, number = [], -1

    def observer(frame, event, _):
        nonlocal number
        if frame.f_code is textget.strip_headers.__code__ and event == "line":
            if frame.f_lineno == anchors["iteration"]:
                number += 1
            kind = None
            if frame.f_lineno == anchors["reset"] and frame.f_locals["reset"]:
                kind = "header_reset"
            if frame.f_lineno == anchors["footer"] and frame.f_locals["footer_found"]:
                kind = "footer_stop"
            if kind:
                start = len(raw[: offsets[number]].decode("utf8"))
                line = frame.f_locals["line"].decode("utf8")
                records.append(
                    {
                        "kind": kind,
                        "physical_line": number + 1,
                        "source_span": [start, start + len(line)],
                        "processed_line_counter": frame.f_locals["i"],
                        "text": line,
                    }
                )
        return observer

    previous = sys.gettrace()
    sys.settrace(observer)
    try:
        result = textget.strip_headers(raw).decode("utf8")
    finally:
        sys.settrace(previous)
    return result, records


def extract(text, meta, slug, trace=False):
    """Use the unchanged extractor and publication normalization on every path."""
    lines = pathlib.Path(parser.__file__).read_text().splitlines()
    anchors = [
        i
        for i, value in enumerate(lines, 1)
        if 'if len(final_body.split("\\n\\n")) > 10:' in value
    ]
    require(len(anchors) == 1, "parser trace anchor changed")
    body, observed = audit_terminal_notice.trace_extract(
        parser, text, meta, anchors[0], trace
    )
    metrics = audit_terminal_notice.body_result(body, meta, slug, parser, None)
    data = {
        "name": meta.titles[0],
        "author": list(meta.authors),
        "body": body,
        "metadata": {},
    }
    normalization.normalize_story_dict(
        data, collection="mass_quantities", story_id=slug
    )
    if observed is not None:
        metrics["trace"] = observed
    return data["body"], metrics


def refusal_group(result, text):
    """Describe observed syntax; do not turn malformed evidence into acceptance."""
    codes = [item.code for item in result.diagnostics]
    if codes == ["mismatched_pair"]:
        return "different_envelope_identifiers"
    if codes == ["unverified_header"]:
        return "first_nonblank_line_is_not_supported_banner"
    unknown_markers = [m for m in result.markers if m.kind == "unrecognized"]
    unknown = [text[m.start : m.end].strip() for m in unknown_markers]
    if unknown and all(line == "*END*" for line in unknown):
        return "interior_star_end_is_competing_marker"
    if (
        unknown
        and all(
            "PROJECT GUTENBERG EBOOK" in line.upper() and not line.endswith("***")
            for line in unknown
        )
        and all(
            re.split(r"\r\n|\r|\n", text[marker.end :], maxsplit=1)[0]
            .rstrip()
            .endswith("***")
            for marker in unknown_markers
        )
    ):
        return "wrapped_envelope_marker"
    return "other_refusal"


def body_group(old, new):
    """Group exact body effects without declaring additions harmless."""
    change = delta(old, new)
    if old and new and change["equal_after_strip"]:
        return "boundary_whitespace_only"
    if change["shape"] == "suffix_extension":
        added = new[len(old) :]
        notice = NOTICE.search(added)
        if notice:
            return (
                "terminal_notice_only"
                if not added[: notice.start()].strip()
                else "terminal_notice_and_preceding_content"
            )
    if change["shape"] == "prefix_extension":
        return "source_prefix_restored"
    return "mixed_front_and_tail_effect"


def mixed_hunks(before, after):
    """Expose exact changed line intervals for the one mixed residual.

    Matching is a presentation aid only: each returned interval is verified by
    direct slicing and hashes. It does not infer narrative boundaries or approval.
    """
    old_lines, new_lines = before.splitlines(keepends=True), after.splitlines(
        keepends=True
    )
    old_offsets, new_offsets = [0], [0]
    for line in old_lines:
        old_offsets.append(old_offsets[-1] + len(line))
    for line in new_lines:
        new_offsets.append(new_offsets[-1] + len(line))
    result = []
    for kind, left, right, new_left, new_right in difflib.SequenceMatcher(
        None, old_lines, new_lines, autojunk=False
    ).get_opcodes():
        if kind == "equal":
            continue
        old_span, new_span = [old_offsets[left], old_offsets[right]], [
            new_offsets[new_left],
            new_offsets[new_right],
        ]
        result.append(
            {
                "kind": kind,
                "before_span": old_span,
                "after_span": new_span,
                "removed": describe(before[slice(*old_span)]),
                "added": describe(after[slice(*new_span)]),
            }
        )
    return result


def preceding_content_probe(before, after, text, meta):
    """Isolate end-of-body filtering of content that precedes a retained notice.

    An authored sentinel plus exact source-backed content probes the unchanged
    fix_body function, independently of either cleaner. It diagnoses behavior,
    never publishes the probe or interprets a title match as valid removal.
    """
    addition = after[len(before) :]
    notice = NOTICE.search(addition)
    require(notice is not None, "expected retained notice")
    preceding = addition[: notice.start()].strip()
    normalized_source = audit_terminal_notice.norm(text)
    occurrence = normalized_source.find(preceding)
    matches = normalized_source.count(preceding)
    probe = "Sentinel narrative paragraph.\n\n" + preceding
    result = parser.fix_body(
        probe, list(meta.titles), list(meta.authors), list(meta.aliases)
    )
    return {
        "preceding_content": describe(preceding),
        "normalized_source_occurrences": matches,
        "normalized_source_span": (
            None if matches != 1 else [occurrence, occurrence + len(preceding)]
        ),
        "line_contains_title": parser.line_contains_title(preceding, list(meta.titles)),
        "line_contains_author": parser.line_contains_author(
            preceding, list(meta.authors), list(meta.aliases)
        ),
        "fix_body_probe_input_sha256": sha(probe),
        "fix_body_probe_result": describe(result),
        "entire_preceding_content_preserved": preceding in result,
        "scope": "authored sentinel plus exact preceding content, unchanged fix_body only; no cleanup or publication",
    }


def normalization_data_guard():
    """Bind the non-Python per-story input that normalization loads lazily."""
    relative = "lcats/src/lcats/gatherers/overrides/mass_quantities.json"
    expected = audit_terminal_notice.git_source(PRODUCT, relative)
    require(
        (ROOT / relative).read_bytes() == expected, "normalization overrides changed"
    )
    return {relative: sha(expected)}


def pinned_report(name):
    """Reject mutated historical evidence rather than silently reusing it."""
    path = RESULTS / name
    compressed, raw = audit_terminal_notice.read_gzip(path)
    relative = str(path.relative_to(ROOT))
    require(
        compressed == audit_terminal_notice.git_source(EVIDENCE, relative),
        "changed prior evidence",
    )
    report = json.loads(raw)
    require(
        report["completed"] and len(report["rows"]) == 1659, "incomplete prior report"
    )
    rows = {row["id"]: row for row in report["rows"]}
    require(len(rows) == 1659, "duplicate prior IDs")
    return report, rows, sha(compressed)


def execute(args):
    """Reproduce residuals, intervene only in memory, and report conservative dispositions."""
    # This import is confined to this historical measurement, never the product.
    from gutenbergpy import textget

    started = time.monotonic()
    measurement_sources = {
        str(pathlib.Path(path).resolve()): sha(pathlib.Path(path).read_bytes())
        for path in (
            __file__,
            audit_terminal_notice.__file__,
            audit_cleanup_causality.__file__,
        )
    }
    hashes = audit_cleanup_causality.product_tree_guard(ROOT, PRODUCT)
    normalization_data = normalization_data_guard()
    audit_cleanup_causality.product_import_guard(ROOT, hashes)
    require(
        pathlib.Path(parser.__file__).read_bytes()
        == audit_terminal_notice.git_source(
            BASE_PARSER, "lcats/src/lcats/gatherers/parser.py"
        ),
        "baseline parser changed",
    )
    prior, census, prior_hash = pinned_report(
        "gettenberg-narrow-delivery-20261022/corpus-comparison.json.gz"
    )
    numeric, metadata_rows, numeric_hash = pinned_report(
        "gettenberg-numeric-notice-audit-20261022/corpus-comparison.json.gz"
    )
    terminal, terminal_rows, terminal_hash = pinned_report(
        "gettenberg-terminal-notice-audit-20261022/corpus-comparison.json.gz"
    )
    require(hashes == prior["product_tree_sha256"], "prior census product bytes differ")
    require(set(census) == set(metadata_rows) == set(terminal_rows), "cohort changed")
    legacy_hash = sha(pathlib.Path(textget.__file__).read_bytes())
    require(legacy_hash == terminal["legacy_cleaner_sha256"], "legacy cleaner changed")
    selected = [
        row
        for row in census.values()
        if row["cleanup_refused"] or not row["legacy_equal"]
    ]
    require(
        len(selected) == 80 and sum(row["cleanup_refused"] for row in selected) == 13,
        "residual set changed",
    )
    rows, counts = [], collections.Counter()
    with mock.patch.object(
        socket, "socket", side_effect=AssertionError("network forbidden")
    ), lifecycle.CatalogManager(
        args.catalog_cache
    ).open() as catalog, contextlib.redirect_stdout(
        io.StringIO()
    ):
        require(
            catalog.info["report"]["archive_sha256"] == prior["catalog_archive_sha256"],
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
        for prior_row in selected:
            identifier = prior_row["id"]
            mrow, trow = metadata_rows[identifier], terminal_rows[identifier]
            compressed, raw = audit_terminal_notice.read_gzip(
                args.text_cache / f"{identifier}.txt.gz"
            )
            require(
                sha(compressed) == prior_row["cache_sha256"]
                and sha(raw) == prior_row["decoded_utf8_sha256"],
                f"source changed:{identifier}",
            )
            corpus = pathlib.Path(trow["corpus_path"])
            require(
                corpus.resolve().is_relative_to(ROOT / "corpora/mass_quantities")
                and sha(corpus.read_bytes()) == prior_row["corpus_sha256"],
                "historical corpus changed",
            )
            meta = source.metadata(identifier)
            require(
                meta is not None and meta.ebook.gutenberg_id == identifier,
                "missing metadata",
            )
            for field in ("titles", "authors", "aliases"):
                require(
                    list(getattr(meta, field)) == mrow[field],
                    f"metadata changed:{field}",
                )
            text = raw.decode("utf8")
            context = cleanup.CleanupContext(
                prior_row["source_id"], identifier, meta.titles
            )
            actual = cleanup.strip_boilerplate(text, context=context)
            codes = [item.code for item in actual.diagnostics]
            require(
                [actual.content_start, actual.content_end] == prior_row["slice"]
                and codes == prior_row["diagnostics"],
                "cleanup changed",
            )
            legacy_text, legacy_trace = legacy_clean(textget, raw)
            special = identifier in (70645, 42640, 32655, 23552)
            legacy_body, legacy_metrics = extract(
                legacy_text, meta, corpus.parent.name, special
            )
            row = {
                "id": identifier,
                "titles": list(meta.titles),
                "authors": list(meta.authors),
                "aliases": list(meta.aliases),
                "resource_uri": prior_row["resource_uri"],
                "source_id": prior_row["source_id"],
                "decoded_utf8_sha256": sha(raw),
                "cache_sha256": sha(compressed),
                "corpus_sha256": prior_row["corpus_sha256"],
                "corpus_path": str(corpus),
                "metadata_projection_sha256": sha(
                    json.dumps(
                        {
                            field: list(getattr(meta, field))
                            for field in ("titles", "authors", "aliases")
                        },
                        sort_keys=True,
                    )
                ),
                "cleanup_diagnostics": codes,
                "cleanup_span": [actual.content_start, actual.content_end],
                "cleanup_markers": [
                    {
                        **dataclasses.asdict(marker),
                        "source": source_excerpt(text, marker.start, marker.end),
                    }
                    for marker in actual.markers
                ],
                "legacy_cleanup_sha256": sha(legacy_text),
                "candidate_cleanup_sha256": sha(actual.text),
                "legacy_cleanup_trace": legacy_trace,
                "legacy_body": legacy_metrics,
                "causal_scope": "same decoded source, metadata, parser and normalization; cleaner substitution only",
                "editorial_approved": False,
                "delivery_accepted": False,
            }
            if prior_row["cleanup_refused"]:
                row.update(
                    disposition="explicit_operational_refusal",
                    mechanism=refusal_group(actual, text),
                    refusal_input_head=describe(text[:400]),
                    acceptance="requires measured batch impact and explicit acceptance; no bypass",
                )
                counts["refusals"] += 1
            else:
                require(
                    legacy_metrics["normalized_sha256"] == mrow["legacy_sha256"],
                    f"legacy replay differs:{identifier}",
                )
                current_body, current_metrics = extract(
                    actual.text, meta, corpus.parent.name, special
                )
                require(
                    all(
                        current_metrics[key] == value
                        for key, value in prior_row["body"].items()
                    ),
                    f"candidate replay differs:{identifier}",
                )
                require(current_body != legacy_body, "not a residual difference")
                group = body_group(legacy_body, current_body)
                row.update(
                    disposition="known_cleaner_substitution_effect",
                    mechanism=group,
                    body_delta=delta(legacy_body, current_body),
                    candidate_body=current_metrics,
                    acceptance="known cause is not approval; assess body contract and operational effect",
                )
                historical = json.loads(corpus.read_bytes())["body"]
                row["checked_in_corpus_body"] = {
                    "sha256": sha(historical),
                    "candidate_equal": current_body == historical,
                    "legacy_control_equal": legacy_body == historical,
                }
                if group == "mixed_front_and_tail_effect":
                    row["exact_line_hunks"] = mixed_hunks(legacy_body, current_body)
                if group == "terminal_notice_and_preceding_content":
                    row["preceding_content_probe"] = preceding_content_probe(
                        legacy_body, current_body, text, meta
                    )
                counts["differences"] += 1
                counts["whole_legacy_body_preserved"] += row["body_delta"][
                    "whole_before_preserved"
                ]
                counts["body_eligibility_changes"] += (
                    legacy_metrics["baseline_body_rejection"]
                    != current_metrics["baseline_body_rejection"]
                )
                footer = [
                    event for event in legacy_trace if event["kind"] == "footer_stop"
                ]
                # A single observed old footer can be moved into the current path
                # to isolate the interaction. This intervention deliberately does
                # not authorize broader notice matching in production.
                if len(footer) == 1:
                    cut = footer[0]["source_span"][0]
                    if actual.content_start < cut < actual.content_end:
                        cut_body, cut_metrics = extract(
                            text[actual.content_start : cut],
                            meta,
                            corpus.parent.name,
                            special,
                        )
                        row["counterfactual_legacy_footer_boundary"] = {
                            "source_cut": cut,
                            "removed_source": source_excerpt(
                                text, cut, actual.content_end
                            ),
                            "body": cut_metrics,
                            "equals_legacy_control": cut_body == legacy_body,
                            "candidate_to_probe_delta": delta(current_body, cut_body),
                            "publication_authorized": False,
                        }
                        counts["legacy_footer_boundary_probe"] += 1
                        counts["legacy_footer_probe_restores_control"] += (
                            cut_body == legacy_body
                        )
                if group == "terminal_notice_only":
                    row["contract_observation"] = (
                        "Exact entire legacy body retained; only whitespace plus a source-backed terminal Gutenberg notice added. No body eligibility change; notice is still boilerplate, not harmless by assertion."
                    )
                elif group == "boundary_whitespace_only":
                    row["contract_observation"] = (
                        "Bodies become byte-equal after strip; all non-boundary content unchanged. No body eligibility change."
                    )
                else:
                    row["contract_observation"] = (
                        "Nontrivial added or removed content needs explicit bounded disposition; do not infer narrative correctness from substring inclusion."
                    )
            counts[row["mechanism"]] += 1
            rows.append(row)
    require(
        audit_cleanup_causality.product_tree_guard(ROOT, PRODUCT) == hashes,
        "product changed during run",
    )
    require(
        normalization_data_guard() == normalization_data,
        "normalization input changed during run",
    )
    require(
        all(
            sha(pathlib.Path(path).read_bytes()) == digest
            for path, digest in measurement_sources.items()
        ),
        "measurement source changed during run",
    )
    require(
        sha(pathlib.Path(textget.__file__).read_bytes()) == legacy_hash,
        "historical cleaner changed during run",
    )
    imported = audit_cleanup_causality.product_import_guard(ROOT, hashes)
    return {
        "scope": __doc__,
        "completed": True,
        "release_accepted": False,
        "product_ref": PRODUCT,
        "head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, timeout=30
        ).strip(),
        "product_tree_sha256": hashes,
        "loaded_modules": imported,
        "normalization_data_sha256": normalization_data,
        "measurement_source_sha256": measurement_sources,
        "catalog_archive_sha256": prior["catalog_archive_sha256"],
        "evidence_ref": EVIDENCE,
        "prior_report_sha256": {
            "narrow": prior_hash,
            "numeric": numeric_hash,
            "terminal": terminal_hash,
        },
        "legacy_cleaner_sha256": legacy_hash,
        "legacy_cleaner_path": str(pathlib.Path(textget.__file__).resolve()),
        "parser_identical_to": BASE_PARSER,
        "runner_sha256": sha(pathlib.Path(__file__).read_bytes()),
        "helper_sha256": {
            module.__name__: sha(pathlib.Path(module.__file__).read_bytes())
            for module in (audit_terminal_notice, audit_cleanup_causality)
        },
        "cohort": {
            "prior_full_census": 1659,
            "equal_nonrefused_prior": 1579,
            "residuals_replayed_now": 80,
        },
        "summary": dict(counts),
        "rows": rows,
        "seconds": round(time.monotonic() - started, 3),
    }


def main(argv=None):
    """Validate paths/time bounds before touching any experimental output."""
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("catalog_cache", "text_cache", "output"):
        ap.add_argument(name, type=lambda value: pathlib.Path(value).resolve())
    args = ap.parse_args(argv)
    require(not args.output.exists(), "output already exists")
    require(
        args.catalog_cache.is_dir() and args.text_cache.is_dir(),
        "existing caches required",
    )
    for protected in (ROOT, args.catalog_cache, args.text_cache):
        require(not args.output.is_relative_to(protected), "protected output path")
    require(hasattr(signal, "SIGALRM"), "POSIX alarm required")
    previous = signal.signal(signal.SIGALRM, timeout)
    signal.alarm(900)
    try:
        report = execute(args)
        with args.output.open("x", encoding="utf8") as stream:
            json.dump(report, stream, indent=2)
            stream.write("\n")
        print(
            json.dumps(
                {
                    "completed": True,
                    "summary": report["summary"],
                    "seconds": report["seconds"],
                }
            )
        )
        return 0
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


if __name__ == "__main__":
    raise SystemExit(main())
