"""Read-only catalog planning and narrowly authorized first-use preparation.

This layer composes the lifecycle and acquisition APIs. It has no default URL,
UI prompts, refresh behavior, collection extraction or output replacement policy.
"""

import dataclasses
import pathlib

from lcats.gettenberg import errors
from lcats.gettenberg import lifecycle
from lcats.gettenberg import resources


class PreparationError(errors.CatalogError):
    """Preparation is blocked or lacks explicit setup approval."""


@dataclasses.dataclass(frozen=True, slots=True)
class PreparationPlan:
    """Serializable explanation; a plan is not an authorization token.

    action is not_required, reuse, setup or blocked. acquisition is none, local,
    reuse, download or blocked. Setup always needs approval, even from local bytes.
    """

    action: str
    reason: str
    catalog_state: str
    acquisition: str = "none"

    @property
    def approval_required(self) -> bool:
        """Whether executing this plan would initialize the catalog."""
        return self.action == "setup"


class CatalogPreparation:
    """Plan and prepare one catalog without implicit network authority.

    Args:
        cache_dir: LCATS cache root, resolved at construction when omitted.
        archive: Explicit local archive, mutually exclusive with request.
        request: Explicit archive-kind SourceRequest; no default is selected.
        policy: Acquisition bounds and permitted origins, offline by default.
        offline: Override online policy, including for verified cache reuse.

    Construction does not create directories. Both underlying stores use the
    same resolved root. Call prepare with approval only for required first setup;
    ready state is reused without consulting the supplied source.
    """

    def __init__(
        self,
        cache_dir=None,
        *,
        archive=None,
        request=None,
        policy=resources.NetworkPolicy(),
        offline=False,
    ):
        if type(offline) is not bool or not isinstance(policy, resources.NetworkPolicy):
            raise errors.CatalogInputError("use a NetworkPolicy and boolean offline")
        if archive is not None and request is not None:
            raise errors.CatalogInputError("choose archive or request, not both")
        if request is not None and (
            not isinstance(request, resources.SourceRequest)
            or request.kind != "archive"
        ):
            raise errors.CatalogInputError("catalog setup requires an archive request")
        self.manager = lifecycle.CatalogManager(cache_dir)
        self.store = resources.ResourceStore(self.manager.cache_dir)
        self.archive = pathlib.Path(archive) if archive is not None else None
        self.request = request
        self.policy = dataclasses.replace(policy, online=False) if offline else policy

    def plan(self, *, required=True) -> PreparationPlan:
        """Inspect local state without requests, prompts, locks or file creation.

        A collection with no metadata requirement does not inspect the catalog at
        all. Invalid catalog/cache evidence is never treated as a cache miss.
        """
        if type(required) is not bool:
            raise errors.CatalogInputError("required must be bool")
        if not required:
            return PreparationPlan(
                "not_required", "collection needs no catalog", "unchecked"
            )
        status = self.manager.status()
        state = status["state"]
        if state == "ready":
            return PreparationPlan("reuse", "active catalog is ready", state)
        if state == "invalid":
            return PreparationPlan("blocked", status["error"], state)
        if self.archive is not None:
            if not self.archive.is_file():
                return PreparationPlan(
                    "blocked", "local archive is not a file", state, "local"
                )
            return PreparationPlan(
                "setup", "build from explicit local archive", state, "local"
            )
        if self.request is None:
            return PreparationPlan(
                "blocked", "provide a local archive or explicit archive URL", state
            )
        acquisition = self.store.plan(self.request, policy=self.policy)
        return PreparationPlan(
            "blocked" if acquisition.action == "blocked" else "setup",
            acquisition.reason,
            state,
            acquisition.action,
        )

    def prepare(self, *, required=True, approved=False, dry_run=False):
        """Recheck and reuse/setup, or return a read-only plan for dry-run.

        Args:
            required: Whether the selected workflow needs metadata.
            approved: Authority for required first setup only, not refresh.
            dry_run: Return the plan without writes, acquisition or approval checks.

        Returns:
            PreparationPlan for dry-run/not-required, otherwise a Generation.

        Raises:
            PreparationError: Blocked plan or missing first-setup approval.
            CatalogError, ResourceError: Integrity, acquisition or build failure.
        """
        if type(approved) is not bool or type(dry_run) is not bool:
            raise errors.CatalogInputError("approved and dry_run must be bool")
        plan = self.plan(required=required)
        if dry_run or plan.action == "not_required":
            return plan
        if plan.action == "blocked":
            raise PreparationError(plan.reason)
        if plan.action == "reuse":
            # Do not pass a source: if the catalog disappears after planning,
            # setup fails rather than using authority intended only for reuse.
            return self.manager.setup()
        if not approved:
            raise PreparationError("catalog setup requires explicit approval")
        source = self.archive
        if self.request is not None:
            source = self.store.fetch(self.request, policy=self.policy)
        return self.manager.setup(source)
