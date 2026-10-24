# Prepare and recover a local Gutenberg catalog

Use this workflow when you already have a Gutenberg RDF `tar.bz2` archive and
want an LCATS-owned catalog. These library operations are entirely offline.
For CLI setup, refresh and gathering, see [catalog preparation](gettenberg-preparation.md)
and [gathering](gettenberg-gather.md); both use these same lifecycle APIs.

## Prepare once and reuse

Choose a cache directory and an existing archive. `cache_dir` below is the
LCATS cache root, not the generation directory. Omitting it honors
`LCATS_CACHE_DIR`, defaulting to `cache` in the current working directory.
The examples assume `cache_dir` and `archive_path` are `pathlib.Path` values.

```pycon
>>> from lcats.gettenberg import lifecycle
>>> manager = lifecycle.CatalogManager(cache_dir)
>>> generation = manager.setup(archive_path)
>>> generation.reused
False
>>> manager.setup().reused
True
>>> with manager.open() as reader:
...     identifiers = reader.find_ids(limit=10)
>>> bool(identifiers)
True
>>> manager.status()['state']
'ready'

```

Setup copies the local source into managed content-addressed storage, builds
and verifies a candidate, and activates it only after all checks pass. It
preserves the original archive. When a valid generation is already active,
setup reuses it even if an archive argument is supplied; use `rebuild` or
`update` to change its contents. There are no age-based refresh checks or network fallbacks.

## Rebuild from the retained source

```pycon
>>> rebuilt = manager.rebuild()
>>> rebuilt.generation_id != generation.generation_id
True
>>> rebuilt.manifest['snapshot_id'] == generation.manifest['snapshot_id']
True

```

Omitting the archive uses the active generation's retained source. To use a
new local archive, pass its path explicitly. For a downloaded archive, pass the
whole `SourceArtifact` to retain its receipt, as described below. An implicit
rebuild preserves the active generation's source provenance.

By default, a changed ebook count raises `CatalogCountChangeError` and leaves
the previous catalog active. The exception exposes `generation_id`, `previous`
and `candidate`. Inspect the named candidate and source before accepting it:

```python
from lcats.gettenberg import errors

candidate_id = None
try:
    updated = manager.rebuild(new_archive_path)
except errors.CatalogCountChangeError as change:
    # Inspect the candidate and the reported old/new counts first.
    candidate_id = change.generation_id
    old_count, new_count = change.previous, change.candidate

# After deciding that the change is expected:
if candidate_id is not None:
    updated = manager.activate(candidate_id, allow_count_change=True)
```

`allow_count_change=True` explicitly accepts the comparison against whichever
valid generation is active when the writer lock is acquired. It is not an
approval tied to a previously observed active generation. The activation record
reports both counts and the previous generation ID. Callers needing a narrower
approval can re-inspect while arranging exclusive access to their cache.

## Apply a downloaded or refreshed archive

Use the separate [acquisition API](gettenberg-resources.md) with an archive-kind
request and explicit network policy. The following network example is separate
from catalog construction; it is not needed for local-only workflows:

```python
from lcats.gettenberg import resources

store = resources.ResourceStore(cache_dir)
request = resources.SourceRequest.from_url(archive_url, kind="archive")
# policy explicitly authorizes the chosen source origin and resource bounds.
artifact = store.fetch(request, policy=policy)
generation = manager.setup(artifact)

# Later, when the caller explicitly requests a freshness check:
artifact = store.refresh(request, policy=policy)
updated = manager.update(artifact)
```

`manager.update` is entirely offline. It verifies the receipt and actual archive,
reuses an unchanged active generation, or builds a candidate from changed bytes.
A changed ebook count still requires the approval workflow above; use
`manager.activate(change.generation_id, allow_count_change=True)` after inspecting
the candidate. Acquiring bytes never implicitly approves a count change.

Given an already acquired archive-kind `artifact`, this offline example checks
the provenance of a new build and demonstrates unchanged-byte reuse:

```pycon
>>> acquired = lifecycle.CatalogManager(cache_dir / "acquired")
>>> built = acquired.setup(artifact)
>>> built.manifest['source']['receipt_sha256'] == artifact.receipt_sha256
True
>>> acquired.update(artifact).reused
True
>>> acquired.rebuild().manifest['source'] == built.manifest['source']
True

```

A reused generation keeps the receipt used to build it. A newer304 receipt lives
in the resource cache and does not rewrite generation history. Passing only
`artifact.path` records local input with unknown retrieval provenance. Retained
catalog provenance survives later changes or loss of resource-cache references.

## Recover after interruption

Inspect `manager.status()`: it lists candidates, retained generations, the active
reference, and any invalid metadata. A failed build or interruption before pointer
replacement leaves the previous active generation available. An interrupted
first setup leaves no active generation; supply the archive again or activate a
fully prepared candidate.

A candidate with a complete valid `manifest.json` can be recovered with
`manager.activate(candidate_id)`. A generation moved into `generations/` before
pointer publication is also recoverable by ID. Activation repeats archive/database
hashes, SQLite integrity, relationships, counts and version checks. A partial or
incompatible candidate is rejected; it cannot become active merely by existing.
Use `manager.activate(old_generation_id)` to switch back to a retained generation;
count-change approval may be needed.

If pointer replacement succeeded but its directory sync failed,
`CatalogPublicationError.published` is true. Inspect status: the new generation
may already be active. Do not infer rollback from an exception after this commit
point. A malformed active pointer or modified active manifest fails closed;
these APIs do not guess which catalog should replace corrupted metadata.

## Clean abandoned work conservatively

```pycon
>>> removed = manager.cleanup()
>>> isinstance(removed, tuple)
True

```

Cleanup returns exact removed paths. It removes candidate directories and known
publication temporary files while holding the writer lock. This includes prepared
candidates waiting for count-change approval: activate any candidate you want to
retain before cleanup. Unknown entries and symlinks are preserved.

Published generations and retained archives are **never** deleted by this cleanup.
That conservative policy keeps both open and concurrently opening readers safe,
and preserves source evidence. Disk use therefore grows with generations/sources;
broad retention/deletion policy is outside this API. Preserve the archive and
manifest elsewhere if long-term reproducibility must outlive this cache.

Legacy `gutenbergindex.db`, `rdf-files.tar.bz2`, `texts/` and `tmp/` at the LCATS
cache root are reported as unverified legacy artifacts and left unchanged by
CatalogManager. The separate destructive `lcats clean --cache-only` command removes
all known caches, including those legacy artifacts and published generations; stop
other LCATS processes first.
Local capture/build time is recorded separately from retrieval provenance;
unknown retrieval dates and HTTP validators remain unknown.

## Handle contention and platform limits

Only one setup, rebuild, activation or cleanup writer operates in a cache root
at a time. `lock_timeout=0` fails immediately with `CatalogLockError`; the default
is 10 seconds and the maximum is 60. Open readers continue without this lock.
The persistent `writer.sqlite` coordination file must not be manually deleted.
SQLite releases the lock if a writer process exits or is killed.

Use a local filesystem supporting SQLite locks, atomic same-directory replacement
and hard links. Archives use no-clobber hard-link publication. Unsupported
filesystem operations fail explicitly; do not place this cache on a filesystem
with unreliable locking. On POSIX, the cache and its containing directories must
allow directory opens and fsync, so newly created paths and retries can be made
durable before publication. POSIX directory fsync supports the durability protocol;
on Windows the implementation promises process-interruption recovery, not a
power-loss durability guarantee. Cooperative callers must treat generation
files as immutable; same-user malicious filesystem changes are outside the
trust boundary.

See [catalog API reference](../reference/gettenberg-catalog.md) for querying and
[lifecycle reference](../reference/gettenberg-lifecycle.md) for operation contracts.
