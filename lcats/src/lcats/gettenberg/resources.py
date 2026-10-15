"""Explicit, bounded original-byte acquisition with offline verified cache reuse.

Construction and plan() are read-only. fetch() acquires only under an explicit
online origin policy; a valid hit never triggers HEAD or conditional requests.
decode_text is a separate offline operation; fetch never decodes or sets up a catalog.
There is no implicit URL guessing or cleanup.
"""

from lcats.gettenberg import _decode_types
from lcats.gettenberg import _resource_decoding
from lcats.gettenberg import _lifecycle_io
from lcats.gettenberg import _resource_io
from lcats.gettenberg import _resource_selection
from lcats.gettenberg import _resource_transport
from lcats.gettenberg import _resource_types
from lcats.utils import env

# Public records and errors live behind this facade; private modules share the
# definitions without circular imports or exposing the transport implementation.
ResourcePreference = _resource_selection.ResourcePreference
ResourceSelection = _resource_selection.ResourceSelection
SelectionDiagnostic = _resource_selection.SelectionDiagnostic
DEFAULT_PREFERENCES = _resource_selection.DEFAULT_PREFERENCES
select_resource = _resource_selection.select_resource

DecodeOptions = _decode_types.DecodeOptions
DecodedText = _decode_types.DecodedText
DecodeDiagnostic = _decode_types.DecodeDiagnostic
ResourceDecodeError = _decode_types.ResourceDecodeError
decode_text = _resource_decoding.decode_text

SourceRequest = _resource_types.SourceRequest
NetworkPolicy = _resource_types.NetworkPolicy
SourceArtifact = _resource_types.SourceArtifact
RetrievalReceipt = _resource_types.RetrievalReceipt
AcquisitionPlan = _resource_types.AcquisitionPlan
ResourceError = _resource_types.ResourceError
ResourceInputError = _resource_types.ResourceInputError
ResourcePolicyError = _resource_types.ResourcePolicyError
ResourceIntegrityError = _resource_types.ResourceIntegrityError
ResourceTransportError = _resource_types.ResourceTransportError
ResourceDeferredError = _resource_types.ResourceDeferredError
ResourcePublicationError = _resource_types.ResourcePublicationError
ResourceLockError = _resource_types.ResourceLockError


class ResourceStore:
    """A cache-root-scoped original-byte store, independent of the metadata catalog.

    Args:
        cache_dir: LCATS cache root. None resolves LCATS_CACHE_DIR at construction.

    The caller owns the cache directory. Symlinked managed entries and corrupt
    evidence are refused, but another process with write access is not a security
    boundary. POSIX directory fsync is used; Windows guarantees atomic process-crash
    publication, not power-loss durability. Immutable publication needs hard links.
    """

    def __init__(self, cache_dir=None):
        self._cache = _resource_io.Cache(
            env.cache_root() if cache_dir is None else cache_dir
        )

    @staticmethod
    def _arguments(request, policy):
        if not isinstance(request, SourceRequest) or not isinstance(
            policy, NetworkPolicy
        ):
            raise ResourceInputError(
                "invalid_arguments", "use SourceRequest and NetworkPolicy"
            )

    def plan(
        self, request: SourceRequest, *, policy: NetworkPolicy = NetworkPolicy()
    ) -> AcquisitionPlan:
        """Inspect a verified cache hit or explain a miss, without writes or requests.

        Corrupt entries raise ResourceIntegrityError; they are never called misses.
        Reading a hit hashes its bytes, bounded by the policy's size limit.
        """
        self._arguments(request, policy)
        with _resource_io.translated_errors():
            artifact = self._cache.lookup(request, policy.byte_limit(request))
        if artifact is not None:
            return AcquisitionPlan(request, "reuse", "verified original", artifact)
        if not policy.online:
            return AcquisitionPlan(request, "blocked", "offline cache miss")
        if not policy.permits(request.request_url):
            return AcquisitionPlan(request, "blocked", "origin not permitted")
        return AcquisitionPlan(request, "download", "permitted cache miss")

    def fetch(
        self, request: SourceRequest, *, policy: NetworkPolicy = NetworkPolicy()
    ) -> SourceArtifact:
        """Reuse verified bytes, or serialize a bounded authorized acquisition.

        Rechecks after taking the persistent resource lock to avoid duplicate
        downloads. No catalog writer lock is taken. A cooperative monotonic budget
        covers lock waits, pacing, retries and streaming; DNS/OS blocking is not
        hard-cancellable. A returned path contains raw body bytes, never decoded text.
        """
        plan = self.plan(request, policy=policy)
        if plan.artifact is not None:
            return plan.artifact
        if plan.action == "blocked":
            raise ResourcePolicyError("network_denied", plan.reason)
        budget = _resource_transport.Budget(policy.seconds(request))
        with _resource_io.translated_errors():
            self._cache.directories(create=True)
            with _lifecycle_io.writer_lock(
                self._cache.root / "network.lock",
                min(policy.lock_timeout, budget.remaining()),
            ):
                budget.remaining()
                artifact = self._cache.lookup(request, policy.byte_limit(request))
                if artifact is not None:
                    return artifact
                return _resource_transport.acquire(request, policy, self._cache, budget)
