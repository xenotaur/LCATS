"""Verify installed RDF/SQLite title and alias behavior without network access.

From outside the checkout, with PYTHONPATH unset, run with the fresh wheel venv:
python /path/qualify_release_catalog.py /path/tests/gettenberg_tests/fixtures NEW_JSON

Uses the seven retained real RDF fixtures plus one explicitly authored multi-title
record. Imports the installed provider, creates/discards a local catalog, verifies
raw RDF identity, title/alias queries and reopen behavior. Reuses the sibling narrow
runner's installed-origin/import/socket guards. No story downloads or shared cache
writes; POSIX 120-second alarm. NEW_JSON must be fresh. This finite check is not a
full-source census or a claim about live Gutenberg formats or other Python versions.
"""

import argparse
import io
import json
import pathlib
import signal
import tarfile
import tempfile

import qualify_narrow_installed


AUTHORED_ID = 990099
AUTHORED = b"""<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
xmlns:pg="http://www.gutenberg.org/2009/pgterms/" xmlns:dc="http://purl.org/dc/terms/"
xml:base="https://www.gutenberg.org/">
<pg:ebook rdf:about="ebooks/990099"><dc:title>First title</dc:title>
<dc:title>Second title</dc:title><dc:alternative>Alternate title</dc:alternative>
<dc:creator><pg:agent rdf:about="2009/agents/990099"><pg:name>Writer, Alice</pg:name>
<pg:alias>Alice Example</pg:alias><pg:alias>Another Name</pg:alias>
</pg:agent></dc:creator></pg:ebook></rdf:RDF>"""


def main(argv=None):
    """Exercise an independent authored expectation and real-source round trips."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixtures", type=pathlib.Path)
    parser.add_argument("output", type=pathlib.Path)
    args = parser.parse_args(argv)
    require = qualify_narrow_installed.require
    sha = qualify_narrow_installed.sha
    require(not args.output.exists(), "output exists")
    distribution, package_root = qualify_narrow_installed.installed_environment()
    require(not args.output.resolve().is_relative_to(package_root), "output in package")
    previous = signal.signal(signal.SIGALRM, qualify_narrow_installed.timeout)
    signal.alarm(120)
    try:
        with qualify_narrow_installed.bounded_runtime():
            from lcats.gettenberg import catalog
            from lcats.gettenberg import lifecycle
            from lcats.gettenberg import rdf

            originals = {
                p.name: p.read_bytes() for p in sorted(args.fixtures.glob("pg*.rdf"))
            }
            require(len(originals) == 7, "expected seven retained real records")
            originals["authored.rdf"] = AUTHORED
            with tempfile.TemporaryDirectory(
                prefix="lcats-release-catalog-"
            ) as temporary:
                root = pathlib.Path(temporary)
                archive = root / "input.tar.bz2"
                with tarfile.open(
                    archive, "w:bz2", format=tarfile.USTAR_FORMAT
                ) as stream:
                    for name, raw in originals.items():
                        member = tarfile.TarInfo(name)
                        member.size = len(raw)
                        stream.addfile(member, io.BytesIO(raw))
                manager = lifecycle.CatalogManager(root / "cache")
                manager.setup(archive)
                checks = []
                with manager.open() as library:
                    for name, raw in originals.items():
                        parsed = rdf.parse_record(raw, source_name=name)
                        record = library.get(parsed.ebook.gutenberg_id)
                        require(record == parsed, "RDF/SQLite round trip differs")
                        require(record.source.data == raw, "raw RDF was changed")
                        for contribution in record.ebook.contributors:
                            for alias in contribution.agent.aliases:
                                require(
                                    record.ebook.gutenberg_id
                                    in library.find_ids(
                                        catalog.Filters(authors=(alias.text,))
                                    ),
                                    "alias query lost contributor",
                                )
                        checks.append(
                            {
                                "id": record.ebook.gutenberg_id,
                                "source": name,
                                "sha256": sha(raw),
                            }
                        )
                    authored = library.get(AUTHORED_ID).ebook
                    require(
                        [title.value.text for title in authored.titles]
                        == ["First title", "Second title", "Alternate title"],
                        "multiple titles lost or reordered",
                    )
                    agent = authored.contributors[0].agent
                    require(
                        [alias.text for alias in agent.aliases]
                        == ["Alice Example", "Another Name"],
                        "aliases collapsed or reordered",
                    )
                    for title in ("First title", "Second title", "Alternate title"):
                        require(
                            library.find_ids(catalog.Filters(titles=(title,)))
                            == (AUTHORED_ID,),
                            "title query mismatch",
                        )
                    for author in ("Writer, Alice", "Alice Example", "Another Name"):
                        require(
                            library.find_ids(catalog.Filters(authors=(author,)))
                            == (AUTHORED_ID,),
                            "author/alias query mismatch",
                        )
                    require(
                        library.find_ids(catalog.Filters(authors=("Shelley, Mary W.",)))
                        == (84,),
                        "retained Shelley alias lost",
                    )
                with manager.open() as reopened:
                    require(
                        reopened.get(AUTHORED_ID).ebook == authored,
                        "offline reopen differs",
                    )
                origins = qualify_narrow_installed.module_origins(package_root)
        report = {
            "completed": True,
            "installed_version": distribution.version,
            "runner_sha256": sha(pathlib.Path(__file__).read_bytes()),
            "helper_sha256": sha(
                pathlib.Path(qualify_narrow_installed.__file__).read_bytes()
            ),
            "records": checks,
            "authored_titles": [title.value.text for title in authored.titles],
            "authored_aliases": [alias.text for alias in agent.aliases],
            "network_bytes": 0,
            "offline_reopen": True,
            "module_origins": origins,
        }
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2)
            stream.write("\n")
        print(json.dumps({"completed": True, "records": len(checks)}))
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


if __name__ == "__main__":
    main()
