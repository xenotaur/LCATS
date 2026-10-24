"""Testable helpers for explicit Gutenberg CI maintenance.

These commands are used by tools/gettenberg_ci.py and the manual maintenance
workflow. Preview is the default. Catalog work delegates to the supported CLI;
GitHub deletion uses fully paginated JSON and numeric IDs, never display tables.
No network request occurs merely by importing this module or computing keys.
"""

import argparse
import hashlib
import json
import pathlib
import re
import sqlite3
import subprocess
import sys

from lxml import etree

from lcats.gettenberg import _store
from lcats.gettenberg import catalog_cli
from lcats.gettenberg import lifecycle
from lcats.gettenberg import resources
from lcats.gettenberg import sources_cli

# Resource receipts currently accept formats 1 and 2. Bump this namespace when
# their storage compatibility changes, independently of SQLite/parser versions.
SOURCE_NAMESPACE = "Linux-lcats-gettenberg-source-v1-"
CATALOG_NAMESPACE = "Linux-lcats-gettenberg-catalog-v1-"
NAMESPACES = {
    "source": SOURCE_NAMESPACE,
    "catalog": CATALOG_NAMESPACE,
    "legacy": "Linux-gutenberg-",
}


def compatibility_fingerprint():
    """Hash shipped catalog code and the runtime that parses/stores its records.

    Including code prevents an accidental omitted version bump from restoring a
    compiled catalog built by different ingestion/validation logic. Source blobs
    have a separate stable namespace, so this does not require another download.
    """
    # Unpinned dependency upgrades can alter parsing even when LCATS source and
    # explicit parser versions are unchanged. Include both runtime and compiled
    # libxml versions, plus Python/SQLite used by ingestion and catalog storage.
    runtime = {
        "python": tuple(sys.version_info[:3]),
        "sqlite": sqlite3.sqlite_version,
        "lxml": etree.LXML_VERSION,
        "libxml_runtime": etree.LIBXML_VERSION,
        "libxml_compiled": etree.LIBXML_COMPILED_VERSION,
    }
    digest = hashlib.sha256(json.dumps(runtime, sort_keys=True).encode("utf-8"))
    folder = pathlib.Path(lifecycle.__file__).parent
    for path in sorted(folder.glob("*.py")):
        digest.update(path.name.encode("utf-8") + b"\0" + path.read_bytes())
    return digest.hexdigest()


def cache_keys(*, cache_dir=None, run_id=None):
    """Return restore prefixes and, for a ready catalog, immutable save keys.

    The source profile is part of both identities; catalog keys also contain
    schema/parser/code identity. Save keys add the activated archive digest and
    run/attempt identity, so conditional-refresh receipts are never overwritten.
    This lightweight key inspection does not itself verify full-file integrity;
    only a successful catalog operation may authorize the workflow's save steps.
    """
    profile = sources_cli.catalog_request().key
    source = SOURCE_NAMESPACE + profile + "-"
    catalog = (
        CATALOG_NAMESPACE
        + f"s{_store.SCHEMA_VERSION}-p{_store.PARSER_VERSION}-"
        + compatibility_fingerprint()
        + "-"
        + profile
        + "-"
    )
    result = {"source_prefix": source, "catalog_prefix": catalog}
    if cache_dir is not None:
        if not isinstance(run_id, str) or not re.fullmatch(r"[0-9]+-[0-9]+", run_id):
            raise ValueError("save keys require numeric run-attempt identity")
        status = lifecycle.CatalogManager(cache_dir).status()
        if status["state"] != "ready":
            raise ValueError("save keys require a ready catalog")
        archive = status["active"]["manifest"]["archive_sha256"]
        result.update(
            archive_sha256=archive,
            source_key=source + archive + "-" + run_id,
            catalog_key=catalog + archive + "-" + run_id,
        )
    return result


def maintain_catalog(operation, cache_dir, *, apply=False, allow_count_change=False):
    """Run or preview a supported catalog operation, preserving its exit status.

    Rebuild never downloads: with no compiled generation it can set up offline
    from a restored resource receipt. Invalid catalogs fail closed; they are not
    silently deleted or replaced. Setup permits first acquisition only on apply;
    refresh remains explicit and retains count-change validation.
    """
    if operation not in ("setup", "rebuild", "refresh"):
        raise ValueError("unknown catalog maintenance operation")
    status = lifecycle.CatalogManager(cache_dir).status()
    if status["state"] == "invalid":
        return {"error": status["error"], "state": "invalid"}, 2
    bootstrap = operation == "rebuild" and status["state"] == "missing"
    command = "setup" if bootstrap else operation
    args = [command, "--cache-dir", str(cache_dir)]
    if command in ("setup", "refresh"):
        args.extend(["--url", sources_cli.CATALOG_URL])
    if command == "setup":
        if apply:
            args.append("--yes")
        if bootstrap:
            args.append("--offline")
    elif allow_count_change:
        args.append("--allow-count-change")
    if not apply:
        args.append("--dry-run")
    message, code = catalog_cli.run(args)
    return {"command": ["lcats", "catalog", *args], "result": json.loads(message)}, code


def _github_json(arguments):
    """Run one GitHub CLI operation; propagate network/auth/HTTP failures."""
    result = subprocess.run(
        ["gh", *arguments], check=True, capture_output=True, text=True, timeout=120
    )
    return json.loads(result.stdout)


def cache_inventory(repository, ref):
    """Read every page of cache metadata for one exact repository/ref.

    GitHub's API applies ref filtering; selection checks it again locally. The
    endpoint and arguments are separate subprocess values, not shell snippets.
    """
    if not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*", repository
    ):
        raise ValueError("repository must be OWNER/REPO")
    if not isinstance(ref, str) or not re.fullmatch(
        r"(?:refs/heads/[^\s]+|refs/pull/[1-9][0-9]*/merge)", ref
    ):
        raise ValueError("an explicit refs/heads/... or refs/pull/... ref is required")
    pages = _github_json(
        [
            "api",
            "--method",
            "GET",
            "--paginate",
            "--slurp",
            f"repos/{repository}/actions/caches",
            "-f",
            f"ref={ref}",
            "-f",
            "per_page=100",
        ]
    )
    if not isinstance(pages, list):
        raise ValueError("invalid GitHub cache inventory")
    records = []
    for page in pages:
        if not isinstance(page, dict) or not isinstance(
            page.get("actions_caches"), list
        ):
            raise ValueError("invalid GitHub cache page")
        records.extend(page["actions_caches"])
    return records


def select_caches(records, kind, ref):
    """Select numeric IDs by fixed namespace and exact ref, rejecting bad data."""
    prefix = NAMESPACES[kind]
    selected = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("invalid GitHub cache record")
        identifier, key, branch = record.get("id"), record.get("key"), record.get("ref")
        if (
            type(identifier) is not int
            or identifier <= 0
            or not isinstance(key, str)
            or not isinstance(branch, str)
        ):
            raise ValueError("invalid GitHub cache identity")
        if key.startswith(prefix) and branch == ref:
            value = {"id": identifier, "key": key, "ref": branch}
            if identifier in selected and selected[identifier] != value:
                raise ValueError("conflicting cache ID in inventory")
            selected[identifier] = value
    return [selected[key] for key in sorted(selected)]


def manage_caches(repository, ref, kind, *, apply=False):
    """Preview or delete selected IDs; stop and report partial completion on error."""
    selected = select_caches(cache_inventory(repository, ref), kind, ref)
    result = {
        "repository": repository,
        "ref": ref,
        "namespace": NAMESPACES[kind],
        "selected": selected,
        "deleted_ids": [],
        "applied": apply,
    }
    if apply:
        for entry in selected:
            try:
                subprocess.run(
                    ["gh", "cache", "delete", str(entry["id"]), "--repo", repository],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
            except (subprocess.SubprocessError, OSError) as exc:
                result["error"] = str(exc)
                return result, 2
            result["deleted_ids"].append(entry["id"])
    return result, 0


def verify_saved(repository, ref, keys):
    """Require every newly saved snapshot to be visible at its exact key/ref.

    The cache action can report some upload failures as warnings. A successful
    catalog build is therefore insufficient evidence that a reusable snapshot
    exists. This read-only check makes a missing save fail the maintenance job.
    """
    if not keys or any(
        not key.startswith((SOURCE_NAMESPACE, CATALOG_NAMESPACE)) for key in keys
    ):
        raise ValueError("expected source/catalog cache keys are required")
    records = cache_inventory(repository, ref)
    selected = select_caches(records, "source", ref) + select_caches(
        records, "catalog", ref
    )
    visible = {record["key"] for record in selected}
    missing = sorted(set(keys) - visible)
    if missing:
        return {"error": "cache snapshots were not saved", "missing_keys": missing}, 2
    return {"verified_keys": sorted(set(keys)), "ref": ref}, 0


def build_parser():
    """Build explicit preview/apply commands for humans and workflow steps."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    keys = commands.add_parser(
        "keys", help="Print restore prefixes or post-success save keys"
    )
    keys.add_argument("--cache-dir")
    keys.add_argument("--run-id")
    keys.add_argument("--github-output", type=pathlib.Path)
    catalog = commands.add_parser(
        "catalog", help="Preview or apply supported catalog maintenance"
    )
    catalog.add_argument("operation", choices=("setup", "rebuild", "refresh"))
    catalog.add_argument("--cache-dir", required=True)
    catalog.add_argument("--allow-count-change", action="store_true")
    caches = commands.add_parser(
        "caches", help="List or delete caches in one namespace/ref"
    )
    caches.add_argument("--repo", required=True)
    caches.add_argument("--ref", required=True)
    caches.add_argument("--kind", choices=tuple(NAMESPACES), default="catalog")
    for command in (catalog, caches):
        mode = command.add_mutually_exclusive_group()
        mode.add_argument(
            "--apply", action="store_true", help="Perform the explicit operation"
        )
        mode.add_argument(
            "--dry-run", "--check", action="store_true", help="Preview only (default)"
        )
    verify = commands.add_parser(
        "verify-saved", help="Require exact uploaded cache keys/ref"
    )
    verify.add_argument("--repo", required=True)
    verify.add_argument("--ref", required=True)
    verify.add_argument("--key", action="append", required=True)
    return parser


def main(argv=None):
    """Print JSON and return 0 on success or 2 on invalid/failed operations."""
    args = build_parser().parse_args(argv)
    try:
        if args.command == "keys":
            result = cache_keys(cache_dir=args.cache_dir, run_id=args.run_id)
            if args.github_output:
                # Values are generated hashes/identifiers, never caller-controlled
                # multiline text that could inject an Actions output assignment.
                with args.github_output.open("a", encoding="utf-8") as stream:
                    for key, value in result.items():
                        stream.write(f"{key}={value}\n")
            code = 0
        elif args.command == "verify-saved":
            result, code = verify_saved(args.repo, args.ref, args.key)
        elif args.command == "catalog":
            result, code = maintain_catalog(
                args.operation,
                args.cache_dir,
                apply=args.apply,
                allow_count_change=args.allow_count_change,
            )
        else:
            result, code = manage_caches(
                args.repo, args.ref, args.kind, apply=args.apply
            )
    except (
        ValueError,
        KeyError,
        OSError,
        subprocess.SubprocessError,
        resources.ResourceError,
    ) as exc:
        result, code = {"error": str(exc)}, 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
