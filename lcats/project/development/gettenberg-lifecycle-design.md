# Local catalog generation lifecycle — WI-GETTENBERG-0004

Decision recorded before implementation, run3 at integration1bc04c29.
Prior-art check is present in WI-0004; reuse ingestion/Catalog and env.cache_root,
without importing legacy cache.py (which creates directories/configures gutenbergpy).

## API and storage

`lifecycle.CatalogManager(cache_dir=None)` resolves LCATS_CACHE_DIR dynamically
at construction (default cache) and owns `<cache_dir>/gettenberg/`. Constructor,
status and open do not create a catalog or perform network access.
`setup(archive=None)` reuses a valid active generation. With none active it
requires an explicit local archive or an explicitly retained source chosen by
rebuild; it never downloads or guesses legacy provenance.
`rebuild(archive=None, allow_count_change=False)` builds from the supplied local
archive or the active generation's retained archive. `activate(generation_id,
allow_count_change=False)` recovers a prepared candidate or retained generation.
`open()` returns a context-managed Catalog pinned to the selected immutable file.
`status()` reports root, active generation, candidates, generations and preserved
legacy paths. `cleanup()` returns exact removed candidate/temp paths, under lock.

Layout: writer.sqlite (persistent coordination inode), active.json, generations/
<uuid32>/{catalog.sqlite,manifest.json}, candidates/<uuid32>/..., archives/
<sha256>.tar.bz2. Names are generated/strictly validated, never derived from tar
members or untrusted manifest paths. Small bounded UTF-8 JSON files hold versioned
manifest and pointer; active pointer includes generation ID and manifest SHA256.
All operations are local. Remote refresh is WI-0005 and deliberately has no
misleading network-capable placeholder here.

## Locking and publication

Use SQLite BEGIN IMMEDIATE on a dedicated persistent coordination file as the
cross-platform writer lock, bounded monotonic timeout. No homegrown stale-PID
unlinking. OS release after process death is tested with real processes. Readers
never acquire this lock. Published generations are retained, so cleanup cannot
invalidate already-open or concurrently-opening readers on POSIX or Windows.
Cleanup conservatively removes candidates and known temporary files only; it
never deletes archives, published generations, writer.sqlite or legacy caches.
Generation/archive retention is intentional and documented as disk growth.

Acquire writer lock for setup/rebuild/activation/cleanup. Copy explicit local
archive with size bounds, hash, source-change checks and fsync into managed
content-addressed storage; preserve source file. Build unique candidate using
WI-0003 limits. Verify complete status, versions, archive hash, actual ebook/
source/member accounting, foreign keys and SQLite integrity. Seal manifest with
source identity, database hash/size, counts, diagnostics and snapshot identity.
Retrieval time/HTTP validators for local or legacy input remain unknown, never
invented. Local capture/build time is labeled separately.

Before activation compare old/new ebook counts; any change requires explicit
allow_count_change=True and raises a structured error with candidate ID and
both counts otherwise. This conservative default makes inspection possible;
activation always returns/persists the comparison, including permitted changes.
Rename prepared candidate to generations, fsync relevant directories where
supported, write+fsync pointer temp in same directory, os.replace active.json,
then fsync directory. Failed/interrupted pre-pointer steps preserve the old
pointer. A post-replace durability error is reported as potentially published
and callers inspect status; never claim rollback after commit point. Tests kill
real writer processes and inject filesystem failures at publication boundaries.

## Bounds and evidence

Archive and build bounds reuse BuildLimits; validation has explicit elapsed
budget and SQLite progress cancellation. No implicit full source rebuild on
status/open/setup reuse. Validate file identity and manifest/schema on open;
full archive/database hashes/integrity are activation gates, not every query.
Trust boundary is cooperative local cache use, not adversarial modification by
another process with the same filesystem permissions. Reject symlinked managed
objects and malformed pointers rather than traversing or deleting them.

Use real archive/SQLite fixtures, multiprocess writer contention/crash release,
two pinned readers across activation, count-change approval, missing/corrupt
source/schema/manifest, setup reuse, LCATS_CACHE_DIR and no-network checks.
Exercise how-to examples. One independent combined review before canonical
validation/internal PR. Additional full cached build only if needed for changed
ingestion semantics; reuse previous qualification plus a measured lifecycle
activation probe of the existing private candidate where feasible.
