# WI-0003 local catalog contract

Decision recorded before implementation, run2 at base71805862. Scope and
acceptance: [WI-0003](../work_items/resolved/WI-GETTENBERG-0003.md).

Use SQLite schema1 with application ID0x4C434754, foreign keys,256-record
batches and explicit complete/building/failed manifest state. Never activate
a generation or replace an existing output. Build an explicitly named new
candidate; failed/incomplete candidates remain inspectable but cannot open
through the public Catalog reader. Retain the supplied archive unchanged. Compress source RDF losslessly per record
with zlib level1; sources store encoding/raw_size and the original SHA-256.
Bounded reader decompression checks original length/hash before parsing.

Normalized tables: ebooks(id,uri,downloads); titles; record-local agents,
agent_literals/agent_links and contributions; languages,subjects,shelves,types;
resources,formats,resource_sizes/resource_modified/resource_links; per-term
scheme tables; ebook_literals/ebook_links/additional_metadata; sources and
diagnostics. Ordinals preserve relationships, source order and multiplicity.
Each term table uses ebook_id,owner,position,value,language,datatype,uri,node_id,
folded; owner is resource ordinal for formats and0 otherwise. Titles use
ebook_id,position,kind,value,language,datatype,folded. Agent literals use
ebook_id,agent_position,kind,position,value,language,datatype,folded.
Contributions use ebook_id,position,role_uri,agent_position. Text indexes use
Unicode casefold stored alongside exact original text. Index ebook joins and
exact-value lookup columns; exact BINARY equality never means substring.

Private `_store` owns schema creation, normalized insertion and schema checks.
Public Catalog opens mode=ro with query_only and requires complete compatible
manifest. `get(id)` returns ParsedRecord orNone; `get_many(ids)` preserves input
order/duplicates with explicit None for missing IDs, at most1000 inputs.
A batch preflights aggregate source sizes (default16MiB, explicit override)
before decoding, counting duplicate requests repeatedly; missing source rows
for existing ebooks are corruption, not ordinary missing-ID results.
Bounded `find_ids(filters,after_id=0,limit=100)` does exact matching; separate
`search_ids` performs literal Unicode-casefolded substring matching. Filter
dimensions: ids,titles,authors,languages,subjects,shelves,types,roles,formats;
AND across nonempty dimensions,OR within each. Authors include names/aliases.
No caller SQL. Keyset pagination orders by ID, at most1000 records per page.
`iter_records` iterates one bounded matching page. Full records reparse retained
RDF under the recorded parser version, ensuring all fields/diagnostics remain
faithful; normalized tables serve filters, not a lossy object reconstruction.
Readers bound source bytes before fetching blobs; current parser version1 only.

`build_catalog(archive,output,limits=BuildLimits(),batch_size=256)` streams
tar.bz2 via bounded decompression and a total decompressed-byte cap, not just
declared member sizes. No extraction. Reject unsafe/nonregular/duplicate
members, unsupported/malformed records and duplicate ebook IDs with accounting.
No speculative deletion/non-book recognition: unsupported records count as
rejected and prevent complete status. Unknown parser diagnostics are retained
and counted explicitly, not silently discarded. An empty catalog is incomplete.

Defaults: compressed256MiB, member2MiB, expanded archive4GiB,200000 members,
database4GiB, max elapsed600s.
Resource targets remain512MiB peak RSS,10-minute full build,4GiB temporary
output. Enforce database pages and check owned SQLite sidecars; limits are
explicit validated overrides. Timings are cooperative checkpoints plus SQLite
progress callbacks, not an OS sandbox guarantee. Truncated compressed input
must fail; partial writes stay failed/building, never complete.

Full qualification reuses the recorded cached archive, creates only a private
/tmp candidate, measures all records, query/read fidelity, time/RSS/disk and
integrity. No network, refresh, caller/CI migration or canonical corpus writes.
