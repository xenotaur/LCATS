"""Reproduce an eight-case cleanup/extractor contrast without changing product code.

From lcats/, project environment and PYTHONPATH=src:
python ../experiments/10_gettenberg_qualification/scripts/audit_cleanup_causality.py CATALOG_CACHE TEXT_CACHE /tmp/NEW_REPORT.json

Requires the historical gutenbergpy measurement environment, never a production
requirement. Uses one pinned historical parser and current local product modules;
this is not a full historical environment reconstruction. Both cleaners and both
parsers receive identical decoded text and current metadata. Source anchor intervals
were reviewed in an earlier run; exact interval retention is not literary approval,
and false can mean typography changes rather than missing narrative.

Reads eight cached gzip texts (32 MiB compressed/expanded each), archived evidence,
Git history and an existing catalog. Blocks socket creation during catalog/source
processing; no acquisition, cache setup or story publication. POSIX alarm: 180s;
Git subprocess timeout: 30s. Output must be a new path outside repository/cache roots.
Failures raise and produce no completed output. Temporary historical module is removed.
See results/gettenberg-scope-audit-20261022/README.md for pins and interpretation.
"""

import argparse
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
import tempfile
from unittest import mock
from gutenbergpy import textget
from lcats.gatherers import (
    gutenberg_source,
    normalization,
    parser,
    readiness,
    story_body,
)
from lcats.gettenberg import cleanup, lifecycle, resources

ROOT = pathlib.Path(__file__).resolve().parents[3]
BASE = "335855c04cd7ba936815d2635969d94fdd278c71"
argument_parser = argparse.ArgumentParser(description=__doc__)
argument_parser.add_argument("catalog_cache", type=pathlib.Path)
argument_parser.add_argument("text_cache", type=pathlib.Path)
argument_parser.add_argument("output", type=pathlib.Path)
args = argument_parser.parse_args()
CACHE = args.text_cache.resolve()
CATALOG = args.catalog_cache.resolve()
OUTPUT = args.output.resolve()
if OUTPUT.exists():
    raise ValueError("output already exists; evidence is never overwritten")
for protected in (CACHE, CATALOG, ROOT):
    if OUTPUT.is_relative_to(protected):
        raise ValueError("output must be outside source, catalog and repository roots")
if not hasattr(signal, "SIGALRM"):
    raise RuntimeError("POSIX SIGALRM required")
if not CACHE.is_dir() or not CATALOG.is_dir():
    raise ValueError("existing text and catalog caches required; no setup/acquisition")
RESULTS = ROOT / "experiments/10_gettenberg_qualification/results"
CASES = RESULTS / "gettenberg-narrative-20261018/narrative-cases.json"
OLD = RESULTS / "gettenberg-qualification-20261018/corpus-after.json.gz"


def sha(data):
    """Identify exact bytes; UTF-8 encoding is not original transport provenance."""
    return hashlib.sha256(data.encode() if isinstance(data, str) else data).hexdigest()


def norm(text):
    """Use the same physical-newline boundary for both parser paths."""
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def bounded_timeout(*args):
    """Bound this finite diagnostic, including source and catalog reads."""
    raise TimeoutError("180-second diagnostic ceiling")


def require(condition, message):
    """Keep evidence guards active even under Python optimization."""
    if not condition:
        raise ValueError(message)


def bounded_gzip(data):
    """Limit legacy gzip expansion to 32 MiB; never acquire missing inputs."""
    if len(data) > 32 * 1024**2:
        raise ValueError("compressed input exceeds 32 MiB")
    with gzip.GzipFile(fileobj=io.BytesIO(data)) as stream:
        result = stream.read(32 * 1024**2 + 1)
    require(len(result) <= 32 * 1024**2, "expanded input exceeds 32 MiB")
    return result


signal.signal(signal.SIGALRM, bounded_timeout)
signal.alarm(180)
cases = json.loads(CASES.read_bytes())
if isinstance(cases, dict):
    cases = cases["cases"]
require(len(cases) == 8, "this diagnostic is limited to the eight archived cases")
old = json.loads(bounded_gzip(OLD.read_bytes()))
archived = {r["id"]: r for r in old["rows"]}
baseline_bytes = subprocess.check_output(
    ["git", "show", f"{BASE}:lcats/src/lcats/gatherers/parser.py"], cwd=ROOT, timeout=30
)
report = {
    "scope": __doc__,
    "head": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, timeout=30
    ).strip(),
    "baseline_parser_ref": BASE,
    "baseline_parser_sha256": sha(baseline_bytes),
    "current_parser_sha256": sha(pathlib.Path(parser.__file__).read_bytes()),
    "current_cleanup_sha256": sha(pathlib.Path(cleanup.__file__).read_bytes()),
    "legacy_cleaner_sha256": sha(pathlib.Path(textget.__file__).read_bytes()),
    "case_file_sha256": sha(CASES.read_bytes()),
    "archived_comparison_sha256": sha(OLD.read_bytes()),
    "network_forbidden": True,
    "rows": [],
}
require(
    report["legacy_cleaner_sha256"] == old["legacy_cleaner_sha256"],
    "legacy cleaner differs from archived measurement",
)
require(
    report["baseline_parser_sha256"]
    == old["source_sha256"]["src/lcats/gatherers/parser.py"],
    "baseline parser differs from archived measurement",
)
# Bind the imported product modules that determine the contrast. Shared helper
# imports remain the current environment: this is a controlled function probe,
# not a reconstruction of every historical package dependency.
report["runtime_product_ref"] = "6a873b611e3958bb9ddad8e84f2ad190831a9da7"
report["runtime_product_sha256"] = {}
runtime_modules = {
    "gatherers/parser.py": parser,
    "gatherers/story_body.py": story_body,
    "gatherers/readiness.py": readiness,
    "gatherers/normalization.py": normalization,
    "gatherers/gutenberg_source.py": gutenberg_source,
    "gettenberg/cleanup.py": cleanup,
    "gettenberg/lifecycle.py": lifecycle,
    "gettenberg/resources.py": resources,
}
report["runtime_import_paths"] = {}
for relative, module in runtime_modules.items():
    path = ROOT / "lcats/src/lcats" / relative
    expected = subprocess.check_output(
        ["git", "show", f"{report['runtime_product_ref']}:lcats/src/lcats/{relative}"],
        cwd=ROOT,
        timeout=30,
    )
    imported_path = pathlib.Path(module.__file__).resolve()
    require(imported_path == path.resolve(), f"wrong imported module: {relative}")
    require(
        imported_path.read_bytes() == expected, f"changed runtime product: {relative}"
    )
    report["runtime_import_paths"][relative] = str(imported_path)
    report["runtime_product_sha256"][relative] = sha(expected)
report["runner_sha256"] = sha(pathlib.Path(__file__).read_bytes())

# Loading only this pinned historical module avoids checking out or editing code.
with tempfile.TemporaryDirectory(prefix="gettenberg-causal-module-") as temp:
    path = pathlib.Path(temp) / "baseline_parser.py"
    path.write_bytes(baseline_bytes)
    spec = importlib.util.spec_from_file_location("causal_baseline_parser", path)
    baseline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(baseline)
    with lifecycle.CatalogManager(CATALOG).open() as catalog, mock.patch.object(
        socket, "socket", side_effect=AssertionError("network forbidden")
    ), contextlib.redirect_stdout(io.StringIO()):
        source = gutenberg_source.GutenbergStorySource(
            catalog,
            resources.ResourceStore(CATALOG),
            routes=resources.GutenbergRoutes(
                "https://www.gutenberg.org/files/",
                "https://www.gutenberg.org/cache/epub/",
            ),
        )
        report["catalog_archive_sha256"] = catalog.info["report"]["archive_sha256"]
        require(
            report["catalog_archive_sha256"] == old["catalog_archive_sha256"],
            "catalog archive identity mismatch",
        )
        for case in cases:
            identifier = case["id"]
            compressed = (CACHE / f"{identifier}.txt.gz").read_bytes()
            raw = bounded_gzip(compressed)
            text = raw.decode("utf8")
            meta = source.metadata(identifier)
            require(
                sha(raw)
                == case["decoded_utf8_sha256"]
                == archived[identifier]["decoded_utf8_sha256"],
                "source identity mismatch",
            )
            clean = {
                "legacy": norm(
                    textget.strip_headers(text.encode("utf8")).decode("utf8")
                ),
                "replacement": norm(cleanup.strip_boilerplate(text).text),
            }
            # Anchors were coordinator source-reviewed in the earlier narrative run;
            # compare exact intervening text, not just opening/closing presence.
            normalized = text.replace("\r\n", "\n").replace("\r", "\n")
            opening, closing = case["opening_anchor"], case["closing_anchor"]
            require(
                normalized.count(opening) == normalized.count(closing) == 1,
                "anchors must be unique",
            )
            narrative = normalized[
                normalized.index(opening) : normalized.index(closing) + len(closing)
            ]
            row = {
                "id": identifier,
                "decoded_utf8_sha256": sha(raw),
                "cache_sha256": sha(compressed),
                "titles": list(meta.titles),
                "authors": list(meta.authors),
                "aliases": list(meta.aliases),
                "narrative_sha256": sha(narrative),
                "contrasts": {},
            }
            for c_name, c_text in clean.items():
                for p_name, module in [("baseline", baseline), ("current", parser)]:
                    body = module.body_of_text(
                        c_text,
                        list(meta.authors),
                        list(meta.aliases),
                        list(meta.titles),
                    )
                    data = {
                        "name": meta.titles[0],
                        "author": list(meta.authors),
                        "body": body,
                        "metadata": {},
                    }
                    normalization.normalize_story_dict(
                        data,
                        collection="mass_quantities",
                        story_id=pathlib.Path(archived[identifier]["path"]).parent.name,
                    )
                    item = {
                        "extracted_sha256": sha(body),
                        "normalized_sha256": sha(data["body"]),
                        "normalized_characters": len(data["body"]),
                        "exact_anchor_interval_preserved": narrative in body,
                        "baseline_chaptered": baseline.chaptered(body),
                    }
                    if p_name == "current":
                        chapter = parser.assess_chapters(
                            body,
                            titles=meta.titles,
                            authors=meta.authors,
                            aliases=meta.aliases,
                        )
                        assessment = readiness.assess(
                            body,
                            chapter,
                            titles=meta.titles,
                            authors=meta.authors,
                            aliases=meta.aliases,
                        )
                        item["current_chapter_assessment"] = chapter
                        item["current_readiness"] = assessment.to_dict()
                    row["contrasts"][f"{c_name}_cleanup__{p_name}_parser"] = item
            row["archived_old_output_reproduced"] = (
                row["contrasts"]["legacy_cleanup__baseline_parser"]["normalized_sha256"]
                == archived[identifier]["normalized_before_sha256"]
            )
            row["archived_new_output_reproduced"] = (
                row["contrasts"]["replacement_cleanup__baseline_parser"][
                    "normalized_sha256"
                ]
                == archived[identifier]["normalized_after_sha256"]
            )
            require(
                row["archived_old_output_reproduced"]
                and row["archived_new_output_reproduced"],
                "archived contrast not reproduced",
            )
            report["rows"].append(row)
signal.alarm(0)
report["completed"] = True
output = OUTPUT
with output.open("x", encoding="utf-8") as stream:
    stream.write(json.dumps(report, indent=2) + "\n")
print(
    json.dumps({"output": str(output), "rows": len(report["rows"]), "completed": True})
)
