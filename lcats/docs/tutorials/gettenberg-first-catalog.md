# Build and reuse your first Gutenberg catalog offline

This tutorial takes a retained RDF fixture through planning, setup, queries and
recovery. It downloads nothing and writes only a temporary directory. You need a
repository checkout with the LCATS project environment installed. Start Python
from `LCATS/lcats`, and run the examples in order in the same session.

## Make a tiny local archive

The repository retains original RDF records with their
[provenance](../../tests/gettenberg_tests/fixtures/provenance.json). Package one
record into the archive format accepted by the public API. This is a learning
fixture, not a representative full Gutenberg snapshot.

```pycon
>>> import pathlib
>>> import tarfile
>>> import tempfile
>>> from lcats.gettenberg import catalog, errors, lifecycle, preparation, resources
>>> temporary = tempfile.TemporaryDirectory()
>>> root = pathlib.Path(temporary.name)
>>> fixtures = pathlib.Path("tests/gettenberg_tests/fixtures")
>>> archive_path = root / "one-book.tar.bz2"
>>> with tarfile.open(archive_path, "w:bz2", format=tarfile.USTAR_FORMAT) as archive:
...     archive.add(fixtures / "pg84.rdf", arcname="pg84.rdf")
>>> cache_dir = root / "cache"
>>> service = preparation.CatalogPreparation(cache_dir, archive=archive_path, offline=True)
>>> plan = service.prepare(dry_run=True)
>>> (plan.action, plan.acquisition, plan.approval_required)
('setup', 'local', True)
>>> cache_dir.exists()
False

```

The plan checks local availability, not archive validity. Setup is the operation
that parses and verifies the archive. Even offline setup needs approval through
`CatalogPreparation`; approval is restricted to creating a missing catalog.

```pycon
>>> try:
...     service.prepare()
... except preparation.PreparationError:
...     print("Setup needs approval")
Setup needs approval
>>> generation = service.prepare(approved=True)
>>> generation.reused
False
>>> manager = lifecycle.CatalogManager(cache_dir)
>>> manager.status()["state"]
'ready'
>>> with manager.open() as library:
...     print(library.find_ids(catalog.Filters(ids=(84,))))
...     print(library.get(84).ebook.gutenberg_id)
(84,)
84

```

A reader is a context-managed session pinned to one generation. Metadata queries
never download a book. The catalog stores the source record as well as searchable
fields; an absent ID returns `None`.

## Reuse the catalog and inspect an offline miss

A ready catalog needs no setup approval. It is reused even if the newly supplied
archive path does not exist; setup is not a refresh command.

```pycon
>>> reused = preparation.CatalogPreparation(
...     cache_dir, archive=root / "not-downloaded.tar.bz2", offline=True,
... ).prepare()
>>> (reused.reused, reused.generation_id == generation.generation_id)
(True, True)
>>> store = resources.ResourceStore(cache_dir)
>>> request = resources.SourceRequest.from_url("https://example.org/story.txt")
>>> resource_plan = store.plan(request)
>>> (resource_plan.action, resource_plan.reason)
('blocked', 'offline cache miss')
>>> try:
...     store.fetch(request)
... except resources.ResourcePolicyError:
...     print("No download is authorized")
No download is authorized

```

`example.org` is an inert teaching placeholder here. A resource cache is separate
from the catalog: having metadata does not mean book bytes are present. An
already acquired resource can be reused with `store.fetch(request)` offline;
verified bytes are returned without a freshness check. See the
[acquisition guide](../how-to/gettenberg-resources.md) for explicit online policy,
cached reuse and deliberate refresh. Corrupt evidence raises an integrity error
instead of becoming a download opportunity.

## Recover a candidate that needs count approval

Add a second retained record to a new archive. A deliberate rebuild prepares a
candidate but refuses to publish a changed ebook count without separate approval.
The old generation remains usable while you inspect the change.

```pycon
>>> larger_archive = root / "two-books.tar.bz2"
>>> with tarfile.open(larger_archive, "w:bz2", format=tarfile.USTAR_FORMAT) as archive:
...     for name in ("pg84.rdf", "pg10000.rdf"):
...         archive.add(fixtures / name, arcname=name)
>>> candidate_id = None
>>> with manager.open() as pinned:
...     try:
...         manager.rebuild(larger_archive)
...     except errors.CatalogCountChangeError as change:
...         candidate_id = change.generation_id
...         print(change.previous, change.candidate)
...     print(pinned.find_ids())
1 2
(84,)
>>> candidate_id in manager.status()["candidates"]
True
>>> manager.status()["active"]["generation_id"] == generation.generation_id
True

```

We deliberately added precisely one record in this fixture. After reviewing that
change, activate the already prepared candidate rather than rebuilding it. This
explicit call approves a count difference against the active generation at
activation time; a saved plan is not a concurrency-safe approval token.

```pycon
>>> recovered = manager.activate(candidate_id, allow_count_change=True)
>>> with manager.open() as library:
...     print(library.find_ids())
(84, 10000)
>>> generation.catalog_path.exists()
True
>>> recovered.generation_id == candidate_id
True
>>> temporary.cleanup()

```

The last line removes this tutorial's temporary files. Normal lifecycle cleanup
retains published generations and archives, but removes abandoned candidates;
activate candidates you need before cleaning them. Interrupted publication and
invalid active pointers need the more specific
[recovery procedure](../how-to/gettenberg-catalog.md#recover-after-interruption).

For real gathering, continue with [the gathering guide](../how-to/gettenberg-gather.md).
The CLI supplies a default source profile and prompts for missing setup; the
library intentionally requires explicit input. Neither setup approval nor a
cache hit authorizes refresh, count changes or replacement of story outputs.
