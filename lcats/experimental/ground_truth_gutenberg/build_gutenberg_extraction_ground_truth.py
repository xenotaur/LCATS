"""Prepare editable Gutenberg opening examples using the LCATS offline cache.

Run from the LCATS Python environment:
    python build_gutenberg_extraction_ground_truth.py --archive new.zip

Uses the same source setup as lcats.gatherers.main: catalog preparation,
NetworkPolicy(online=False), CatalogPreparation.manager.open(), and
GutenbergStorySource(catalog, service.store, routes=routes, policy=policy).
Only Gettenberg's wrapper cleanup is used; no narrative-start filtering.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
from pathlib import Path
import re
import sys
from urllib import parse as urlparse
from zipfile import ZipFile


DEFAULT_ARCHIVE = Path("new.zip")
DEFAULT_OUTPUT = Path("gutenberg_extraction_ground_truth.json")


def corpus_records(archive: Path) -> dict[int, dict]:
    """Index JSON story records by the canonical Gettenberg provenance ID."""
    records = {}
    with ZipFile(archive) as zipped:
        for member in sorted(zipped.namelist()):
            if not member.endswith("/story.json"):
                continue
            with zipped.open(member) as stream:
                record = json.load(stream)
            metadata = record.get("metadata") or {}
            provenance = metadata.get("gettenberg") or {}
            gutenberg_id = provenance.get("gutenberg_id")
            if gutenberg_id is None:
                raise ValueError(f"Missing Gettenberg Gutenberg ID: {member}")
            gutenberg_id = int(gutenberg_id)
            if gutenberg_id in records:
                raise ValueError(f"Duplicate Gutenberg ID {gutenberg_id}: {member}")
            records[gutenberg_id] = {
                "archive_member": member,
                "catalog_name": record.get("name"),
                "catalog_authors": record.get("author", []),
            }
    if not records:
        raise ValueError(f"No story.json files in {archive}")
    return records


def _seems_to_contain_body(lines: list[str]) -> bool:
    """Weak signal ONLY for deciding whether to supply extra context.

    A long mixed-case line suggests body MAY have started. This method never
    chooses or removes a narrative boundary, and short dialogue may prompt
    extra context. False positives merely mean the first 20 lines are retained.
    """
    for line in lines:
        s = line.strip()
        if len(s) < 65 or len(s.split()) < 10:
            continue
        if s.isupper():
            continue
        if re.match(
            r"(?i)^(?:copyright|project gutenberg|produced by|published by|"
            r"printed by|all rights reserved|transcriber's note)",
            s,
        ):
            continue
        return True
    return False


def opening_text(text: str, initial_lines: int = 20, max_lines: int = 100,
                 extension_lines: int = 20) -> tuple[str, int]:
    """Keep original physical line breaks, indentation, italics and blanks.

    First take 20 physical lines (including blanks). If none looks like prose,
    add 20 more at a time, stopping once some plausible body is visible or the
    configured cap is reached. No line is deleted or re-ordered.
    """
    if initial_lines < 1 or max_lines < initial_lines or extension_lines < 1:
        raise ValueError("Require 1 <= initial_lines <= max_lines; extension_lines >= 1")
    lines = text.replace("\r\n", "\n").replace("\r", "\n").splitlines(keepends=True)
    count = min(initial_lines, len(lines))
    while count < min(max_lines, len(lines)):
        if _seems_to_contain_body([line.rstrip("\n") for line in lines[:count]]):
            break
        count = min(count + extension_lines, max_lines, len(lines))
    return "".join(lines[:count]), count


def generate_ground_truth(
    *,
    source,
    archive: Path = DEFAULT_ARCHIVE,
    output: Path = DEFAULT_OUTPUT,
    initial_lines: int = 20,
    max_lines: int = 100,
    extension_lines: int = 20,
    errors_output: Path | None = None,
) -> dict:
    """Create the dataset using an ALREADY CONFIGURED offline Gettenberg source.

    All records contain identical original_opening/first_narrative_text initially.
    Missing source/cache entries are recorded separately and *not* presented as
    reviewed text. Output is atomically replaced and existing annotations are
    never silently overwritten.
    """
    archive = Path(archive)
    output = Path(output)
    errors_output = Path(errors_output) if errors_output else output.with_name(
        output.stem + "_errors.json"
    )
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite human annotations: {output}")
    if errors_output.exists():
        raise FileExistsError(f"Refusing to overwrite existing errors: {errors_output}")

    corpus = corpus_records(archive)
    results = []
    errors = []
    for index, (gutenberg_id, details) in enumerate(sorted(corpus.items()), 1):
        if index % 100 == 0:
            print(f"Processed {index}/{len(corpus)} Gutenberg IDs", file=sys.stderr)
        try:
            metadata = source.metadata(gutenberg_id)
            if metadata is None:
                raise LookupError("No metadata in the offline catalog")
            prepared = source.read(metadata)
            cleaned = prepared.cleaned.text
            if not isinstance(cleaned, str):
                raise TypeError("Gettenberg prepared.cleaned.text is not a string")
            opening, count = opening_text(
                cleaned, initial_lines, max_lines, extension_lines
            )
            if not opening.strip():
                raise ValueError("Cleaned Gutenberg source is empty")
            titles = list(metadata.titles)
            authors = list(metadata.authors)
            results.append({
                "gutenberg_id": gutenberg_id,
                "title": titles,
                "authors": authors,
                "original_opening": opening,
                "first_narrative_text": opening,
                "review_status": "pending",
                "physical_lines_included": count,
            })
        except Exception as exc:
            errors.append({
                "gutenberg_id": gutenberg_id,
                "archive_member": details["archive_member"],
                "error_type": type(exc).__name__,
                "error": str(exc),
            })

    _write_json_new(output, results)
    _write_json_new(errors_output, errors)
    return {
        "total_ids": len(corpus),
        "records_written": len(results),
        "failed_ids": len(errors),
        "output": str(output),
        "errors_output": str(errors_output),
    }


def _write_json_new(path: Path, data) -> None:
    """Create new output exclusively; never overwrite review edits."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


@contextmanager
def open_cached_gutenberg_source(
    *,
    cache_dir=None,
    catalog_archive=None,
    catalog_url=None,
    main_root=None,
    generated_root=None,
):
    """Create the identical Gettenberg source used by LCATS gatherer main.

    Network access is *always disabled*. The catalog and story text must be
    available in the configured cache (or a supplied local catalog archive).
    The catalog manager stays open while callers read story metadata/text.
    """
    from lcats.gettenberg import preparation
    from lcats.gettenberg import resources
    from lcats.gettenberg import sources_cli
    from lcats.gatherers import gutenberg_source

    routes = sources_cli.gutenberg_routes(main_root, generated_root)
    request = sources_cli.catalog_request(
        archive=catalog_archive,
        url=catalog_url,
    )
    urls = [routes.main_root, routes.generated_root]
    if request is not None:
        urls.append(request.request_url)
    origins = [
        f"{urlparse.urlsplit(url).scheme}://{urlparse.urlsplit(url).netloc}"
        for url in urls
    ]
    policy = resources.NetworkPolicy(
        online=False,
        allowed_origins=tuple(dict.fromkeys(origins)),
    )
    service = preparation.CatalogPreparation(
        cache_dir,
        archive=catalog_archive,
        request=request,
        policy=policy,
        offline=True,
    )
    # No interactive setup approval: this is a cache-only, read-oriented task.
    # Offline preparation may use already cached resources; it cannot download.
    service.prepare(approved=False)
    with service.manager.open() as catalog:
        source = gutenberg_source.GutenbergStorySource(
            catalog,
            service.store,
            routes=routes,
            policy=policy,
        )
        yield source


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--initial-lines", type=int, default=20)
    parser.add_argument("--max-lines", type=int, default=100)
    parser.add_argument("--extension-lines", type=int, default=20)
    parser.add_argument("--cache-dir", type=Path, default=None,
                        help="Override LCATS's normal Gettenberg cache location")
    parser.add_argument("--catalog-archive", type=Path, default=None,
                        help="Optional local metadata archive, as in LCATS gather")
    parser.add_argument("--catalog-url", default=None,
                        help="Catalog URL used for matching cached configuration; never fetched")
    parser.add_argument("--main-root", default=None,
                        help="Override LCATS's Gutenberg main resource root")
    parser.add_argument("--generated-root", default=None,
                        help="Override LCATS's Gutenberg generated resource root")
    args = parser.parse_args(argv)

    with open_cached_gutenberg_source(
        cache_dir=args.cache_dir,
        catalog_archive=args.catalog_archive,
        catalog_url=args.catalog_url,
        main_root=args.main_root,
        generated_root=args.generated_root,
    ) as source:
        result = generate_ground_truth(
            source=source,
            archive=args.archive,
            output=args.output,
            initial_lines=args.initial_lines,
            max_lines=args.max_lines,
            extension_lines=args.extension_lines,
        )
    print(json.dumps(result, indent=2))
    if result["failed_ids"]:
        print("WARNING: Some cached sources unavailable; see errors JSON", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
