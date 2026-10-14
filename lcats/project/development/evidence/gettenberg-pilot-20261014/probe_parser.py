"""Reproduce the bounded local-archive parsing probe from the lcats/ root.

Arguments: existing RDF tar.bz2 archive, output JSON path. This diagnostic
helper does not build a catalog or establish corpus/ingestion qualification.
Formatting/import layout was cleaned after the recorded probe; parsing and
measurement operations are unchanged.
"""

import collections
import hashlib
import json
import pathlib
import resource
import subprocess
import sys
import tarfile
import time

from lcats.gettenberg import errors
from lcats.gettenberg import rdf

archive = pathlib.Path(sys.argv[1])
output = pathlib.Path(sys.argv[2])
start = time.monotonic()
if archive.stat().st_size > 256 * 1024**2:
    raise ValueError("compressed size limit")
h = hashlib.sha256()
with archive.open("rb") as f:
    for chunk in iter(lambda: f.read(1024**2), b""):
        h.update(chunk)
source_hashes = {
    str(p): hashlib.sha256(p.read_bytes()).hexdigest()
    for p in pathlib.Path("src/lcats/gettenberg").glob("*.py")
}
head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
counts = collections.Counter()
codes = collections.Counter()
diagnostic_kinds = collections.Counter()
diagnostic_codes = collections.Counter()
examples = []
total = 0
n = 0
with tarfile.open(archive, "r|bz2") as tf:
    for n, member in enumerate(tf, 1):
        if n > 200000 or time.monotonic() - start > 300:
            raise ValueError("member/time limit")
        if member.size < 0 or member.size > 2 * 1024**2:
            raise ValueError("member size limit")
        total += member.size
        if total > 4 * 1024**3:
            raise ValueError("expanded size limit")
        if not member.isfile() or not member.name.endswith(".rdf"):
            raise ValueError("unexpected member")
        raw = tf.extractfile(member).read(2 * 1024**2 + 1)
        try:
            result = rdf.parse_record(raw, source_name=member.name)
            counts["parsed"] += 1
            counts["resources"] += len(result.ebook.resources)
            counts["contributions"] += len(result.ebook.contributors)
            for d in result.diagnostics:
                diagnostic_codes[d.predicate_uri] += 1
                diagnostic_kinds[d.code] += 1
            if result.diagnostics and len(examples) < 20:
                examples.append(
                    {
                        "member": member.name,
                        "diagnostics": [d.predicate_uri for d in result.diagnostics],
                    }
                )
        except errors.RecordParseError as exc:
            counts["rejected"] += 1
            codes[exc.code] += 1
            if len(examples) < 20:
                examples.append({"member": member.name, "error": str(exc)})
        tf.members.clear()
result = {
    "candidate_head": head,
    "parser_source_sha256": source_hashes,
    "diagnostic_codes": dict(diagnostic_kinds),
    "archive_sha256": h.hexdigest(),
    "archive_bytes": archive.stat().st_size,
    "expanded_bytes": total,
    "members": n,
    "counts": dict(counts),
    "error_codes": dict(codes),
    "diagnostic_predicates": dict(diagnostic_codes),
    "examples": examples,
    "elapsed_seconds": time.monotonic() - start,
    "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    "platform": "macOS ru_maxrss bytes",
    "network_bytes": 0,
    "scope": "Full cached archive pure parsing probe, not ingestion/catalog or corpus qualification.",
}
output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, indent=2))
