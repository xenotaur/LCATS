# Original-byte acquisition

`lcats.gettenberg.resources` provides explicit HTTP(S) GET acquisition and a
verified local cache. It does not require a Gutenberg metadata catalog or
`gutenbergpy`. The existing `lcats gather` command has not migrated to this API.

This covers acquisition and pure resource selection within WI-GETTENBERG-0005.
Automatic Gutenberg alias/mirror routing and catalog-manifest receipt integration
are not yet implemented. Explicit conditional refresh is available. [Offline decoding](gettenberg-decoding.md)
is a separate operation. Every content type can be fetched as original bytes using an
explicit permitted URL; that does not promise an extractor for the format.

## Public interface

Import the module with `from lcats.gettenberg import resources`.

| Interface | Behavior |
|---|---|
| `select_resource(ebook, preferences=DEFAULT_PREFERENCES)` | Pure declared-format selection with stable source-order ties and diagnostics; see below. |
| `SourceRequest(source_uri, request_url, kind="resource", route_policy="explicit-url-v1")` | Immutable source identity and explicit request route. No URL-pattern guessing. |
| `SourceRequest.from_url(url, kind="resource")` | Convenience constructor retaining the original supplied URI. |
| `NetworkPolicy(...)` | Immutable authority and resource bounds; offline by default. |
| `ResourceStore(cache_dir=None)` | Resolves `LCATS_CACHE_DIR` at construction, defaulting to `cache`; creates nothing. |
| `store.plan(request, policy=NetworkPolicy(), refresh=False)` | Reads/verifies cached bytes and returns `AcquisitionPlan`: `reuse`, `refresh`, `download`, or `blocked`, with reason and optional artifact. No network, writes, locks, sleeps or prompts. |
| `store.fetch(request, policy=NetworkPolicy())` | Returns `SourceArtifact` from verified cache or performs an authorized bounded acquisition. |
| `store.refresh(request, policy=NetworkPolicy())` | Explicitly validates a cached representation or acquires a complete replacement; requires online authority even on hits. |

A cache hit is usable offline, even when the current origin allowlist is empty.
It causes no HEAD, refresh or validator request. Limits still apply while reading
the hit. A corrupt entry raises an integrity error rather than becoming a miss.
A plan is a description, not approval: `fetch` rechecks cache and current policy.

`SourceArtifact` contains a `path` (`pathlib.Path`), `sha256`, byte `size`,
`receipt_sha256` and immutable `RetrievalReceipt`. Paths refer to raw local files.
The receipt records the acquiring caller's source URI and route policy, canonical
request/final URLs, redirect targets, body identity, UTC retrieval time, status,
selected headers and schema/transport versions. A later caller reusing those
bytes receives their current receipt; its different source label does not
rewrite acquisition history. Receipt retention does not certify ebook identity.

## Explicit refresh and provenance

`plan(..., refresh=True)` remains read-only. It reports `refresh` for a verified
hit with online authority, explaining conditional or unconditional GET, `download`
for an authorized miss, and `blocked` for an offline/disallowed request. A blocked
plan can still expose the verified cached artifact; this does not authorize refresh.
It describes current evidence, not a promise about redirects or the eventual response.

`refresh` rechecks the cache after taking the network lock. If another successful
acquisition/refresh changed the receipt while this call waited, it returns that
verified update without another request. Sequential explicit calls each refresh.
It always starts at the requested URL, rechecking redirect policy on every hop.
Syntactically usable ETag and Last-Modified values are sent only at the **exact
canonical final URL** recorded by the previous receipt. Neither another path on
the same origin nor a cross-origin redirect inherits them. Missing or malformed
validators cause an unconditional GET. Normal `fetch` still does no freshness work.

A matching `304` keeps body/hash, original retrieval time and original caller's
source label. It appends a new immutable receipt and atomically switches the request
reference without relinking or rewriting the body. A full `200` records a new
retrieval, even if its bytes happen to hash identically. Both retain prior receipts
and bodies. A failed response, invalid cache, or pre-reference publication failure
leaves the old reference intact; errors are explicit, never silent stale fallback.
The existing post-reference publication-uncertainty error also applies to refresh.

New receipts use schema 2; schema-1 files remain readable, including by the offline
decoder, without rewriting their bytes or changing their hashes. Additional fields:

| Field | Meaning |
|---|---|
| `previous_receipt_sha256` | Previous current receipt for a refresh, or `None` on a cold acquisition. Retained audit link, not a recursively validated chain. |
| `validated_at` | UTC time of a successful `304`, or `None` for a `200`. Local clock movement can put this before retrieval time. |
| `validation_headers` | Selected headers actually returned by the latest `304`; must contain a valid validator on persisted reads; empty for `200`. |

`status` records the latest event (`200` or `304`); `headers` contains effective
selected metadata, carrying omitted fields forward after `304`. `retrieved_at`
continues to name the original full-body retrieval. Receipt identity changes even
when body identity does not. A saved old `SourceArtifact` remains usable by the
offline decoder. There is no automatic age refresh or pruning.

Validation deliberately fails closed: unsolicited/cold `304`, a response from a
URL where no conditional headers were sent, or contradictory returned validators
cannot select old bytes. A returned strong ETag must equal the sent ETag; a weak
returned tag can weakly match it. Last-Modified governs matching when no ETag was
sent. The corresponding validator must be returned and match; a missing one fails
closed. Equivalent valid HTTP date forms compare as UTC instants.
Malformed/duplicate selected response headers are refused. A changed or newly
introduced Content-Type/Content-Encoding in `304` is also refused rather than
reinterpreting the original bytes; this limited client does not automatically retry
such contradictions unconditionally. The prior entry remains available via `fetch`.
Weak validation means semantic currency, **not proof that current remote bytes
are identical**. Local bytes are always independently hashed.

These binding rules follow [HTTP conditional-request semantics](https://www.rfc-editor.org/rfc/rfc9110.html#section-13.1)
and conservative [304 response identification](https://www.rfc-editor.org/rfc/rfc9111.html#section-4.3.4).
This is an explicit archival source store, not a browser/shared cache implementing
Cache-Control freshness, Vary negotiation, authentication, or conditional ranges.

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

Publication bounds serialized receipt metadata before linking any body into the
immutable store. It fsyncs the temporary body, publishes it without clobbering an existing
hash object, publishes an immutable receipt, then atomically replaces the request
reference. Only a complete hash-verified receipt/body pair is a cache hit. Failed
partial bodies are removed when possible; orphan objects/receipts can remain.
There is no automatic pruning, repair, partial resume or age-based refresh.
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
| `ResourcePolicyError` | Offline miss/refresh, disallowed origin or HTTPS downgrade. |
| `ResourceIntegrityError` | Invalid cache paths, hashes, schema or pacing state; investigate, do not silently redownload over evidence. |
| `ResourceTransportError` | HTTP/connection/framing/size/deadline failure; no complete new entry promised. |
| `ResourceDeferredError` | Wait exceeds the current budget; inspect `next_eligible_at` before scheduling another operation. |
| `ResourceLockError` | Shared acquisition is busy beyond the allowed lock wait. |
| `ResourcePublicationError` | `published=True`: reference replacement occurred but durability confirmation failed; inspect cache state. |

See [the acquisition how-to](../how-to/gettenberg-resources.md) for planning and
explicit download examples. The control-plane
[acceptance matrix](../../project/development/gettenberg-acquisition-design.md)
tracks the remaining work separately from this implemented reference.

## Pure resource selection

`resources.select_resource(ebook, *, preferences=resources.DEFAULT_PREFERENCES)`
returns an immutable `ResourceSelection`. It performs no I/O and requires no cache
or catalog setup. The default ordered preferences are `text/plain` with UTF-8,
any `text/plain`, then `text/html`. Supply a nonempty tuple of
`ResourcePreference(media_type, charset=None)` to replace that order. Media types
are exact, case-insensitive type/subtype strings without parameters or wildcards;
charset aliases known to Python normalize equally, unknown charset names compare
case-insensitively. None accepts any or absent charset. Invalid caller arguments
raise `ResourceInputError`. Source media claims must use ASCII MIME syntax;
malformed, empty or extended (RFC 2231) charset parameters are diagnosed and
ignored as whole claims rather than guessed.

Ranking is preference index, resource source index, then format source index.
Every format claim is considered, and all original metadata is preserved. A result
contains `resource` (the original object), `source_index`, `preference_index`,
`matched_format` (the unchanged source claim), `diagnostics`, and
`policy_version="declared-media-v1"`. The four selection fields are None when no
claim matches. Choosing PDF/EPUB/audio explicitly is supported as metadata
selection; it does not imply an extractor or permitted download route.

Diagnostics are immutable `SelectionDiagnostic` records with `code`, `message`,
and optional zero-based `resource_index` / `format_index`. Stable codes are:

| Code | Meaning |
|---|---|
| `invalid_format` | Malformed media claim ignored; never silently treated as plain text. |
| `conflicting_charsets` | Conflicting charset parameters in a claim prevent charset-specific matching; generic media matching remains possible. |
| `unmatched_resource` | None of this resource's claims matches a preference. |
| `source_order_tie` | Multiple resources match the winning preference; source order decides. |
| `no_match` | No resource matches any supplied preference. |

Selection uses declared formats, never URL suffixes, byte sniffing or speculative
requests. Its encoding hints are not decoding authority. A later decoder must
independently validate encoding and container evidence.
