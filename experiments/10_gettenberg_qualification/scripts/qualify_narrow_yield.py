"""Measure actual narrow gather publication on the frozen decoded-source cohort.

From lcats/, project Python and absolute PYTHONPATH="$PWD/src":
python ../experiments/10_gettenberg_qualification/scripts/qualify_narrow_yield.py CATALOG_CACHE TEXT_CACHE NEW_OUTPUT_JSON

Read-only pinned catalog, historical gzip sources and prior census. All publication,
resource receipts and logs live in a temporary directory and are removed on exit.
No sockets, Gutenberg downloads, canonical data/cache writes or product changes.
The real HTTP opener receives explicit fixture.invalid UTF-8 responses made from
historically decoded text. Only while seeding these disposable receipts, transport
clock sleeps advance a virtual clock. This does NOT measure acquisition latency,
pacing, original wire fidelity, or the entire configured 5,492-story collection.

Real production gathering then runs offline: a cold batch in configured order
restricted to the 1,659 pinned IDs, a repeat of that batch, separate one-item calls
in a fresh shared output collection, and reuse with an EMPTY source cache. The
one-item census is an experiment controller, not a production continue-on-error
policy. No errors are silently converted into successful publication. Per-input
paths/body/provenance hashes and raw run events identify collisions and refusals.

Requires POSIX alarm (1,200s), gzip inputs <=32MiB, committed product bytes and fresh
output outside repository/input roots. Failed guards abort without a completed
report. Output JSON is exclusive; no historical evidence is overwritten.
"""

import argparse
import collections
import contextlib
import io
import json
import os
import pathlib
import signal
import socket
import tempfile
import time
from unittest import mock

from lcats import constants
from lcats.gatherers import gutenberg_source, parser
from lcats.gatherers.mass_quantities import gatherer, storymap
from lcats.gettenberg import _resource_transport, lifecycle, resources
from lcats.utils import names
import audit_cleanup_causality
import audit_terminal_notice
import qualify_narrow_installed

ROOT = pathlib.Path(__file__).resolve().parents[3]
PIN = "95ad5afddc6841c6f7946c7ae43fd98b6f39b25f"
CENSUS = "experiments/10_gettenberg_qualification/results/gettenberg-narrow-delivery-20261022/corpus-comparison.json.gz"
ORIGIN = "https://decoded-source-fixture.invalid"
require = audit_terminal_notice.require
sha = audit_terminal_notice.sha


class FixtureClock:
    """Advance fixture pacing without sleeping; never used during offline gather."""

    def __init__(self):
        self.offset = 0.0

    def time(self):
        return time.time() + self.offset

    def monotonic(self):
        return time.monotonic() + self.offset

    def sleep(self, delay):
        require(delay >= 0, "negative fixture delay")
        self.offset += delay


class TrackedInputs:
    """Observe the public iterable boundary without wrapping the production parser."""

    def __init__(self, identifiers, before_item):
        self.identifiers = list(identifiers)
        self.attempted = []
        self.before_item = before_item
        self.before = {}

    def __len__(self):
        return len(self.identifiers)

    def __iter__(self):
        for identifier in self.identifiers:
            self.before[identifier] = self.before_item(identifier)
            self.attempted.append(identifier)
            yield identifier


def output_path(data_root, metadata):
    """Predict the documented bucket for observation; product alone writes it."""
    filename = names.title_and_author_to_filename(
        metadata.titles[0],
        list(metadata.authors),
        ext=constants.FILE_SUFFIX,
        max_len=50,
    )
    return (
        data_root
        / storymap.TARGET_DIRECTORY
        / pathlib.Path(filename).stem
        / "story.json"
    )


def snapshot(data_root, metadata):
    """Read one output, retaining owner identity to detect bucket collisions."""
    path = output_path(data_root, metadata)
    if not path.exists():
        return None
    require(path.is_file() and not path.is_symlink(), "unsafe disposable output")
    raw = path.read_bytes()
    document = json.loads(raw)
    provenance = document["metadata"]["gettenberg"]
    return {
        "path": str(path.relative_to(data_root)),
        "json_sha256": sha(raw),
        "body_sha256": sha(document["body"]),
        "body_characters": len(document["body"]),
        "owner_id": provenance["gutenberg_id"],
        "fixture_source_sha256": provenance["original_sha256"],
        "receipt_sha256": provenance["receipt_sha256"],
    }


def observe_gather(identifiers, source, metas, data_root, log_dir, priors):
    """Call the real batch API; distinguish attempts, exceptions, files and reuse."""
    tracked = TrackedInputs(identifiers, lambda book: snapshot(data_root, metas[book]))
    failure = None
    returned = None
    with mock.patch.dict(os.environ, {"LCATS_DATA_DIR": str(data_root)}):
        try:
            result = gatherer.gather_batch(tracked, log_dir=log_dir, source=source)
            returned = {
                "ready_ids": list(result.ready),
                "skips": {str(k): v for k, v in result.skipped.items()},
                "refusals": {str(k): v for k, v in result.refused.items()},
            }
        except (resources.ResourceError, resources.ResourceDecodeError, OSError) as exc:
            failure = {
                "type": type(exc).__name__,
                "code": getattr(exc, "code", None),
                "message": str(exc),
            }
    events = [
        json.loads(line)
        for line in (log_dir / gatherer.GATHER_LOG_FILENAME).read_text().splitlines()
    ]
    event_for = {e["story"]: e["event"] for e in events if "story" in e}
    rows = []
    counts = collections.Counter()
    for identifier in tracked.attempted:
        after = snapshot(data_root, metas[identifier])
        prior = tracked.before[identifier]
        event = event_for.get(identifier)
        if event == "story_ready":
            require(after is not None, "ready event has no output")
            outcome = "reused" if prior is not None else "published"
            if prior is not None:
                require(prior == after, "existing output changed")
        elif event == "story_failed":
            outcome = "skipped"
        elif event == "story_cleanup_refused":
            outcome = "refused"
        else:
            require(
                failure is not None and identifier == tracked.attempted[-1],
                "missing outcome event",
            )
            outcome = "error"
        counts[outcome] += 1
        row = {"id": identifier, "outcome": outcome, "event": event, "output": after}
        if after is not None:
            row["owner_matches"] = after["owner_id"] == identifier
            row["matches_prior_body"] = after["body_sha256"] == priors[identifier].get(
                "body", {}
            ).get("normalized_sha256")
            counts["ownership_mismatches"] += not row["owner_matches"]
            counts["body_mismatches"] += not row["matches_prior_body"]
        if returned is not None and str(identifier) in returned["skips"]:
            row["skip_reason"] = returned["skips"][str(identifier)]
        if returned is not None and str(identifier) in returned["refusals"]:
            row["refusal_reason"] = returned["refusals"][str(identifier)]
        if failure is not None and identifier == tracked.attempted[-1]:
            row["exception"] = failure
        rows.append(row)
    unattempted = list(identifiers)[len(tracked.attempted) :]
    counts.update(
        {
            "requested": len(identifiers),
            "attempted": len(tracked.attempted),
            "unattempted": len(unattempted),
        }
    )
    require(len(rows) + len(unattempted) == len(identifiers), "incomplete accounting")
    return {
        "summary": dict(counts),
        "exception": failure,
        "returned": returned,
        "rows": rows,
        "unattempted_ids": unattempted,
        "events": events,
    }


def data_guard():
    """Pin both distributed JSON inputs, including lazy normalization overrides."""
    values = {}
    for relative in (
        "lcats/src/lcats/gatherers/overrides/mass_quantities.json",
        "lcats/src/lcats/analysis/corpus/allowlists/corpus_specials.json",
    ):
        raw = (ROOT / relative).read_bytes()
        require(
            raw == audit_terminal_notice.git_source(PIN, relative),
            "product JSON changed",
        )
        values[relative] = sha(raw)
    return values


def timeout(*_):
    """End the experiment before the bounded grant can be exhausted."""
    raise TimeoutError("1,200-second gather-yield ceiling")


def main(argv=None):
    """Pin evidence, seed explicitly synthetic receipts, and measure real gathering."""
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("catalog_cache", "text_cache", "output"):
        ap.add_argument(name, type=lambda value: pathlib.Path(value).resolve())
    ap.add_argument(
        "--product-ref", default=PIN, help="Committed product revision to verify"
    )
    args = ap.parse_args(argv)
    require(not args.output.exists(), "output exists")
    for protected in (ROOT, args.catalog_cache, args.text_cache.parent):
        require(not args.output.is_relative_to(protected), "protected output")
    require(
        args.catalog_cache.is_dir() and args.text_cache.is_dir(), "missing input cache"
    )
    old_handler = signal.signal(signal.SIGALRM, timeout)
    signal.alarm(1200)
    started = time.monotonic()
    runner_sha = sha(pathlib.Path(__file__).read_bytes())
    helpers = (audit_cleanup_causality, audit_terminal_notice, qualify_narrow_installed)
    helper_hashes = {
        m.__name__: sha(pathlib.Path(m.__file__).read_bytes()) for m in helpers
    }
    data_hashes = data_guard()
    try:
        product_hashes = audit_cleanup_causality.product_tree_guard(
            ROOT, args.product_ref
        )
        audit_cleanup_causality.product_import_guard(ROOT, product_hashes)
        compressed, raw = audit_terminal_notice.read_gzip(ROOT / CENSUS)
        require(
            compressed == audit_terminal_notice.git_source(PIN, CENSUS),
            "prior census changed",
        )
        census = json.loads(raw)
        require(
            census["completed"] and census["qualified_reproduction"],
            "incomplete prior census",
        )
        priors = {r["id"]: r for r in census["rows"]}
        require(len(priors) == len(census["rows"]) == 1659, "cohort changed")
        ordered = [book for book in storymap.SINGLE_STORIES if book in priors]
        require(
            len(ordered) == len(set(ordered)) == len(priors),
            "configured cohort membership changed",
        )
        real_routes = resources.GutenbergRoutes(
            "https://www.gutenberg.org/files/", "https://www.gutenberg.org/cache/epub/"
        )
        fixture_routes = resources.GutenbergRoutes(
            ORIGIN + "/files/", ORIGIN + "/cache/epub/"
        )
        source_pins, inventory, metas, requests = {}, [], {}, {}
        with tempfile.TemporaryDirectory(
            prefix="gettenberg-yield-"
        ) as temporary, mock.patch.object(
            socket, "socket", side_effect=AssertionError("network forbidden")
        ), lifecycle.CatalogManager(
            args.catalog_cache
        ).open() as catalog, contextlib.redirect_stdout(
            io.StringIO()
        ), contextlib.redirect_stderr(
            io.StringIO()
        ):
            root = pathlib.Path(temporary).resolve()
            require(
                catalog.info["report"]["archive_sha256"]
                == census["catalog_archive_sha256"],
                "catalog changed",
            )
            store = resources.ResourceStore(root / "fixture-cache")
            source = gutenberg_source.GutenbergStorySource(
                catalog, store, routes=fixture_routes
            )
            # These are the explicitly supplied existing roots, not a claim that
            # no resource receipts exist elsewhere on this computer.
            existing_stores = {
                str(path): resources.ResourceStore(path)
                for path in (args.catalog_cache, args.text_cache.parent)
            }
            for book in ordered:
                meta = source.metadata(book)
                require(meta is not None, "missing metadata")
                metas[book] = meta
                real = resources.select_routable_resource(
                    meta.ebook, routes=real_routes, preferences=gutenberg_source._PLAIN
                )
                fixture = resources.select_routable_resource(
                    meta.ebook,
                    routes=fixture_routes,
                    preferences=gutenberg_source._PLAIN,
                )
                require(
                    real.request is not None and fixture.request is not None,
                    "no resource route",
                )
                require(
                    real.request.source_uri
                    == priors[book]["resource_uri"]
                    == fixture.request.source_uri,
                    "source selection changed",
                )
                require(
                    fixture.request.request_url not in requests, "duplicate fixture URL"
                )
                requests[fixture.request.request_url] = (book, fixture.request)
                inventory.append(
                    {
                        "id": book,
                        "metadata_rejection": parser._metadata_rejection(meta, book),
                        "request_url": real.request.request_url,
                        "existing_plans": {
                            name: item.plan(real.request).action
                            for name, item in existing_stores.items()
                        },
                    }
                )
                compressed, decoded = audit_terminal_notice.read_gzip(
                    args.text_cache / f"{book}.txt.gz"
                )
                require(
                    sha(compressed) == priors[book]["cache_sha256"]
                    and sha(decoded) == priors[book]["decoded_utf8_sha256"],
                    "historical source changed",
                )
                source_pins[book] = {
                    "gzip_sha256": sha(compressed),
                    "decoded_utf8_sha256": sha(decoded),
                }
            calls = []

            class FixtureClient:
                """Only exact selected fixture URLs can access verified decoded bytes."""

                def open(self, request, timeout=None):
                    require(request.full_url in requests, "unexpected fixture request")
                    book, _ = requests[request.full_url]
                    zipped, decoded = audit_terminal_notice.read_gzip(
                        args.text_cache / f"{book}.txt.gz"
                    )
                    require(
                        sha(zipped) == source_pins[book]["gzip_sha256"]
                        and sha(decoded) == source_pins[book]["decoded_utf8_sha256"],
                        "fixture source changed",
                    )
                    calls.append(book)
                    return qualify_narrow_installed.MemoryResponse(decoded)

            clock = FixtureClock()
            policy = resources.NetworkPolicy(online=True, allowed_origins=(ORIGIN,))
            with mock.patch.object(
                _resource_transport, "opener", return_value=FixtureClient()
            ), mock.patch.object(_resource_transport, "time", clock):
                for book, request in requests.values():
                    artifact = store.fetch(request, policy=policy)
                    require(
                        artifact.sha256 == source_pins[book]["decoded_utf8_sha256"],
                        "fixture receipt differs",
                    )
                    source_pins[book][
                        "fixture_receipt_sha256"
                    ] = artifact.receipt_sha256
            require(calls == ordered, "fixture acquisition count/order differs")
            # Seeding is over: ordinary clock, offline policy and real resource
            # reads/decoding/cleanup/extraction/normalization/publication follow.
            with mock.patch.dict(
                os.environ,
                {
                    "LCATS_CORPORA_DIR": str(root / "corpora"),
                    "LCATS_CACHE_DIR": str(root / "unused-cache"),
                },
            ), contextlib.chdir(root):
                cold = observe_gather(
                    ordered,
                    source,
                    metas,
                    root / "batch-data",
                    root / "batch-log",
                    priors,
                )
                repeat = observe_gather(
                    ordered,
                    source,
                    metas,
                    root / "batch-data",
                    root / "repeat-log",
                    priors,
                )
                single = []
                for book in ordered:
                    single.append(
                        observe_gather(
                            [book],
                            source,
                            metas,
                            root / "one-item-data",
                            root / "one-item-logs" / str(book),
                            priors,
                        )
                    )
                ready_ids = [
                    r["rows"][0]["id"]
                    for r in single
                    if r["rows"][0]["outcome"] in ("published", "reused")
                ]
                # A cache miss would now fail. Successful repeat publication must
                # use the preexisting output, independent of source availability.
                source.store = resources.ResourceStore(root / "empty-source-cache")
                reuse = observe_gather(
                    ready_ids,
                    source,
                    metas,
                    root / "one-item-data",
                    root / "reuse-log",
                    priors,
                )
            totals = collections.Counter()
            for result in single:
                totals.update(result["summary"])
            paths = [
                r["rows"][0]["output"]["path"]
                for r in single
                if r["rows"][0]["output"] is not None
            ]
            totals["unique_output_files"] = len(set(paths))
            # Re-read immutable inputs before certifying that measurements did not
            # mutate them. Catalog is read-only; historical source hashes are exact.
            for book in ordered:
                zipped, decoded = audit_terminal_notice.read_gzip(
                    args.text_cache / f"{book}.txt.gz"
                )
                require(
                    sha(zipped) == source_pins[book]["gzip_sha256"]
                    and sha(decoded) == source_pins[book]["decoded_utf8_sha256"],
                    "source changed during gathering",
                )
            report = {
                "completed": True,
                "release_accepted": False,
                "scope": __doc__,
                "product_ref": args.product_ref,
                "product_tree_sha256": product_hashes,
                "census_sha256": sha((ROOT / CENSUS).read_bytes()),
                "catalog_archive_sha256": census["catalog_archive_sha256"],
                "runner_sha256": runner_sha,
                "helper_sha256": helper_hashes,
                "product_data_sha256": data_hashes,
                "configured_collection_count": len(storymap.SINGLE_STORIES),
                "frozen_cohort_count": len(ordered),
                "ordered_ids": ordered,
                "metadata_and_cache_inventory": inventory,
                "source_pins": source_pins,
                "fixture_requests": calls,
                "fixture_virtual_wait_seconds": clock.offset,
                "cold_batch": cold,
                "repeated_batch": repeat,
                "one_item_summary": dict(totals),
                "one_item_runs": single,
                "empty_source_cache_reuse": reuse,
                "limitations": [
                    "Decoded UTF-8 fixtures are not original transport receipts.",
                    "Only configured-order intersection with the frozen 1659 cohort was executed, not full configured selection.",
                    "One-item calls are experimental isolation, not a production continue-on-error mode.",
                    "Product publication is not editorial acceptance.",
                ],
            }
        require(
            audit_cleanup_causality.product_tree_guard(ROOT, args.product_ref)
            == product_hashes,
            "product changed",
        )
        report["loaded_modules"] = audit_cleanup_causality.product_import_guard(
            ROOT, product_hashes
        )
        require(
            sha(pathlib.Path(__file__).read_bytes()) == runner_sha,
            "runner changed during measurement",
        )
        require(data_guard() == data_hashes, "product JSON changed during measurement")
        require(
            all(
                sha(pathlib.Path(m.__file__).read_bytes()) == helper_hashes[m.__name__]
                for m in helpers
            ),
            "measurement helper changed during run",
        )
        report["seconds"] = round(time.monotonic() - started, 3)
        with args.output.open("x", encoding="utf8") as stream:
            json.dump(report, stream, indent=2)
            stream.write("\n")
        print(
            json.dumps(
                {
                    "cold_batch": cold["summary"],
                    "one_item": dict(totals),
                    "reuse": reuse["summary"],
                    "seconds": report["seconds"],
                }
            )
        )
        return 0
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


if __name__ == "__main__":
    raise SystemExit(main())
