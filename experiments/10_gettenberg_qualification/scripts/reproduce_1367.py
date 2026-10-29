"""Reproduce ebook 1367 acquisition through the real CLI with isolated state.

From lcats/ in the project environment, with src on PYTHONPATH:
python ../experiments/10_gettenberg_qualification/scripts/reproduce_1367.py \
    --catalog /absolute/path/to/catalog.sqlite --output /tmp/NEW-evidence \
    --existing-story /absolute/path/to/findelkind__ouida/story.json

Reads one RDF record from an existing catalog opened read-only, then builds a
one-record catalog in a temporary directory. Only collection selection is
substituted. Output, resource cache, logs and the working directory are isolated;
existing story bytes are fingerprinted before/after, never used by gathering.
Uses the default mirror and real HTTP transport, with at most one request to the
selected URL (no retry, redirect or fallback probe). Does not download metadata.
POSIX alarm limits the whole run to 120 seconds. Live status may change: report
an observation, not an evergreen test assertion. --output must not exist; it
retains RDF, run logs and a JSON report, but no downloaded story body. Exit 0
means the experiment completed, not that gathering or the expected 404 succeeded.
"""

import argparse
import contextlib
import datetime
import hashlib
import io
import json
import os
import pathlib
import signal
import sys
import tarfile
import tempfile
from unittest import mock

from lcats import cli
from lcats.gatherers import gutenberg_source
from lcats.gatherers import parser
from lcats.gatherers import story_output
from lcats.gatherers.mass_quantities import gatherer, storymap
from lcats.gettenberg import _resource_transport
from lcats.gettenberg import catalog, lifecycle, resources, sources_cli


def digest(path):
    """Fingerprint a small evidence/output file without rewriting it."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_state(path):
    """Record metadata without hashing the entire large catalog database."""
    stat = path.stat()
    return {"path": str(path), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns}


def deadline(signum, frame):
    """Stop live work; a timeout must never be reported as a completed check."""
    raise TimeoutError("1367 reproduction exceeded 120 seconds")


def main(argv=None):
    """Run a fresh one-item CLI acquisition and record its actual outcome."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--catalog", required=True, type=pathlib.Path)
    ap.add_argument("--existing-story", required=True, type=pathlib.Path)
    ap.add_argument("--output", required=True, type=pathlib.Path)
    args = ap.parse_args(argv)
    args.catalog = args.catalog.resolve(strict=True)
    args.existing_story = args.existing_story.resolve(strict=True)
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    before = {
        "catalog": file_state(args.catalog),
        "story_sha256": digest(args.existing_story),
    }
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    previous_alarm = signal.signal(signal.SIGALRM, deadline)
    signal.alarm(120)
    try:
        with catalog.Catalog(args.catalog) as original:
            record = original.get(1367)
            if record is None:
                raise ValueError("catalog has no ebook 1367")
            original_info = original.info
        (args.output / "1367.rdf").write_bytes(record.source.data)
        with tempfile.TemporaryDirectory(prefix="gettenberg-1367-live-") as temporary:
            root = pathlib.Path(temporary).resolve()
            cache, data = root / "cache", root / "data"
            archive = root / "one-record.tar.bz2"
            with tarfile.open(archive, "w:bz2") as bundle:
                member = tarfile.TarInfo("1367/pg1367.rdf")
                member.size = len(record.source.data)
                bundle.addfile(member, io.BytesIO(record.source.data))
            manager = lifecycle.CatalogManager(cache)
            manager.setup(archive)
            routes = sources_cli.gutenberg_routes()
            with manager.open() as isolated:
                source = gutenberg_source.GutenbergStorySource(
                    isolated, resources.ResourceStore(cache), routes=routes
                )
                selected = resources.select_routable_resource(
                    source.metadata(1367).ebook,
                    routes=routes,
                    preferences=gutenberg_source._PLAIN,
                )
            request = selected.request
            if request is None:
                raise ValueError("1367 has no selected plain-text resource")
            store = resources.ResourceStore(cache)
            if store.plan(request).artifact is not None or data.exists():
                raise ValueError("reproduction must start without source or output")
            requests = []
            real_opener = _resource_transport.opener

            class ObservedClient:
                """Delegate to real HTTP, retaining only URL/status observations."""

                def __init__(self, client):
                    self.client = client

                def open(self, outgoing, timeout=None):
                    if requests or outgoing.full_url != request.request_url:
                        raise RuntimeError(
                            "refusing additional or alternate live request"
                        )
                    observed = {
                        "url": outgoing.full_url,
                        "method": outgoing.get_method(),
                    }
                    requests.append(observed)
                    response = self.client.open(outgoing, timeout=timeout)
                    observed["status"] = response.status
                    return response

            def observed_opener(*args, **kwargs):
                return ObservedClient(real_opener(*args, **kwargs))

            stdout, stderr = io.StringIO(), io.StringIO()
            with (
                contextlib.chdir(root),
                mock.patch.dict(
                    os.environ,
                    LCATS_DATA_DIR=str(data),
                    LCATS_CORPORA_DIR=str(root / "corpora"),
                    LCATS_CACHE_DIR=str(cache),
                ),
                mock.patch.object(storymap, "SINGLE_STORIES", [1367]),
                mock.patch.object(_resource_transport, "opener", observed_opener),
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                try:
                    cli.main(["gather", "mass_quantities", "--cache-dir", str(cache)])
                except SystemExit as exc:
                    status = exc.code
                else:
                    raise RuntimeError("CLI did not exit")
            log = root / "logs/gather" / gatherer.GATHER_LOG_FILENAME
            events = [json.loads(line) for line in log.read_text().splitlines()]
            (args.output / "gather.jsonl").write_bytes(log.read_bytes())
            outputs = {
                str(p.relative_to(data)): digest(p) for p in data.rglob("story.json")
            }
            artifact = store.plan(request).artifact
            observation = {
                "requests": requests,
                "cli_status": status,
                "stdout": stdout.getvalue(),
                "stderr": stderr.getvalue(),
                "output_hashes": outputs,
                "cached_source": artifact is not None,
                "temporary_acquisition_files": [
                    p.name for p in (cache / "gettenberg/resources/tmp").glob("*")
                ],
                "events": events,
                "isolated_root": str(root),
            }
        after = {
            "catalog": file_state(args.catalog),
            "story_sha256": digest(args.existing_story),
        }
        if before != after:
            raise RuntimeError(
                "original catalog metadata or existing story bytes changed"
            )
        report = {
            "completed": True,
            "started_at": started,
            "finished_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "python": sys.version,
            "runner_sha256": digest(pathlib.Path(__file__)),
            "original_catalog_info": original_info,
            "rdf_source_name": record.source.source_name,
            "rdf_sha256": record.source.sha256,
            "source_uri": request.source_uri,
            "request_url": request.request_url,
            "existing_story": str(args.existing_story),
            "protected_before": before,
            "protected_after": after,
            "module_sha256": {
                str(pathlib.Path(module.__file__).resolve()): digest(
                    pathlib.Path(module.__file__)
                )
                for module in (
                    cli,
                    parser,
                    gatherer,
                    story_output,
                    gutenberg_source,
                    _resource_transport,
                )
            },
            **observation,
        }
        (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(f"CLI status {status}; requests {requests}; evidence {args.output}")
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous_alarm)


if __name__ == "__main__":
    main()
