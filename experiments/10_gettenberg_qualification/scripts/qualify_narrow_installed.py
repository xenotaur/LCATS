"""Qualify the narrow installed provider and gathering path on authored fixtures.

Run outside the source checkout using the fresh wheel venv, PYTHONPATH unset:
python /absolute/path/qualify_narrow_installed.py NEW_OUTPUT_JSON

No tests or optional gutenbergpy package are imported. A two-story catalog and one
refused source are authored in a disposable directory. Only the HTTP transport
boundary is replaced with in-memory responses; catalog, resource receipts, strict
decoding, cleanup/context, historical parser, output publication and batch logging
run for real. Socket creation is denied throughout. No external acquisition,
canonical corpus changes or persistent cache writes. POSIX alarm:120seconds.
The output must not exist; failures produce no successful report. The coordinator
must separately verify wheel/source equality and pip check. This finite smoke does
not qualify all historical corpus cases or broader editorial correctness.
"""

import argparse
import contextlib
import email.message
import hashlib
import importlib.metadata
import importlib.util
import io
import json
import os
import pathlib
import signal
import socket
import sys
import tarfile
import tempfile
from unittest import mock


BOOKS = (990011, 990012, 990013)
ORIGIN = "https://fixture.invalid"
TITLE = "Lantern Voyage"
FORBIDDEN = (
    "gutenbergpy",
    "lcats.gatherers.gather_result",
    "lcats.gatherers.review_cli",
    "lcats.gatherers.readiness",
    "lcats.gatherers.story_body",
    "lcats.gatherers.review_store",
    "lcats.gatherers.review_rules",
    "lcats.gatherers.candidate_review",
    "lcats.gatherers.historical_review",
    "lcats.gatherers.editorial_evidence",
)


def require(condition, message):
    """Keep qualification checks active under Python optimization."""
    if not condition:
        raise ValueError(message)


def sha(data):
    """Identify exact fixture bytes, independent of temporary filenames."""
    return hashlib.sha256(data).hexdigest()


class DenyUnrelatedImports:
    """Fail visibly if the narrow path tries retired or separated functionality."""

    def find_spec(self, fullname, path=None, target=None):
        if any(
            fullname == name or fullname.startswith(name + ".") for name in FORBIDDEN
        ):
            raise ImportError(f"forbidden narrow-delivery import: {fullname}")
        return None


@contextlib.contextmanager
def bounded_runtime():
    """Forbid legacy/review imports and all real sockets; restore caller state."""
    require(
        not any(
            name == blocked or name.startswith(blocked + ".")
            for name in sys.modules
            for blocked in FORBIDDEN
        ),
        "forbidden module was already imported",
    )
    blocker = DenyUnrelatedImports()
    sys.meta_path.insert(0, blocker)
    try:
        with mock.patch.object(
            socket, "socket", side_effect=AssertionError("network forbidden")
        ):
            yield
    finally:
        sys.meta_path.remove(blocker)


class MemoryResponse(io.BytesIO):
    """A bounded response at the sole replaced HTTP boundary."""

    def __init__(self, body):
        super().__init__(body)
        self.status = 200
        self.headers = email.message.Message()
        self.headers["Content-Length"] = str(len(body))
        self.headers["Content-Type"] = "text/plain; charset=utf-8"


def record(book_id):
    """Produce authored RDF with enough metadata for the real gather filters."""
    return f"""<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
xmlns:pg="http://www.gutenberg.org/2009/pgterms/" xmlns:dc="http://purl.org/dc/terms/"
xml:base="https://www.gutenberg.org/">
<pg:ebook rdf:about="ebooks/{book_id}"><dc:title>{TITLE} {book_id}</dc:title>
<dc:creator><pg:agent rdf:about="2009/agents/1"><pg:name>Smith, John</pg:name></pg:agent></dc:creator>
<dc:language><rdf:Description><rdf:value>en</rdf:value></rdf:Description></dc:language>
<dc:subject><rdf:Description><rdf:value>PS</rdf:value></rdf:Description></dc:subject>
<dc:subject><rdf:Description><rdf:value>Short stories</rdf:value></rdf:Description></dc:subject>
<dc:hasFormat><pg:file rdf:about="https://www.gutenberg.org/ebooks/{book_id}.txt.utf-8">
<dc:format><rdf:Description><rdf:value>text/plain; charset=utf-8</rdf:value></rdf:Description></dc:format>
</pg:file></dc:hasFormat></pg:ebook></rdf:RDF>""".encode()


def source_bytes(book_id, narrative):
    """One numeric envelope, one title envelope, and one mismatched refusal."""
    title = f"{TITLE} {book_id}"
    marker = str(book_id) if book_id != BOOKS[1] else title
    end_marker = "Unrelated book" if book_id == BOOKS[2] else marker
    return (
        f"*** START OF THE PROJECT GUTENBERG EBOOK {marker} ***\r\n\r\n"
        + title
        + "\r\n\r\nJohn Smith\r\n\r\n"
        + narrative.replace("\n", "\r\n")
        + f"\r\n\r\nEnd of the Project Gutenberg EBook of {title}, by John Smith\r\n\r\n"
        + f"*** END OF THE PROJECT GUTENBERG EBOOK {end_marker} ***\r\n"
    ).encode()


def exercise(root):
    """Run real product behavior on disposable authored inputs, without test imports.

    This function is also used for a checkout development smoke. Only main() adds
    installed-environment validation; exercise() alone never certifies a wheel.
    """
    from lcats.gatherers import gutenberg_source
    from lcats.gatherers.mass_quantities import gatherer
    from lcats.gettenberg import _resource_transport
    from lcats.gettenberg import catalog
    from lcats.gettenberg import cleanup
    from lcats.gettenberg import lifecycle
    from lcats.gettenberg import resources

    root = pathlib.Path(root).resolve()
    archive = root / "fixture.tar.bz2"
    originals = {}
    narrative = "\n\n".join(
        f"Paragraph {index}: the travelers waited beside the river and watched the boats."
        for index in range(15)
    )
    with tarfile.open(archive, "w:bz2") as stream:
        for book_id in BOOKS:
            raw = record(book_id)
            member = tarfile.TarInfo(f"{book_id}.rdf")
            member.size = len(raw)
            stream.addfile(member, io.BytesIO(raw))
            originals[book_id] = source_bytes(book_id, narrative)
    cache = root / "cache"
    manager = lifecycle.CatalogManager(cache)
    manager.setup(archive)
    store = resources.ResourceStore(cache)
    routes = resources.GutenbergRoutes(ORIGIN + "/main/", ORIGIN + "/generated/")
    policy = resources.NetworkPolicy(online=True, allowed_origins=(ORIGIN,))
    requests = []

    class MemoryClient:
        """Map exact authored URLs to fixture bytes, rejecting speculative routes."""

        def open(self, request, timeout=None):
            url = request.full_url
            expected = {
                f"{ORIGIN}/generated/{book}/pg{book}.txt": book for book in BOOKS
            }
            require(url in expected, "unexpected fixture acquisition route")
            requests.append(url)
            return MemoryResponse(originals[expected[url]])

    with manager.open() as library, mock.patch.dict(
        os.environ,
        {
            "LCATS_DATA_DIR": str(root / "data"),
            "LCATS_CORPORA_DIR": str(root / "corpora"),
            "LCATS_CACHE_DIR": str(cache),
        },
    ), contextlib.chdir(root), contextlib.redirect_stdout(
        io.StringIO()
    ), contextlib.redirect_stderr(
        io.StringIO()
    ):
        require(
            library.find_ids(catalog.Filters(languages=("en",))) == BOOKS,
            "fixture catalog IDs differ",
        )
        source = gutenberg_source.GutenbergStorySource(
            library, store, routes=routes, policy=policy
        )
        artifacts = {}
        # Seed the actual resource store through the transport API; no fake files
        # or receipts are inserted. Offline gathering then must reuse these bytes.
        with mock.patch.object(
            _resource_transport, "opener", return_value=MemoryClient()
        ):
            for book_id in BOOKS:
                metadata = source.metadata(book_id)
                selected = resources.select_routable_resource(
                    metadata.ebook, routes=routes
                )
                artifacts[book_id] = store.fetch(selected.request, policy=policy)
        require(len(requests) == len(BOOKS), "unexpected acquisition count")
        source.policy = resources.NetworkPolicy()
        prepared = source.read(source.metadata(BOOKS[0]))
        require(
            prepared.cleaned.context
            == cleanup.CleanupContext(BOOKS[0], BOOKS[0], (f"{TITLE} {BOOKS[0]}",)),
            "numeric cleanup context differs",
        )
        require(
            [d.code for d in prepared.cleaned.diagnostics]
            == ["envelope_removed", "numeric_notice_removed"],
            "numeric notice repair missing",
        )
        published, failures = gatherer.gather_stories(
            BOOKS[:2], log_dir=root / "logs", source=source
        )
        require(
            set(published) == set(BOOKS[:2]) and not failures,
            "actual gather tuple differs",
        )
        stories = []
        for book_id, filename in published.items():
            payload = pathlib.Path(filename).read_bytes()
            story = json.loads(payload)
            require(story["body"] == narrative, "published narrative differs")
            provenance = story["metadata"]["gettenberg"]
            require(
                provenance["original_sha256"] == sha(originals[book_id]),
                "source provenance differs",
            )
            require(
                provenance["cleanup_context"]
                == {
                    "source_id": book_id,
                    "catalog_id": book_id,
                    "titles": [f"{TITLE} {book_id}"],
                },
                "published cleanup context differs",
            )
            require(
                provenance["cleanup_policy"] == "gutenberg-boundaries-v3",
                "cleanup version differs",
            )
            require(
                artifacts[book_id].path.read_bytes() == originals[book_id],
                "original bytes changed",
            )
            stories.append({"id": book_id, "json": story, "json_sha256": sha(payload)})
        # Existing buckets must be reused without rewriting their JSON or source.
        before_reuse = {
            book: pathlib.Path(path).read_bytes() for book, path in published.items()
        }
        reused, reuse_failures = gatherer.gather_stories(
            BOOKS[:2], log_dir=root / "reuse-log", source=source
        )
        require(
            reused == published and not reuse_failures, "existing output reuse differs"
        )
        require(
            all(
                pathlib.Path(reused[book]).read_bytes() == raw
                for book, raw in before_reuse.items()
            ),
            "existing story was rewritten",
        )
        result = gatherer.gather_batch(
            [BOOKS[2]], log_dir=root / "refusal-log", source=source
        )
        require(set(result.refused) == {BOOKS[2]}, "ambiguous envelope not refused")
        require(not result.ready and not result.skipped, "refusal misclassified")
        refusal = {"code": "cleanup_refused", "message": result.refused[BOOKS[2]]}
        require(
            len(list((root / "data").rglob("story.json"))) == 2, "refusal wrote a story"
        )
        log_path = root / "refusal-log" / gatherer.GATHER_LOG_FILENAME
        events = [json.loads(line) for line in log_path.read_text().splitlines()]
        require(
            any(e["event"] == "story_cleanup_refused" for e in events),
            "missing distinct refusal log",
        )
        require(events[-1]["event"] == "run_end", "refusal aborted iteration")
        require(events[-2]["incomplete"], "refusal omitted from batch summary")
        protected_checks = []
        for protected in (
            root / "data" / "forbidden-log",
            root / "corpora" / "forbidden-log",
        ):
            try:
                gatherer.gather_stories([], log_dir=protected, source=source)
            except ValueError:
                require(not protected.exists(), "protected log path was created")
                protected_checks.append(str(protected.relative_to(root)))
            else:
                raise ValueError("protected log root accepted")
        require(len(requests) == len(BOOKS), "offline gather acquired data")
        require(
            artifacts[BOOKS[2]].path.read_bytes() == originals[BOOKS[2]],
            "refused source bytes changed",
        )
    return {
        "fixture_kind": "independently authored RDF and decoded UTF-8 transport responses",
        "network_bytes": 0,
        "fixture_transport_requests": requests,
        "catalog_archive_sha256": sha(archive.read_bytes()),
        "published_count": len(stories),
        "stories": stories,
        "refusal": refusal,
        "refusal_events": events,
        "protected_log_checks": protected_checks,
        "originals_preserved": True,
        "offline_reuse": True,
        "existing_outputs_unchanged": True,
    }


def installed_environment():
    """Reject editable/source imports and retired/VCS dependencies before exercising."""
    require(
        not os.environ.get("PYTHONPATH"), "unset PYTHONPATH for installed qualification"
    )
    require(sys.prefix != sys.base_prefix, "use a fresh isolated wheel venv")
    require(
        importlib.util.find_spec("gutenbergpy") is None, "legacy package is importable"
    )
    try:
        importlib.metadata.distribution("gutenbergpy")
    except importlib.metadata.PackageNotFoundError:
        pass
    else:
        raise ValueError("legacy distribution installed")
    distribution = importlib.metadata.distribution("lcats")
    require(
        not any(
            "gutenbergpy" in value.lower() or "git+" in value.lower()
            for value in distribution.requires or ()
        ),
        "legacy/VCS dependency in wheel",
    )
    direct = distribution.read_text("direct_url.json")
    require(
        not direct or not json.loads(direct).get("dir_info", {}).get("editable"),
        "editable package installed",
    )
    root = pathlib.Path(distribution.locate_file("lcats")).resolve()
    require(
        "site-packages" in root.parts and root.is_dir(),
        "installed package root missing",
    )
    for name in FORBIDDEN:
        if name.startswith("lcats."):
            relative = pathlib.Path(*name.split(".")[1:])
            require(
                not (root / relative).with_suffix(".py").exists()
                and not (root / relative / "__init__.py").exists(),
                f"separated module shipped in wheel: {name}",
            )
    return distribution, root


def module_origins(root):
    """Verify all loaded product modules resolve under this installed distribution."""
    imported = {}
    for name, module in tuple(sys.modules.items()):
        if name != "lcats" and not name.startswith("lcats."):
            continue
        origin = getattr(module, "__file__", None)
        require(origin is not None, f"missing product origin: {name}")
        path = pathlib.Path(origin).resolve()
        require(path.is_relative_to(root), f"non-installed module: {name}")
        imported[name] = {"path": str(path), "sha256": sha(path.read_bytes())}
    require(bool(imported), "no installed modules exercised")
    return imported


def timeout(*_):
    """Bound fixture acquisition, parser and filesystem operations together."""
    raise TimeoutError("120-second installed smoke ceiling")


def main(argv=None):
    """Run installed qualification only; import and help have no product side effects."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("output", type=pathlib.Path)
    args = ap.parse_args(argv)
    output = args.output.resolve()
    require(not output.exists(), "output exists; evidence is never overwritten")
    require(hasattr(signal, "SIGALRM"), "POSIX SIGALRM required")
    distribution, root = installed_environment()
    require(not output.is_relative_to(root), "output inside installed package")
    previous = signal.signal(signal.SIGALRM, timeout)
    signal.alarm(120)
    try:
        with bounded_runtime(), tempfile.TemporaryDirectory(
            prefix="gettenberg-narrow-wheel-"
        ) as temporary:
            result = exercise(pathlib.Path(temporary))
            origins = module_origins(root)
        report = {
            "scope": __doc__,
            "completed": True,
            "installed_qualification": True,
            "python_executable": sys.executable,
            "prefix": sys.prefix,
            "base_prefix": sys.base_prefix,
            "distribution_version": distribution.version,
            "requirements": list(distribution.requires or ()),
            "module_origins": origins,
            "runner_sha256": sha(pathlib.Path(__file__).read_bytes()),
            "result": result,
        }
        with output.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2)
            stream.write("\n")
        print(
            json.dumps(
                {
                    "output": str(output),
                    "published": result["published_count"],
                    "completed": True,
                }
            )
        )
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


if __name__ == "__main__":
    main()
