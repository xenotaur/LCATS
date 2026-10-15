# Original-byte acquisition

`lcats.gettenberg.resources` provides explicit HTTP(S) GET acquisition and a
verified local cache. It does not require a Gutenberg metadata catalog or
`gutenbergpy`. The existing `lcats gather` command has not migrated to this API.

This is the acquisition-core tranche of WI-GETTENBERG-0005. Automatic Gutenberg
alias/mirror routing, preferred-resource selection, conditional refresh, text
and container decoding, and catalog-manifest receipt integration are not yet
implemented. Every content type can be fetched as original bytes using an
explicit permitted URL; that does not promise an extractor for the format.

## Public interface

Import the module with `from lcats.gettenberg import resources`.

| Interface | Behavior |
|---|---|
| `SourceRequest(source_uri, request_url, kind="resource", route_policy="explicit-url-v1")` | Immutable source identity and explicit request route. No URL-pattern guessing. |
| `SourceRequest.from_url(url, kind="resource")` | Convenience constructor retaining the original supplied URI. |
| `NetworkPolicy(...)` | Immutable authority and resource bounds; offline by default. |
| `ResourceStore(cache_dir=None)` | Resolves `LCATS_CACHE_DIR` at construction, defaulting to `cache`; creates nothing. |
| `store.plan(request, policy=NetworkPolicy())` | Reads/verifies cached bytes and returns `AcquisitionPlan`: `reuse`, `download`, or `blocked`, with reason and optional artifact. No network, writes, locks, sleeps or prompts. |
| `store.fetch(request, policy=NetworkPolicy())` | Returns `SourceArtifact` from verified cache or performs an authorized bounded acquisition. |

A cache hit is usable offline, even when the current origin allowlist is empty.
It causes no HEAD, refresh or validator request. Limits still apply while reading
the hit. A corrupt entry raises an integrity error rather than becoming a miss.
A plan is a description, not approval: `fetch` rechecks cache and current policy.

`SourceArtifact` contains a `path` (`pathlib.Path`), `sha256`, byte `size`,
`receipt_sha256` and immutable `RetrievalReceipt`. Paths refer to raw local files.
The receipt records the acquiring caller's source URI and route policy, canonical
request/final URLs, redirect targets, body identity, UTC retrieval time, status,
selected headers and schema/transport versions. A later caller reusing those
bytes receives their original receipt; its different source label does not
rewrite acquisition history. Receipt retention does not certify ebook identity.

## Policy and bounds

| Field | Default | Meaning |
|---|---:|---|
| `online` | `False` | Permit network only when true and the origin is allowed. |
| `allowed_origins` | `()` | Tuple of scheme/host/port origins; no path/query/fragment. |
| `max_resource_bytes` | 32 MiB | Raw resource body/read bound. |
| `max_archive_bytes` | 256 MiB | Raw archive body/read bound. |
| `io_timeout` | 30 seconds | Maximum blocking connection/read timeout, at most 86,400 seconds. |
| `operation_seconds` | 180 seconds | Cooperative resource-operation budget. |
| `archive_seconds` | 900 seconds | Cooperative archive-operation budget. |
| `lock_timeout` | 10 seconds | Lock wait, between zero and 60; capped by remaining budget. |
| `min_interval` | 2 seconds | Minimum request-start spacing; overrides cannot reduce it. |
| `max_retries` | 2 | Additional attempts across the operation. |
| `max_redirects` | 5 | Redirects across the operation; receipt format also caps this at 256. |

Reject booleans masquerading as numbers, nonfinite time limits and invalid bounds.
Positive byte/time limits are required, except zero lock wait is valid. Retry and
redirect counts are nonnegative integers. Each response is streamed in chunks no
larger than 128 KiB, with at most one byte beyond the body limit read to detect
oversize. Advertised oversize, truncated bodies and invalid lengths fail explicitly.

Only absent transfer coding or one `Transfer-Encoding: chunked` is supported.
Chunk framing is removed; other/duplicate transfer codings and simultaneous
Transfer-Encoding/Content-Length are rejected before publication. Content-Encoding
bytes are preserved with their header for later decoding.

The private urllib opener verifies TLS certificates and ignores environment
proxies. There are no cookies, credentials, authentication or custom request
headers. Requests identify LCATS and request `Accept-Encoding: identity`. Only
HTTP(S) is supported. An explicitly allowed `http://` origin opts into HTTP;
HTTPS redirects may not downgrade to HTTP. Every redirect needs an allowed
origin and passes URL validation; loops and missing/ambiguous Location fail.
No denial triggers another mirror, resource or format guess.

Retryable HTTP statuses are 408, 429, 500, 502, 503 and 504. Temporary DNS,
connection/read failures are bounded by the same attempt and time budgets.
TLS verification errors, malformed status lines/overlong headers, other HTTP
statuses, malformed representation metadata,
policy failures and integrity failures do not trigger speculative fallback.
Fallback backoff is two then four seconds; valid longer Retry-After delays take
precedence. Retry-After supports integer seconds and HTTP dates, including on
redirects. A required delay beyond remaining time raises `ResourceDeferredError`
with `next_eligible_at` (Unix UTC seconds), without an excessive sleep.

Deadlines are **cooperative**, checked around I/O and before retry/wait. Each real
socket read has its timeout capped by remaining time, including raw reads used
to parse status lines, headers, chunk extensions and trailers. Standard-library DNS/OS
blocking cannot be hard-cancelled; this is not a guarantee of exact wall-clock
termination. Cache verification and filesystem durability also depend on local I/O.
The urllib response adapter uses the socket makefile interface and is covered
by local HTTP/HTTPS framing tests.

## Coordination and cache layout

All acquisitions sharing a resolved cache root use one persistent SQLite network
lock, held through response streaming/publication. Rechecking the cache after
locking avoids duplicate downloads. A killed process releases its lock. Never
unlink the lock file to resolve contention. Resource and catalog publishers also
share a persistent archive-publication leaf lock during archive publication,
verification and temporary-link cleanup. Lock order is resource-network or
catalog-writer, then archive-publication; never acquire an outer lock while
holding the archive lock. Cache hits remain read-only and lock-free.
Different roots/machines and external
clients are outside this coordination boundary.

Atomic pacing metadata preserves global request spacing and per-origin cooldowns
across processes. Before dispatch it persists an in-flight marker; after each
attempt it conservatively renews spacing from completion. A slow metadata fsync
therefore cannot consume the gap owed to the next actual GET. A new process
finding an abandoned in-flight marker waits a fresh full interval. Wall/monotonic
observations protect normal same-boot pacing.
After a reboot or large clock step, outstanding delays are conservatively rebased
and saved before waiting; some previously elapsed delay may be repeated rather
than bypassing a server cooldown. The operation budget still bounds waiting.
At the 256-origin/64-KiB metadata capacity, pending cooldowns collapse into a
conservative global deadline equal to the latest pending cooldown. No observed
Retry-After is dropped. Malformed pacing state is an explicit integrity error.

```text
<cache>/gettenberg/
  archives/<body-sha256>.tar.bz2
  archive-publication.sqlite
  resources/
    objects/<body-sha256>
    receipts/<receipt-sha256>.json
    refs/<request-key>.json
    tmp/<random>.part
    network.lock
    pacing.json
```

The request key hashes versioned GET identity, canonical URL, fixed representation
policy and storage kind. Scheme/host case and default ports normalize; fragments
are removed; path escaping and query order remain significant. URLs must be ASCII,
with other characters percent-encoded. Credentials, controls and malformed escapes
are rejected. This normalization makes no claim that two distinct URLs have equal
bytes. Archive/resource kinds use separate keys and storage locations.

Publication fsyncs the temporary body, publishes it without clobbering an existing
hash object, publishes an immutable receipt, then atomically replaces the request
reference. Only a complete hash-verified receipt/body pair is a cache hit. Failed
partial bodies are removed when possible; orphan objects/receipts can remain.
There is no automatic pruning, repair, partial resume or refresh in this tranche.
Archive cleanup, including failure cleanup, shares the publication lock. Both resource failure cleanup and catalog
cleanup retain linked archive temporary orphans so it cannot change an immutable
archive inode while a lock-free resource reader verifies it.
Temporary hard links are removed before reference publication so concurrent
hash checks do not mistake cleanup for content mutation. A failure after reference
replacement reports possible publication explicitly; a pacing durability failure
before resource publication reports an integrity error. A completion-pacing failure
after reference publication reports `ResourcePublicationError(published=True)`;
the resource is already visible even though coordination persistence failed.

The caller owns and trusts the local cache. Managed symlinks and corrupt evidence
are refused, but the store is not an isolation boundary against another user with
write access. Publication requires hard-link support. POSIX directory fsync is
used; Windows offers process-crash atomicity, not guaranteed power-loss durability.

`kind="archive"` shares the offline catalog lifecycle's archive namespace. It
preserves bytes only: it does not verify RDF, initialize/activate a catalog, or
embed retrieval provenance in a generation. Passing its path to the existing
local lifecycle remains an explicit offline operation with local-only provenance.

## Errors

All public errors below derive from `resources.ResourceError`, itself a
`gettenberg.errors.GettenbergError`. Each carries a machine-readable `code`.

| Error | Meaning / response |
|---|---|
| `ResourceInputError` | Invalid request/policy; fix caller input. |
| `ResourcePolicyError` | Offline miss, disallowed origin or HTTPS downgrade. |
| `ResourceIntegrityError` | Invalid cache paths, hashes, schema or pacing state; investigate, do not silently redownload over evidence. |
| `ResourceTransportError` | HTTP/connection/framing/size/deadline failure; no complete new entry promised. |
| `ResourceDeferredError` | Wait exceeds the current budget; inspect `next_eligible_at` before scheduling another operation. |
| `ResourceLockError` | Shared acquisition is busy beyond the allowed lock wait. |
| `ResourcePublicationError` | `published=True`: reference replacement occurred but durability confirmation failed; inspect cache state. |

See [the acquisition how-to](../how-to/gettenberg-resources.md) for planning and
explicit download examples. The control-plane
[acceptance matrix](../../project/development/gettenberg-acquisition-design.md)
tracks the remaining work separately from this implemented reference.
