"""Account for every RDF member and verify every current catalog round trip.

From lcats/: python ../experiments/10_gettenberg_qualification/scripts/qualify_snapshot.py ARCHIVE CATALOG_CACHE OUTPUT_JSON
Streams the pinned local archive; never extracts, downloads or writes the catalog.
For each member, compare parsed typed values, diagnostics and original bytes with
Catalog.get(). Inventory all XML elements/attributes and retained diagnostics.
This validates storage fidelity, not independent correctness of the RDF parser;
real/synthetic semantic fixtures provide that complementary evidence. POSIX alarm
900s, compressed256MiB, expanded4GiB, member2MiB, at most200000 members. Output is
exclusive-create and failure evidence is retained. RSS is platform-normalized.
"""

import argparse
import collections
import hashlib
import json
import pathlib
import resource
import signal
import socket
import sys
import tarfile
import time
from unittest import mock

from lxml import etree

from lcats.gettenberg import catalog as catalog_api
from lcats.gettenberg import lifecycle
from lcats.gettenberg import rdf

EXPECTED_ARCHIVE = "358f177c30818027ad93b3478da2248d7996999475d83e59288ee74423050b28"


def check_record(raw, member_name, catalog):
    """Verify the entire public record, including raw-source and diagnostic data."""
    parsed = rdf.parse_record(raw, source_name=member_name)
    stored = catalog.get(parsed.ebook.gutenberg_id)
    if stored is None or stored.ebook != parsed.ebook:
        raise ValueError(f"typed record mismatch: {member_name}")
    if stored.source != parsed.source or stored.diagnostics != parsed.diagnostics:
        raise ValueError(f"source/diagnostic mismatch: {member_name}")
    return parsed


def timeout(*_):
    """Bound the whole audit, including catalog reads and hash verification."""
    raise TimeoutError("snapshot qualification exceeded 900 seconds")


def main(argv=None):
    """Write exhaustive counts and exact per-record fidelity acceptance."""
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("archive", "cache", "output"):
        ap.add_argument(name, type=lambda value: pathlib.Path(value).resolve())
    args = ap.parse_args(argv)
    if args.output.exists():
        ap.error("output exists")
    if not hasattr(signal, "SIGALRM"):
        ap.error("POSIX SIGALRM required")
    result = {"qualified": False, "network_bytes": 0, "scope": __doc__}
    start = time.monotonic()
    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(900)
    try:
        if args.archive.stat().st_size > 256 * 1024**2:
            raise ValueError("compressed archive exceeds bound")
        digest = hashlib.sha256()
        with args.archive.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024**2), b""):
                digest.update(chunk)
        result["archive_sha256"] = digest.hexdigest()
        if result["archive_sha256"] != EXPECTED_ARCHIVE:
            raise ValueError("archive differs from pinned snapshot")
        tags, attributes, diagnostics = (collections.Counter() for _ in range(3))
        members = expanded = 0
        identities = set()
        with (
            lifecycle.CatalogManager(args.cache).open() as catalog,
            tarfile.open(args.archive, "r|bz2") as archive,
            mock.patch.object(
                socket, "socket", side_effect=AssertionError("network forbidden")
            ),
        ):
            if catalog.info["report"]["archive_sha256"] != EXPECTED_ARCHIVE:
                raise ValueError("catalog source identity mismatch")
            for member in archive:
                members += 1
                expanded += member.size
                if (
                    members > 200000
                    or expanded > 4 * 1024**3
                    or not member.isfile()
                    or not member.name.endswith(".rdf")
                    or member.size < 0
                    or member.size > 2 * 1024**2
                ):
                    raise ValueError("archive member/size bound")
                raw = archive.extractfile(member).read(2 * 1024**2 + 1)
                record = check_record(raw, member.name, catalog)
                if record.ebook.gutenberg_id in identities:
                    raise ValueError("duplicate ebook identity")
                identities.add(record.ebook.gutenberg_id)
                diagnostics.update(
                    (d.code, d.predicate_uri) for d in record.diagnostics
                )
                # Parse independently for the vocabulary inventory, retaining XML
                # container counts separately from semantic predicate claims.
                root = etree.fromstring(
                    raw,
                    etree.XMLParser(
                        resolve_entities=False, no_network=True, load_dtd=False
                    ),
                )
                for node in root.iter():
                    if isinstance(node.tag, str):
                        tags[node.tag] += 1
                        attributes.update(node.attrib.keys())
                archive.members.clear()
            found = set()
            after = 0
            while page := catalog.find_ids(after_id=after, limit=1000):
                found.update(page)
                after = page[-1]
            if found != identities:
                raise ValueError("catalog/archive ID sets differ")
            timings = []
            for _ in range(3):
                query_start = time.monotonic()
                english, after = [], 0
                while page := catalog.find_ids(
                    catalog_api.Filters(languages=("en",)), after_id=after, limit=1000
                ):
                    english.extend(page)
                    after = page[-1]
                timings.append(time.monotonic() - query_start)
            result["english_query"] = {
                "seconds": timings,
                "count": len(english),
                "ids_sha256": hashlib.sha256(json.dumps(english).encode()).hexdigest(),
            }

        if members != 78937:
            raise ValueError("snapshot member count mismatch")
        result.update(
            members=members,
            expanded_bytes=expanded,
            exact_record_roundtrips=members,
            elements=dict(sorted(tags.items())),
            attributes=dict(sorted(attributes.items())),
            diagnostics=[
                {"code": k[0], "predicate": k[1], "count": v}
                for k, v in sorted(diagnostics.items())
            ],
            qualified=True,
        )
    except BaseException as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        signal.alarm(0)
        result["seconds"] = time.monotonic() - start
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        result["peak_rss_bytes"] = rss if sys.platform == "darwin" else rss * 1024
        result["source_sha256"] = {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(pathlib.Path("src/lcats/gettenberg").glob("*.py"))
        }
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")


if __name__ == "__main__":
    main()
