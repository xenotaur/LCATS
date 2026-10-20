"""Smoke-test a fresh installed wheel from outside its source checkout.

Run with the isolated venv's Python and PYTHONPATH unset:
python /absolute/path/qualify_installed.py NEW_OUTPUT_JSON
No downloads or shell calls. Creates a tiny authored catalog in a temporary
directory, exercises public operations, and checks metadata/import provenance.
The caller builds/installs the wheel, verifies its source hashes and runs pip
check separately. This smoke alone does not prove wheel/source equivalence.
"""

import argparse
import contextlib
import os
import types
import importlib.metadata
import importlib.util
import io
import json
import pathlib
import socket
import tarfile
import tempfile
from unittest import mock


def main(argv=None):
    """Exercise the installed distribution without inherited legacy dependencies."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("output", type=pathlib.Path)
    args = ap.parse_args(argv)
    if args.output.exists():
        ap.error("output exists")
    from lcats import cli
    from lcats.gatherers import parser
    from lcats.gatherers import readiness
    from lcats.gatherers.mass_quantities import gatherer
    from lcats.gettenberg import catalog
    from lcats.gettenberg import cleanup
    from lcats.gettenberg import lifecycle
    from lcats.utils import genre

    distribution = importlib.metadata.distribution("lcats")
    if importlib.util.find_spec("gutenbergpy") is not None:
        raise ValueError("legacy dependency present")
    if any(
        "gutenbergpy" in value.lower() or "git+" in value
        for value in distribution.requires or ()
    ):
        raise ValueError("legacy or VCS dependency in distribution")
    imported = pathlib.Path(catalog.__file__).resolve()
    if "site-packages" not in imported.parts:
        raise ValueError("import did not resolve installed package")
    raw = b"""<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:pg="http://www.gutenberg.org/2009/pgterms/" xmlns:dc="http://purl.org/dc/terms/" xml:base="https://www.gutenberg.org/">
<pg:ebook rdf:about="ebooks/84"><dc:title>Authored wheel fixture</dc:title><dc:language><rdf:Description><rdf:value>en</rdf:value></rdf:Description></dc:language></pg:ebook></rdf:RDF>"""
    with (
        tempfile.TemporaryDirectory() as temporary,
        mock.patch.object(
            socket, "socket", side_effect=AssertionError("network forbidden")
        ),
    ):
        root = pathlib.Path(temporary)
        archive = root / "fixture.tar.bz2"
        with tarfile.open(archive, "w:bz2") as stream:
            member = tarfile.TarInfo("84.rdf")
            member.size = len(raw)
            stream.addfile(member, io.BytesIO(raw))
        manager = lifecycle.CatalogManager(root / "cache")
        manager.setup(archive)
        with manager.open() as library:
            if library.find_ids(catalog.Filters(languages=("en",))) != (84,):
                raise ValueError("installed catalog query mismatch")
            if library.get(84).source.data != raw:
                raise ValueError("installed source roundtrip mismatch")
            genre.get_genre_by_id(84, catalog=library)
        if cleanup.strip_boilerplate("Authored story.").text != "Authored story.":
            raise ValueError("installed cleanup mismatch")
        # Exercise readiness, candidate storage and runtime log guards from the
        # installed wheel, with only the acquisition boundary authored in memory.
        # This catches accidental dependence on a checkout's pyproject.toml.
        narrative = "\n\n".join(
            f"The traveler waited at the gate on day {i}." for i in range(15)
        )

        class FixtureSource:
            def metadata(self, book_id):
                return types.SimpleNamespace(
                    titles=(f"Authored fixture {book_id}",),
                    authors=("Smith, John",),
                    aliases=(),
                    subjects=("PS", "Short stories"),
                    languages=("en",),
                )

            def read(self, metadata):
                text = (
                    narrative
                    if metadata.titles[0].endswith("84")
                    else "Transcriber's Note\n\n" + narrative
                )
                return types.SimpleNamespace(
                    cleaned=cleanup.strip_boilerplate(text),
                    provenance=lambda: {
                        "source_uri": "https://fixture.invalid/authored",
                        "input_kind": "authored_decoded_text",
                        "decoded_utf8_sha256": readiness.text_sha256(text),
                    },
                )

        with (
            mock.patch.dict(
                os.environ,
                LCATS_DATA_DIR=str(root / "data"),
                LCATS_CORPORA_DIR=str(root / "corpora"),
            ),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            source = FixtureSource()
            outcomes = gatherer.gather_stories(
                [84, 85], log_dir=root / "logs", source=source
            )
            if outcomes.counts != {"published": 1, "needs_review": 1}:
                raise ValueError(
                    f"installed readiness outcomes differ: {outcomes.counts}"
                )
            candidate = pathlib.Path(outcomes.outcomes[1].review_path)
            report = json.loads(candidate.read_text())["report"]

            def review_command(arguments):
                """Exercise the installed CLI entry point, including its exit code."""
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    try:
                        cli.main(["gather-review", *arguments])
                    except SystemExit as exc:
                        if exc.code != 0:
                            raise ValueError(
                                f"installed review CLI failed: {output.getvalue()}"
                            ) from exc
                return json.loads(output.getvalue())

            start = report["body"].index(narrative)
            packet = review_command(
                [
                    "show",
                    str(candidate),
                    "--start",
                    str(start),
                    "--end",
                    str(len(report["body"])),
                ]
            )
            if (
                packet["window"]["text"] != narrative
                or packet["omitted_before"] != start
            ):
                raise ValueError("installed review preview changed exact text")
            disposition = review_command(
                [
                    "record",
                    str(candidate),
                    "--outcome",
                    "approve",
                    "--start",
                    str(start),
                    "--end",
                    str(len(report["body"])),
                    "--reviewer",
                    "authored wheel fixture",
                    "--rationale",
                    "Select the known full authored narrative.",
                    "--directory",
                    str(root / "dispositions"),
                ]
            )["disposition"]
            for outcome in ("exclude", "defer"):
                review_command(
                    [
                        "record",
                        str(candidate),
                        "--outcome",
                        outcome,
                        "--reviewer",
                        "authored wheel fixture",
                        "--rationale",
                        "Demonstrate a conflicting audit record without publication.",
                        "--directory",
                        str(root / "dispositions"),
                    ]
                )
            inventory = review_command(
                [
                    "list",
                    str(candidate.parent),
                    "--dispositions",
                    str(root / "dispositions"),
                ]
            )
            if inventory["counts"] != {"conflict": 1}:
                raise ValueError("installed inventory hid conflicting intents")
            export = review_command(
                [
                    "export",
                    disposition,
                    "--candidates",
                    str(candidate.parent),
                    "--output",
                    str(root / "selected-approvals.json"),
                ]
            )
            decision = readiness.load_decisions(export["review_decisions"])[85]
            if len(list((root / "data").rglob("story.json"))) != 1:
                raise ValueError("review commands changed story outputs")
            selected = parser.inspect_story(85, source=source, review_decision=decision)
            if selected["status"] != "ready":
                raise ValueError("installed explicit review selection failed")
            reviewed = gatherer.gather_stories(
                [85],
                log_dir=root / "logs",
                source=source,
                review_decisions={85: decision},
            )
            published = json.loads(pathlib.Path(reviewed.gathered[85]).read_text())
            if published["body"] != narrative:
                raise ValueError("installed reviewed publication changed narrative")
        package = imported.parents[1]
        for relative in ("gatherers/overrides", "analysis/corpus/allowlists"):
            if not tuple((package / relative).glob("*.json")):
                raise ValueError(f"missing packaged data: {relative}")
    result = {
        "qualified": True,
        "version": distribution.version,
        "import_path": str(imported),
        "gutenbergpy_installed": False,
        "network_bytes": 0,
        "checks": [
            "metadata",
            "catalog setup/query/raw-source",
            "genre",
            "cleanup",
            "packaged JSON",
            "readiness withholding, immutable candidate and runtime logs",
            "explicit reviewed selection/publication",
            "installed gather-review list/show/approve/exclude/defer/export and conflict visibility",
        ],
    }
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    main()
