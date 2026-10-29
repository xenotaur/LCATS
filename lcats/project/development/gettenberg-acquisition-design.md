# Gettenberg acquisition contract and implementation handoff

Status: coordinator-authored design checkpoint, not implemented or independently
reviewed. Prepared under the 15-minute planning grant `gettenberg-20261015-plan`.
Governing scope: [WI-0005](../work_items/resolved/WI-GETTENBERG-0005.md),
[redesign](../design/proposals/adopted/lcats-gettenberg-redesign/00_proposal.md)
Decisions 6–8, and the [charter](gettenberg-pilot-charter.md).
Base: `2f14e4e886c1f3fd6a6f021e3f72db6621cbb3a2` on main. WI-0002 and the
WI-0004 lifecycle are resolved there. The next run must verify its actual base.

## Existing boundaries and implications

Citations below refer to that base; paths resolve from this document.

| Existing evidence | Consequence for WI-0005 |
|---|---|
| [models.py:62](../../src/lcats/gettenberg/models.py#L62): Resource retains URI, multiple format/size claims | Keep metadata lossless; selecting a preferred resource must not discard other downloadable formats. |
| [cache.py:147](../../src/lcats/gettenberg/cache.py#L147): legacy downloader tries URL patterns after HTTP errors and reads the response whole | Do not reuse its retry/fallback behavior; leave callers unchanged until WI-0008. |
| [downloaders.py:18](../../src/lcats/gatherers/downloaders.py#L18), :85: gatherers decode and cache text | Those files are derived legacy representations, not recoverable originals. |
| [lifecycle.py:487](../../src/lcats/gettenberg/lifecycle.py#L487): setup is offline and reuses an active generation | Download first through an explicit acquisition operation; retain offline setup/rebuild semantics. |
| [lifecycle.py:402](../../src/lcats/gettenberg/lifecycle.py#L402): local source metadata has unknown retrieval fields | Add verified receipt linkage for acquired archives without inventing provenance for local/legacy input. |
| [_lifecycle_io.py:87](../../src/lcats/gettenberg/_lifecycle_io.py#L87), :204, :274: writer locks, atomic JSON and immutable archive retention | Reuse tested publication principles; do not couple network waits to the catalog writer lock or introduce a second catalog publisher. |
| [pyproject.toml:20](../../pyproject.toml#L20): no directly declared requests/httpx dependency | Prefer the standard library transport for this tranche; do not rely on transitive HTTP dependencies. |

## Decisions for implementation

### 1. Public operations and authority

Names below are the intended API surface, not claims that these symbols exist.
Keep the public resource facade in `gettenberg/resources.py`; private transport,
cache and decoding modules may separate responsibilities without a generic plugin
framework. Use typed immutable request/result/policy records and structured errors
under `GettenbergError`, rather than catalog-specific exceptions for HTTP failures.

| Operation | Contract |
|---|---|
| `select_resource(ebook, preferences=...)` | Pure deterministic choice, returning selected Resource and selection diagnostics. Default preference: UTF-8 plain text, other declared plain text, then HTML; stable source-order tie-break. No requests or guessed URL cascade. Explicit resource selection remains available for every format. |
| `ResourceStore(cache_dir=None)` | Resolve LCATS_CACHE_DIR at construction; no directory creation or network access. |
| `store.plan(request, policy=..., refresh=False)` | Read-only plan: cache identity/state, intended route, estimated bytes when known, action/reason. No directories, locks, requests, sleeps, prompts or decoding writes. A plan never grants authority to execute later. |
| `store.fetch(request, policy=...)` | Verify and reuse a cached original; otherwise acquire only if policy explicitly allows it. No freshness request on a valid hit. |
| `store.refresh(request, policy=...)` | Explicit conditional GET when validators exist; preserve the old entry on failure. No automatic age-based refresh. |
| `decode_text(source, options=...)` | Offline bounded transformation returning text/HTML markup plus source hash, chosen encoding, decoder version and diagnostics. No Gutenberg boilerplate removal. |

`SourceRequest` records source URI, resolved request URL, kind (`archive` or
`resource`) and route-policy identity. `NetworkPolicy` defaults to offline;
online permission is explicit. Dry-run uses `plan` and cannot fall through to
`fetch`. The future WI-0007 command layer owns approval and prompting. Fixed
URLs need no catalog; the transport never initializes one. No per-story prompts.

### 2. Transport and routes

Use a private `urllib.request` opener with certificate verification, explicit
proxy configuration, a descriptive LCATS user agent and `Accept-Encoding: identity`.
Disable automatic redirects and handle each hop in the policy loop. Only HTTP(S)
GET is supported; reject URL credentials, malformed ports/control characters and
non-HTTP schemes before network access. HTTPS is the default; explicit configured
HTTP mirror origins may be permitted, but HTTPS-to-HTTP redirects are refused.
No global opener mutation, cookies, authentication or environment-proxy surprises.

Validate the initial URL and every redirect against the configured route/origin
policy. Bound redirects to five hops across the whole operation (not per retry), detect
loops, retain the complete route,
and charge every hop against pacing and the operation deadline. Cross-origin
redirects require an explicitly permitted destination. Resolve relative Location
values normally; never forward validators from one origin to another blindly.

A catalog URI is evidence of identity, not blanket authorization to robot the
human-facing website. Use documented machine-access endpoints or a configured
mirror and a versioned, fixture-tested route mapping. Preserve the original URI
alongside the actual request URL. Do not scrape landing pages or guess a sequence
of replacement patterns after denial. The official robot, mirror and catalog
pages below ground this boundary; the two-second interval is the WI's conservative
local default, not a claim of universal upstream permission.

**Routing checkpoint:** see [the qualification table](gettenberg-route-qualification.md)
for documented endpoints, pinned resolver evidence and qualified offline mappings.
The 2026-10-15 implementation section supersedes the initial unresolved aliases.
Automatic routing requires explicit main/generated roots; operational default-mirror
qualification remains open. The table does not establish live availability.

**Implementation preflight still required:** choose the concrete supported default
endpoint/mirror mapping from the official listings and check representative main,
generated and catalog paths against saved metadata and documentation. Especially
cover `/ebooks/...` resource aliases and the documented `cache/generated` versus
`cache/epub` difference. Do not silently assert that changing a hostname preserves
paths. This is an engineering qualification task before live use, not permission
to probe many hosts or a blocker to fixture-based implementation.

### 3. Bounds, retries and coordination

Defaults from WI-0005: one active request, at least two seconds between Gutenberg
request starts, 30-second blocking-I/O timeout, two retries after the initial
attempt, 256 MiB archive body and 32 MiB resource body. Caller overrides must be
finite and typed: positive sizes/timeouts, nonnegative integer retry/redirect
counts, and the existing zero-wait lock option. Reject booleans and invalid
limits. Keep the Gutenberg pacing floor at two seconds. Count streamed
bytes, not just Content-Length; reject an advertised oversize early and detect
truncated bodies. Read bounded chunks; never call an unbounded response read.

Add an explicit monotonic operation budget (proposed defaults: 180 seconds for a
resource, 900 for an archive) covering lock waits, pacing, redirects and retries.
Each blocking timeout is at most the remaining budget; do not start another
request or sleep if it cannot fit. These are cooperative deadlines: Python's
socket/urllib timeout is not a proof of hard DNS/OS cancellation. Document this
limit and test stalled reads; if hard cancellation becomes a requirement, replan
transport isolation explicitly instead of claiming threads can cancel sockets.
No live bulk request is needed to qualify this WI in a bounded agent run.

Retry only transient connection/read failures and 408/429/500/502/503/504, within
both retry and elapsed budgets. Honor Retry-After in seconds or HTTP-date form,
including redirects. Use the longer of pacing, bounded backoff and valid server
delay; if it exceeds remaining allowance, return a deferred/rate-limit result
with the next eligible time, without sleeping beyond the budget. Malformed or
absent values use documented conservative backoff (2 then 4 seconds). Permanent
401/403, 404/410, TLS validation errors, policy denials, malformed redirects and
integrity errors are terminal; no automatic alternate-resource/mirror attempts.
No partial-download resume in v1: failed partial bodies are never cache hits.

Use one persistent resource-network SQLite lock per resolved cache root. Recheck
the requested cache entry after taking it: two processes requesting the same
missing resource must cause one download. Hold serialization across body streaming;
retain persisted per-origin next-eligible times, including Retry-After, so a new
process cannot immediately bypass cooldown. Cache hits and read-only plans do not
acquire a writable lock. Coordination covers cooperating users of the same cache
root, not unrelated roots, machines or external downloaders. Fixed lock order:
resource network lock only during acquisition; release it before catalog writer
lock acquisition. The implementation review qualified one shared archive-publication
leaf lock: resource-network or catalog-writer may acquire it, never the reverse.
It covers archive publication/verification through temporary hard-link cleanup,
preventing link-count changes from racing with the other publisher's hash checks. A killed downloader releases its SQLite lock; persistent lock
files are never unlinked as cleanup. Clock changes must not cause negative waits
or unbounded sleeps; reject implausible/corrupt pacing metadata explicitly.

### 4. Original bytes, identity and publication

A cache key is SHA256 over a versioned canonical request identity: GET, normalized
request URL (scheme/host case and default port normalized, fragment omitted;
path escaping and query ordering preserved) and representation headers. Record
the caller's source URI separately. Different query strings and representation
policies must not collide. Do not use ebook ID or media type alone as a key.

Store immutable bodies by SHA256, immutable retrieval receipts by receipt hash,
and a small per-request reference to the latest complete receipt. Proposed root:
`<LCATS_CACHE_DIR>/gettenberg/resources/{objects,receipts,refs,tmp}` plus a
persistent network lock/state database. Use separate typed storage rules for
archives, sharing `<cache>/gettenberg/archives/<sha256>.tar.bz2` with lifecycle
retention. Do not introduce a second owner that can delete retained archives.
Safe reuse may remove an unnecessary local copy after identity verification;
zero extra disk copies are an optimization, not an unverified acceptance claim.

The original is the HTTP body after transfer framing, **before Content-Encoding,
container or text decoding**. Record Content-Encoding even when identity was
requested. Never overwrite raw bytes with decoded output. Metadata includes
schema version, original/request/final URLs, redirect chain, hash/length,
retrieval UTC time, status, bounded selected headers (Content-Type,
Content-Encoding, ETag, Last-Modified), and route/transport version. Bound metadata
size and reject unsafe stored paths; no credentials, arbitrary headers or secrets.

Publication order: exclusive temporary file, stream/hash/size checks, fsync,
no-clobber body publication, durable immutable receipt, atomic request-reference
replacement, directory sync. A failed reference update leaves the prior complete
entry usable; a post-replacement durability error reports that publication may
have occurred. A complete hash-verified receipt/body pair is necessary for reuse.
Corrupt existing state fails explicitly; an ordinary fetch does not silently
redownload over it. A successful explicit refresh of valid state publishes a new receipt without
deleting historical bodies. Corrupt-state repair is a separately specified
recovery operation; do not silently overwrite a corrupt content-addressed object
while claiming no-clobber publication. Keep orphan cleanup conservative.

On 304, require a valid matching cached representation, preserve its body/hash
and original retrieval time, and record a new validation event/time and returned
validators. Do not accept 304 on a cold miss or send validators for unverifiable
bytes. A normal fetch never performs this request. Retain old receipts/bodies
through changed-content refresh, interruption and reader overlap.

### 5. Catalog handoff and provenance

Acquisition returns a `SourceArtifact` containing immutable body path, hash,
length and a validated receipt. Catalog construction consumes that same local
archive offline. Add an optional typed acquisition-provenance argument to local
setup/rebuild (or an equally narrow offline adapter), checking receipt hash/size
against the actual retained archive before preparing a generation. Local-only
calls keep their existing unknown retrieval fields. Acquired inputs embed the
receipt identity and bounded source metadata in the generation manifest so
provenance survives resource-reference refresh. No network inside CatalogManager.

Download success is not activation approval. Refresh compares new archive identity;
unchanged bytes need no rebuild. Changed bytes pass through existing candidate
verification, count-change approval and activation. Acquisition, decode or build
failure must leave the active catalog and previous originals intact. Cover this
composition in tests even though user-facing command orchestration belongs to
WI-0007. Only recognized archive-kind requests publish into the catalog archive namespace;
acquisition does not certify valid RDF contents. Catalog validation remains required.

### 6. Decoding and format support

All catalog-described formats remain retrievable as bytes; retrieval support does
not promise an extractor. Initial text/HTML decoding is strict and offline.
Choose encoding deterministically: explicit override, BOM, HTTP declaration,
catalog declaration, HTML encoding declaration, then UTF-8. Record conflicting
claims and the chosen source; absent an explicit override or BOM, conflicting
declarations produce an ambiguity error. Unknown codecs/invalid bytes produce structured
errors instead of silent replacement or guessed Latin-1. Never fetch linked HTML
assets. Return decoded HTML markup for the existing extraction layer; cleanup
and segmentation are separate work items.

Handle identity/gzip Content-Encoding and gzip or single-unambiguous-text-member
ZIP containers with explicit bounded inflation (proposed 64 MiB decoded bytes,
1,000 ZIP entries). Read selected members without filesystem extraction; reject
unsafe/encrypted/ambiguous containers, and require explicit member choice when
needed. EPUB/PDF/audio remain byte-retrieval only. Unknown encoding/container
chains remain cached originals with an actionable decoding error. Decoder identity
includes version, source hash, encoding override and container/member policy.
An immutable in-memory DecodedText result suffices initially; any persisted derived
cache must use that separate identity and cannot replace the original.

## Acceptance matrix

Use authored tiny HTTP responses and real temporary files/SQLite. Substitute at
the transport/clock boundary where necessary; use local loopback HTTP integration
for actual streaming/redirect behavior. No Gutenberg requests in unit tests.

| ID | Scenario | Required observable result |
|---|---|---|
| A01 | Import, construction and dry-run with missing cache | No created files, network, lock writes, sleep or prompt; plan says missing. |
| A02 | Offline hit / offline miss / denied origin | Verified bytes returned on hit; typed miss/denial before transport on others. |
| A03 | Valid cached fetch with online permission | Zero refresh/HEAD requests, unchanged receipt and bytes. |
| A04 | Successful stream, including binary/non-text format | Exact received body hash/length, bounded memory, provenance and reusable receipt. |
| A05 | Missing/false Content-Length, oversized/truncated stream | Bounded failure; previous reference intact; no partial hit. |
| A06 | Two processes fetch one missing URL | One network acquisition; second rechecks and reuses; killed writer releases lock. |
| A07 | Distinct URLs, redirects and restarted process | One active request; start spacing/cooldown survives restart within same cache root. |
| A08 | Retry-After seconds/date, malformed value, wait beyond budget | Correct bounded scheduling/deferred error; no shortened valid server delay. |
| A09 | Transient retry versus 403/404/TLS/policy denial | Exact attempt budget; no speculative alternate URL or format after terminal error. |
| A10 | Relative/cross-origin/downgrade/loop/too-many redirects | Every target checked; validators scoped; bounded chain and complete provenance. |
| A11 | Query/escaping/representation variations | No key collisions or silent URL rewriting; stable documented normalization. |
| A12 | Failure at each body/receipt/reference publication boundary | Prior complete entry usable; orphan is not success; post-commit state reported. |
| A13 | Corrupt/symlinked metadata or body, unsupported schema | Explicit integrity/path/schema error, no implicit repair download. |
| A14 | Conditional 304 / changed 200 / cold or corrupt 304 | Correct validator binding; original retrieval time preserved; old bytes retained. |
| A15 | Acquired archive into offline setup/rebuild | Manifest receipt matches retained hash; legacy/local unknown provenance stays unknown. |
| A16 | Download/build/count-change failure during catalog refresh | Prior active generation and pinned reader remain usable; approval still required. |
| A17 | Multiple equal media types, preferences, unsupported extractor | Stable pure selection; every Resource remains explicitly retrievable. |
| A18 | Charset conflicts/BOM/invalid bytes/explicit override | Deterministic strict result/error with source hash, version and diagnostics. |
| A19 | Gzip/ZIP limits, multiple members, unsupported format, HTML assets | Bounded offline decoding; raw originals intact; no extraction writes or asset requests. |
| A20 | Missing cached metadata versus fixed URL | No full catalog initialization by ResourceStore. |
| A21 | Socket stall, exhausted deadline, cancellation | Bounded I/O behavior and no further attempts; accurately document DNS/OS limitation. |
| A22 | Concrete mirror route fixtures | Main/generated/catalog paths and original URI mapping verified before any live use. |

## Next implementation run

Start only after a renewed human grant. Fetch main; preserve this planning commit
and reconcile any newer code. Use absolute PYTHONPATH: the project environment's
editable install currently points to a different LCATS checkout. Verify imports.
Record native WI readiness separately from dependency acceptance; both WI-0002
and lifecycle WI-0004 are resolved on this base. Do not resolve WI-0005 now.

Implement in this order: (1) request/policy/error contract and read-only planning;
(2) streaming transport, cache publication and request coordination; (3) offline
decoding and catalog receipt composition; (4) docs, independent review and stable
source qualification. Before implementation, qualify the default route mapping
and confirm the cooperative timeout contract in the code-level plan. If these
require a material behavior change, return that decision to the human.

Normally the coordinator authors the tightly coupled transport/cache work; reserve
one independent review assignment. Delegate only a clearly separated test/decoding
slice after interfaces settle. Do not consume all slots on parallel implementations.
At minute 45 of a future 90-minute run, assess whether complete WI acceptance fits;
if not, preserve a coherent unaccepted tranche rather than omit tests or pretend
that acquisition alone completes decoding/provenance requirements. No automatic
WI-0006 start, main promotion, new paid model calls, bulk fetch or CI redesign.

Expected product docs: `docs/reference/gettenberg-network.md`, a how-to for
cached/offline acquisition and explicit refresh, and relevant lifecycle provenance
updates. Product docs describe implemented behavior only. Use canonical package
checks and focused fixture tests; no full catalog import is needed for network
policy correctness. Record acceptance evidence by A-ID, current head and reviewer.

## Sources checked 2026-10-15 UTC

- [Python 3.10 urllib.request](https://docs.python.org/3.10/library/urllib.request.html):
  opener handlers, default redirects/proxies and blocking-operation timeout.
- [HTTP Semantics, RFC 9110 section 10.2.3](https://www.rfc-editor.org/rfc/rfc9110.html#section-10.2.3):
  Retry-After delay/date forms and applicability to redirects and 503 responses.
- [Project Gutenberg robot access](https://www.gutenberg.org/policy/robot_access.html):
  machine-access exceptions and example pacing; do not infer blanket crawl permission.
- [Offline catalogs](https://www.gutenberg.org/ebooks/offline_catalogs.html):
  machine-readable metadata and published mirror discovery.
- [Mirroring how-to](https://www.gutenberg.org/help/mirroring.html):
  distinct main/generated layouts and generated-path aliasing.

These sources informed choices; this sprint did not fetch ebook/catalog data,
validate a live mirror's availability, run a transport benchmark or implement code.
