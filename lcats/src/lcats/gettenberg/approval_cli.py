"""Shared terminal approval for catalog setup; no library-side prompting."""

import dataclasses
import json
import sys

from lcats.gettenberg import preparation


def plan_report(service, plan):
    """Expose the exact source and acquisition bounds before approval."""
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
        "online": service.policy.online,
        "allowed_origins": list(service.policy.allowed_origins),
    }


def confirm_setup(service, plan, *, yes=False):
    """Approve actionable first setup only; caller must bypass this for dry-run.

    Reuse/blocked plans never prompt. Actual preparation still rechecks the plan.
    Redirected input never counts as interactive approval, even if it contains y.
    """
    if not plan.approval_required or yes:
        return yes
    if not sys.stdin.isatty():
        raise preparation.PreparationError(
            "catalog setup needs approval; rerun with --yes or use an interactive terminal"
        )
    print(json.dumps(plan_report(service, plan), indent=2), file=sys.stderr)
    print(
        "Initialize this metadata catalog? [y/N] ", end="", file=sys.stderr, flush=True
    )
    if sys.stdin.readline().strip().lower() not in ("y", "yes"):
        raise preparation.PreparationError("catalog setup declined; no changes made")
    return True
