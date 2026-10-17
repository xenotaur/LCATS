# Default-source endpoint qualification — 2026-10-17

## Decision

Recommend a static, overridable CLI default profile for the next WI-GETTENBERG-0007
implementation tranche:

| Role | Candidate |
|---|---|
| RDF archive | `https://www.gutenberg.org/cache/epub/feeds/rdf-files.tar.bz2` |
| Main files root | `https://gutenberg.pglaf.org/` |
| Generated files root | `https://gutenberg.pglaf.org/cache/epub/` |

Representative endpoint checks passed from this host. This is sufficient evidence
to recommend the profile for implementation, not a claim of full acquisition,
archive integrity, corpus equivalence, sustained availability or freshness. Product
code remains explicit-source-only until the defaults are implemented and reviewed.

This closes the bounded endpoint investigation left by the
[earlier routing qualification](gettenberg-route-qualification.md); it does not
replace that document's pinned upstream mapping evidence or offline route tests.
Base: `c167d74cfef5ae2d51b6c28b4c24e0d5ddc44833`. Full request arguments, response
headers, timestamps, relevant transfer metrics and prefix hashes are in
[evidence](evidence/gettenberg-default-source-20261017/probe.json). Original GET
response bytes are retained in
[response-bodies.json](evidence/gettenberg-default-source-20261017/response-bodies.json),
keyed by probe name. Base64 preserves original CRLF and truncated final lines;
decode each `data` value before checking its byte count and SHA-256. No refetch
is needed to audit these dated samples.

## Authority and observations

The [robot policy](https://www.gutenberg.org/policy/robot_access.html) directs
machine access to harvesting, mirrors and catalogs. The official
[mirror list](https://www.gutenberg.org/dirs/MIRRORS.ALL) lists the HTTPS PGLAF
combined mirror. The [mirroring guide](https://www.gutenberg.org/help/mirroring.html)
distinguishes main digit-sharded paths and generated per-ebook paths. The
[offline catalog guide](https://www.gutenberg.org/ebooks/offline_catalogs.html)
links the [feed directory](https://www.gutenberg.org/cache/epub/feeds/), including
the exact archive endpoint. These public documents were re-read on 2026-10-17.
No policy inference comes from the mirror's robots.txt returning 404; that response
means no robots file was obtained, not permission or an access denial.

Six sequential requests were made once each, with TLS verification, a 20-second
request maximum, 8-second connect timeout, no retries/redirect following and at
least 2 seconds between calls. GET used Range 0–4095 and a 4096-byte maximum. An
unexpected transfer failure or access denial would stop probes without trying
another mirror; the missing robots file is interpreted separately above.

| Probe | Observed outcome |
|---|---|
| Archive HEAD | 200; 126,790,723 bytes advertised, below 256 MiB policy ceiling; zero body bytes |
| PGLAF robots.txt | 404; 162-byte error body |
| Main `/8/84/84-0.txt` HEAD | 200; 421,633 bytes; text/plain; ETag present |
| Generated `/cache/epub/84/pg84.txt` HEAD | 200; 448,885 bytes; text/plain; ETag present |
| Main Range GET | 206; exactly 4096 bytes; Content-Range 0–4095/421633 |
| Generated Range GET | 206; exactly 4096 bytes; Content-Range 0–4095/448885 |

All six responses stayed on their requested HTTPS URL; no redirects observed.
Actual router calls mapped source `/files/84/84-0.txt` and `/ebooks/84.txt.utf-8`
to the tested destinations. Total response bodies: 8354 bytes; no archive body.
Main/generated sizes and prefix hashes differ: preserve their source identities;
never treat them as equivalent copies or substitute one after a failed request.
The live archive HEAD was newer than the web-tool feed-index timestamp, so use
it for this observation's size/time evidence. Neither observation validates bytes.

## Next implementation slice

1. Resolve the profile only at the CLI/workflow boundary when a selected
   collection needs metadata. Keep `GutenbergRoutes` explicit and library network
   policy offline by default; do not add a global client or mirror discovery call.
2. Missing metadata setup with no explicit archive/source uses the published
   archive URL. Existing setup approval remains mandatory, including unattended
   `--yes`; ready catalogs are reused without acquiring or refreshing anything.
3. Neither root supplied selects the default pair. Both supplied overrides the
   pair; exactly one supplied remains a configuration error. Explicit local
   archive/URL takes precedence over the default archive. Keep archive and
   resource roots independently configurable.
4. Permit only origins selected by that resolved configuration. Preserve explicit
   additional redirect origins, offline dominance, bounded pacing/retries and
   terminal denial behavior. No mirror failover or fallback to human ebook pages.
5. Curated-only selection must not resolve/inspect/setup a catalog. Dry-run must
   report selected endpoints and authority without requests, prompts or writes.
   Make standalone `catalog setup` and smart gathering agree on default setup;
   leave explicit refresh/rebuild authority unchanged.
6. Add offline fixture tests for no-argument first use, ready reuse, override
   precedence, incomplete root pairs, missing approval, denied origins, offline
   misses and mixed collection selection. Retain current body/bucket/override
   tests and fresh-process legacy-import prohibition. Update CLI help and guides.

A successful default-profile implementation needs cold review, canonical tests
and exact-head CI. A separately bounded live ResourceStore check would validate
that client's TLS/HTTP path; these curl probes do not. A full catalog fetch/build
is a separate explicit acquisition budget, not implied by this sprint. Do not
raise byte limits solely because a future Content-Length exceeds today's value.

## Boundaries

Only two plain-text resources for one ebook were sampled. No full text, ZIP,
HTML, EPUB, whole-catalog or throughput test was performed. This is a dated
observation, not a scheduled monitor. Do not add live probes to unit tests or CI.
No product code, defaults, canonical corpus or package dependency changed. Native
WI/execution status remains nonterminal, and main promotion remains human-gated.
