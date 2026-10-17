"""Thin catalog commands using the same preparation, acquisition and lifecycle APIs."""

import argparse
import dataclasses
import json
import sys
from urllib import parse

from lcats.gettenberg import errors
from lcats.gettenberg import preparation
from lcats.gettenberg import resources


def build_parser(add_help=True):
    """Build explicit catalog operations; no implicit default mirror exists."""
    parser = argparse.ArgumentParser(
        prog="lcats catalog", add_help=add_help, description=__doc__
    )
    commands = parser.add_subparsers(dest="catalog_command", required=True)
    for name in ("status", "setup", "refresh", "rebuild"):
        command = commands.add_parser(name)
        command.add_argument(
            "--cache-dir", help="LCATS cache root; otherwise LCATS_CACHE_DIR."
        )
        if name == "status":
            continue
        command.add_argument(
            "--dry-run",
            action="store_true",
            help="Inspect only; no writes or requests.",
        )
        if name in ("setup", "refresh"):
            command.add_argument(
                "--offline", action="store_true", help="Forbid all network requests."
            )
            source = command.add_mutually_exclusive_group(required=name == "refresh")
            if name == "setup":
                source.add_argument(
                    "--archive", help="Explicit local RDF tar.bz2 archive."
                )
            source.add_argument(
                "--url",
                help="Explicit catalog archive URL.",
            )
            command.add_argument(
                "--allow-origin",
                action="append",
                default=[],
                help="Additional permitted redirect origin (repeatable).",
            )
        if name == "setup":
            command.add_argument(
                "--yes", action="store_true", help="Approve required first setup only."
            )
        if name == "rebuild":
            command.add_argument(
                "--archive", help="Local archive; otherwise use retained active source."
            )
        if name in ("refresh", "rebuild"):
            command.add_argument(
                "--allow-count-change",
                action="store_true",
                help="Explicitly accept a changed ebook count.",
            )
    return parser


def _preparation(args):
    """Translate explicit CLI authority into a bounded network policy."""
    url = getattr(args, "url", None)
    request = resources.SourceRequest.from_url(url, kind="archive") if url else None
    origins = ()
    if request is not None:
        parts = parse.urlsplit(request.request_url)
        origins = (f"{parts.scheme}://{parts.netloc}", *args.allow_origin)
    elif getattr(args, "allow_origin", None):
        raise errors.CatalogInputError("--allow-origin requires --url")
    policy = resources.NetworkPolicy(online=bool(url), allowed_origins=origins)
    return preparation.CatalogPreparation(
        args.cache_dir,
        archive=getattr(args, "archive", None),
        request=request,
        policy=policy,
        offline=getattr(args, "offline", False),
    )


def _plan_report(service, plan):
    """Expose the source and acquisition decision before requesting approval."""
    return {
        **dataclasses.asdict(plan),
        "approval_required": plan.approval_required,
        "cache_dir": str(service.manager.cache_dir),
        "source": (
            str(service.archive)
            if service.archive is not None
            else (service.request.request_url if service.request else None)
        ),
        "max_archive_bytes": service.policy.max_archive_bytes,
    }


def _setup(args, service):
    """Prompt only for actionable missing setup, never for reuse or dry-run."""
    plan = service.plan()
    report = _plan_report(service, plan)
    if args.dry_run:
        return report, 2 if plan.action == "blocked" else 0
    approved = args.yes
    if plan.approval_required and not approved:
        if not sys.stdin.isatty():
            raise preparation.PreparationError(
                "catalog setup needs approval; rerun with --yes or use an interactive terminal"
            )
        print(json.dumps(report, indent=2), file=sys.stderr)
        print(
            "Initialize this metadata catalog? [y/N] ",
            end="",
            file=sys.stderr,
            flush=True,
        )
        approved = sys.stdin.readline().strip().lower() in ("y", "yes")
        if not approved:
            raise preparation.PreparationError(
                "catalog setup declined; no changes made"
            )
    generation = service.prepare(approved=approved)
    return {"generation_id": generation.generation_id, "reused": generation.reused}, 0


def _change(args, service):
    """Explicit refresh/rebuild never inherits setup consent."""
    status = service.manager.status()
    if status["state"] != "ready":
        raise preparation.PreparationError(
            "refresh/rebuild requires a ready catalog; inspect catalog status first"
        )
    if args.catalog_command == "refresh":
        plan = service.store.plan(service.request, policy=service.policy, refresh=True)
        if args.dry_run:
            return {
                "action": plan.action,
                "reason": plan.reason,
                "source": service.request.request_url,
            }, (2 if plan.action == "blocked" else 0)
        if plan.action == "blocked":
            raise preparation.PreparationError(plan.reason)
        source = service.store.refresh(service.request, policy=service.policy)
        generation = service.manager.update(
            source, allow_count_change=args.allow_count_change
        )
    else:
        if args.dry_run:
            source = service.archive or status["active"]["archive_path"]
            return {
                "action": "rebuild",
                "source": str(source),
                "allow_count_change": args.allow_count_change,
            }, 0
        generation = service.manager.rebuild(
            service.archive, allow_count_change=args.allow_count_change
        )
    return {"generation_id": generation.generation_id, "reused": generation.reused}, 0


def run(argv=None, *, parsed_args=None):
    """Return (JSON message, exit status): 0 success, 2 invalid/blocked/failed.

    Error results preserve count-change candidate identity for explicit recovery.
    The lifecycle retains earlier generations on validation/activation failures.
    """
    args = parsed_args if parsed_args is not None else build_parser().parse_args(argv)
    try:
        service = _preparation(args)
        if args.catalog_command == "status":
            report = service.manager.status()
            code = 2 if report["state"] == "invalid" else 0
        elif args.catalog_command == "setup":
            report, code = _setup(args, service)
        else:
            report, code = _change(args, service)
    except (
        errors.GettenbergError,
        resources.ResourceError,
        OSError,
        ValueError,
    ) as exc:
        report, code = {"error": str(exc)}, 2
        if isinstance(exc, errors.CatalogCountChangeError):
            report["candidate_generation_id"] = exc.generation_id
    return json.dumps(report, indent=2, sort_keys=True), code
