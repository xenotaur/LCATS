# Gettenberg route qualification checkpoint

Status: documentation qualification, not implemented, independently reviewed or
live-download validated. Run `gettenberg-20261015-routes`, 2026-10-15 UTC.
Companion to [the acquisition contract](gettenberg-acquisition-design.md), A22.
Source base: a528ebfdb6c4ecb1b1b05bb4bd5a7b5a0f7b3f0d; fetched main remains
2f14e4e886c1f3fd6a6f021e3f72db6621cbb3a2.

## Evidence and proposed endpoint roles

The official [mirror list](https://www.gutenberg.org/dirs/MIRRORS.ALL) lists
`https://gutenberg.pglaf.org/` as a Gutenberg mirror including generated content.
It is the proposed combined-mirror candidate, not a proven operational default.
A single web-tool read of its root index timed out; this proves neither outage
nor accessibility. No mirror failover or file download was attempted.

The [offline catalogs page](https://www.gutenberg.org/ebooks/offline_catalogs.html)
links the [feed index](https://www.gutenberg.org/cache/epub/feeds/), which lists
`rdf-files.tar.bz2`. Use its exact published archive URL as the catalog default;
do not derive it from an ebook URL or require the mirror to carry it.
The directory listing is evidence of publication, not a measured download size,
archive integrity check or a promise that the existing byte limit will always fit.

The [mirroring documentation](https://www.gutenberg.org/help/mirroring.html)
distinguishes digit-sharded main paths from generated paths and describes the
`cache/generated` to `cache/epub` alias. It does not specify every `/ebooks/`
format alias. Separate origin and layout configuration; a host swap alone is
insufficient. The [robot policy](https://www.gutenberg.org/policy/robot_access.html)
points automated users to harvesting, mirrors and catalog downloads. Pacing does
not authorize arbitrary human-site crawling.

## Input/output table for A22

`G` below means `https://www.gutenberg.org`; `M` means the proposed combined
mirror `https://gutenberg.pglaf.org`. These are documentation-derived cases for
future tests, not passing test results. Preserve the complete original source URI
and the selected route-policy version in every request/receipt.

| Case | Input | Intended output or disposition | Evidence and qualification level |
|---|---|---|---|
| R01 | Catalog setup, no existing archive | `G/cache/epub/feeds/rdf-files.tar.bz2` | Exact file linked by the official feed index; documented endpoint, bytes not fetched. |
| R02 | `G/files/84/84-0.txt` | Candidate `M/8/84/84-0.txt` | [pg84.rdf:259](../../tests/gettenberg_tests/fixtures/pg84.rdf#L259) supplies filename; digit sharding follows the mirroring layout. The `/files/` alias conversion remains an inference requiring authoritative resolver evidence before shipping. |
| R03 | `G/files/10001/10001-h/10001-h.htm` | Candidate `M/1/0/0/0/10001/10001-h/10001-h.htm` | [pg10001.rdf:96](../../tests/gettenberg_tests/fixtures/pg10001.rdf#L96); same inference as R02, preserving the entire nested suffix. |
| R04 | `G/cache/epub/84/pg84.cover.medium.jpg` | `M/cache/epub/84/pg84.cover.medium.jpg` | [pg84.rdf:285](../../tests/gettenberg_tests/fixtures/pg84.rdf#L285), combined-mirror layout; structurally documented, mirror availability untested. |
| R05 | `G/cache/epub/84/pg84-h.zip` | `M/cache/epub/84/pg84-h.zip` | [pg84.rdf:311](../../tests/gettenberg_tests/fixtures/pg84.rdf#L311); preserve ZIP filename, do not substitute uncompressed HTML. Same operational qualification as R04. |
| R06 | `G/cache/generated/1001/1001.epub` | `M/cache/epub/1001/1001.epub` | Synthetic case from the official mirroring example; explicit path-alias rule, not a captured local RDF case. |
| R07 | `G/ebooks/84.txt.utf-8` or `G/ebooks/84.html.images` | Unresolved; no guessed request URL | [pg84.rdf:246](../../tests/gettenberg_tests/fixtures/pg84.rdf#L246), [pg84.rdf:142](../../tests/gettenberg_tests/fixtures/pg84.rdf#L142). A separately cataloged plain/HTML resource is another selection, not proof of alias identity or byte equivalence. |
| R08 | `G/ebooks/84.epub3.images`, other EPUB/Kindle aliases, or `G/ebooks/84.rdf` | Unresolved; no extension substitution | [pg84.rdf:168](../../tests/gettenberg_tests/fixtures/pg84.rdf#L168), [pg84.rdf:272](../../tests/gettenberg_tests/fixtures/pg84.rdf#L272). Format labels alone do not establish generated filenames. |
| R09 | Unknown origin/layout, legacy `etext*` path, single-digit ID, query-bearing alias | Explicit unsupported automatic mapping until separately specified | Negative fixture cases. Do not generalize R02 to historical layouts or invent padding. An explicitly supplied permitted URL remains available to the generic byte transport. |

## Fixture coverage and selection consequence

Read-only stdlib XML enumeration of all seven `tests/gettenberg_tests/fixtures/*.rdf`
files found 113 `pgterms:file` nodes: 65 `/ebooks`, 27 `/files`, 21 `/cache`.
This counts resource nodes, not unique URLs or the full catalog. Inputs and hashes
are recorded in [the evidence inventory](evidence/gettenberg-route-qualification-20261015/inventory.json).

Alias resolution therefore cannot be treated as a rare edge case or silently
removed from the all-formats requirement. Keep metadata unchanged. Before network
access, selection/planning must surface unroutable candidates and make an explicit,
deterministic choice among qualified alternatives, preserving diagnostics. Never
send a failed request merely to discover the next pattern. Do not assume a direct
resource with the same MIME type is byte-identical to an alias.

This raises an implementation detail to settle before coding: either make route
capability an explicit input to pure resource selection or expose ordered
candidates for a pure planning step. Do not let the current source-order tie-break
select an unsupported alias and hide an otherwise usable direct resource. Both
forms preserve offline planning and the existing preference order.

## Remaining qualification and acceptance

A22 is narrowed, not complete. Before shipping automatic mapping:

1. Obtain authoritative upstream resolver rules for `/files/` and `/ebooks/`
   aliases, including small IDs, historic layouts and current generated names.
   Prefer pinned upstream source with saved fixtures; do not copy another client's
   guessed suffix cascade. The old upstream mailing-list search result described
   `/files/12345` to digit-sharded `/dirs/` redirects, but its page could not be
   opened in this sprint, so it is not treated as conclusive evidence.
2. Turn R01–R09 into offline tests of route policy, suffix preservation, origin
   validation and unsupported cases. Reject traversal, encoded separators and
   credentials rather than allowing a mapped path to escape its configured root.
   Keep archive and generated-mirror roots independently configurable.
3. Qualify any actual default mirror with a separately bounded operational check
   before live use, recording redirects and final origin. Do not silently switch
   mirrors after denial or assert that a listing guarantees every resource exists.
4. Satisfy full format coverage through qualified aliases or explicit permitted
   URLs. Report unsupported automatic routes accurately until then; do not mark
   WI-0005 complete on the strength of the concrete-path subset.

No product code, source fixtures, data cache, catalog or experimental measurement
was changed. No ebook or archive body was fetched. Product tests and independent
implementation review remain obligations of the implementation run.
