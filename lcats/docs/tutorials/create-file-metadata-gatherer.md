# Create a gatherer with per-file metadata

Build a small collection from two HTML files, each supplying its own title and
creator. You will extract stories, verify cold and warm behavior without network
access, then learn how to register the gatherer with `lcats gather`.

This teaches the current interface useful for Kenny's Standard Ebooks work. It is
**not a Standard Ebooks parser**: the HTML and metadata conventions below are
invented tutorial fixtures. Actual EPUB/OPF/XHTML parsing and source selection need
fixtures from Kenny's implementation. No Gutenberg catalog is involved, and the
proposed shared `GatherResult` is not implemented here.

## 1. Prepare an isolated prototype

Activate the LCATS project environment and work from the repository's `lcats/`
directory. Use `scripts/develop` if the package is not installed. Create
`experimental/file_metadata_demo/` with an empty `__init__.py`. The prototype
belongs here until its parsing rules and tests are ready for promotion.

The tutorial test uses temporary output, cache and log directories. It never
requests a real ebook, initializes a catalog, or modifies existing corpora.

## 2. Write the collection module

Save this as `experimental/file_metadata_demo/gatherer.py`:

```python
"""Teach per-file metadata extraction using authored HTML fixtures."""

import pathlib

import bs4

from lcats.gatherers import downloaders
from lcats.utils import run_log

# Stable output identities are independent of the title found in each file.
ITEMS = (
    ("lantern", "https://example.invalid/lantern.html"),
    ("harbor", "https://example.invalid/harbor.html"),
)


def extract_document(contents, source_url):
    """Read the tutorial's explicit metadata and story region.

    Real providers need their own validated metadata and body selectors.
    Reject missing fields instead of falling back to the entire document.
    """
    soup = bs4.BeautifulSoup(contents, "lxml")
    title_tag = soup.find("meta", attrs={"name": "dc.title"})
    author_tag = soup.find("meta", attrs={"name": "dc.creator"})
    region = soup.find("article", id="story")
    title = title_tag.get("content", "").strip() if title_tag else ""
    author = author_tag.get("content", "").strip() if author_tag else ""
    if not title or not author or region is None:
        raise ValueError("missing tutorial title, creator, or story region")
    paragraphs = [p.get_text(" ", strip=True) for p in region.find_all("p")]
    body = "\n\n".join(p for p in paragraphs if p)
    if not body:
        raise ValueError("empty tutorial story")
    return title, body, {"author": author, "url": source_url, "title": title}


def gather(*, offline=False, cache_dir=None, log_dir="logs/gather"):
    """Gather this collection; return newly written paths under today's API."""
    cache = None if cache_dir is None else pathlib.Path(cache_dir) / "resources"
    target = downloaders.DataGatherer(
        "file_metadata_demo",
        description="Two authored tutorial stories",
        license="Authored tutorial fixtures only",
        offline=offline,
        cache=cache,
    )
    with run_log.RunLog(
        log_dir,
        "file_metadata_demo_gather_run_log.jsonl",
        corpus="file_metadata_demo",
        story_count=len(ITEMS),
    ) as log:
        for item_id, url in ITEMS:
            # Bind this iteration's URL; the callback reads metadata from this file.
            def extract(contents, source_url=url):
                return extract_document(contents, source_url)

            target.download(item_id, url, extract)
            log.event(
                "story_downloaded" if item_id in target.downloads else "story_skipped",
                filename=item_id,
                corpus="file_metadata_demo",
            )
    return target.downloads
```

`DataGatherer.download()` calls the extractor with decoded HTML and expects
`(description, body, metadata)`. It applies existing normalization and writes
`<LCATS_DATA_DIR>/file_metadata_demo/<item_id>/story.json`. Its current `downloads`
dictionary contains new writes only; warm output reuse returns an empty dictionary.
The fixed unique `ITEMS` in this exercise make the log classification unambiguous.
This is the existing HTML helper, not mass gathering's atomic publication or
structured refusal-continuation loop. Exceptions abort and the run log records
abortion; adding per-item recovery is a separate policy decision.

For collections sharing one author/year, `gatherlib.gather()` offers a shorter
wrapper with `entry_url` and `extraction_strategy`. Here we use the lower-level
callback because metadata varies per file; the helper's standard callback receives
collection-level author/year values. See [gatherlib](../../src/lcats/gatherers/gatherlib.py).

## 3. Test without downloading anything

Save this as `experimental/file_metadata_demo/gatherer_test.py`:

```python
"""Exercise the tutorial against real temporary files and authored sources."""

import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

from experimental.file_metadata_demo import gatherer
from lcats.gettenberg import resources
from lcats.utils import capture
from lcats.utils import names


class GathererTest(unittest.TestCase):
    def test_per_file_metadata_and_warm_reuse(self):
        """Two different authors survive; warm gathering preserves both outputs."""
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            cache = root / "cache"
            html_cache = cache / "resources"
            html_cache.mkdir(parents=True)
            for (item_id, url), author in zip(gatherer.ITEMS, ("Ada", "Bea")):
                html = (
                    f'<html><head><meta name="dc.title" content="{item_id}">'
                    f'<meta name="dc.creator" content="{author}"></head><body>'
                    '<nav>Do not include navigation.</nav><article id="story">'
                    f"<p>The {item_id} story.</p></article></body></html>"
                )
                # Seed only this legacy HTML helper's cache with authored fixtures.
                # This is not a way to import files into the verified ResourceStore.
                (html_cache / names.url_to_filename(url)).write_text(
                    html, encoding="utf-8"
                )
            with mock.patch.dict(os.environ, {"LCATS_DATA_DIR": str(root / "data")}):
                with mock.patch(
                    "lcats.gatherers.downloaders.load_page",
                    side_effect=AssertionError("unexpected network access"),
                ), capture.capture_output():
                    written = gatherer.gather(
                        offline=True, cache_dir=cache, log_dir=root / "logs"
                    )
                    self.assertEqual(set(written), {"lantern", "harbor"})
                    before = {
                        key: pathlib.Path(path).read_bytes()
                        for key, path in written.items()
                    }
                    for item_id, author in (("lantern", "Ada"), ("harbor", "Bea")):
                        story = json.loads(before[item_id])
                        self.assertEqual(story["metadata"]["author"], author)
                        self.assertEqual(story["body"], f"The {item_id} story.")
                    repeated = gatherer.gather(
                        offline=True, cache_dir=cache, log_dir=root / "logs"
                    )
                    self.assertEqual(repeated, {})  # Reused, not zero ready stories.
                    for key, path in written.items():
                        self.assertEqual(pathlib.Path(path).read_bytes(), before[key])

    def test_missing_metadata_is_rejected(self):
        """Do not publish a whole HTML page when its metadata is missing."""
        with self.assertRaises(ValueError):
            gatherer.extract_document("<p>Not a qualified source</p>", "fixture")

    def test_offline_cache_miss_is_an_error(self):
        """Offline mode must not silently fetch the missing source."""
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            with mock.patch.dict(os.environ, {"LCATS_DATA_DIR": str(root / "data")}):
                with capture.capture_output(), self.assertRaises(
                    resources.ResourcePolicyError
                ):
                    gatherer.gather(
                        offline=True, cache_dir=root / "cache", log_dir=root / "logs"
                    )
```

Run from `lcats/`:

```bash
python -m unittest discover -s experimental/file_metadata_demo -p '*_test.py'
scripts/format --check -- experimental/file_metadata_demo
scripts/lint experimental/file_metadata_demo
```

Expected result: three passing tests. The cold run writes two stories with different
authors; the warm run writes none and leaves both output files byte-identical.
Missing metadata and an offline cache miss fail explicitly. Capturing output is
local to the tests, so ordinary print debugging still works.

## 4. Register only when ready for a product collection

After validating the provider-specific parser, move the module to
`src/lcats/gatherers/file_metadata_demo/gatherer.py` with an `__init__.py`, move its
tests under `tests/gatherers_tests/`, and change the test import to
`from lcats.gatherers.file_metadata_demo import gatherer`. For a real collection,
choose its permanent name instead of registering this tutorial fixture.

Add that name to `NAMES` in
[planning.py](../../src/lcats/gatherers/planning.py). Under the current comprehension,
any new name other than `mass_quantities` receives:

```python
CollectionRequirement("file_metadata_demo", "fixed_url", "none")
```

The [main registry](../../src/lcats/gatherers/main.py) derives the conventional
module path from `NAMES` automatically; no separate registry edit is needed for
this layout. Adding a name also includes it in the default all-collection run,
so prototype discovery must not be registered prematurely.

Then check the registered collection's read-only plan:

```bash
lcats gather file_metadata_demo --dry-run --offline
```

It should say `fixed_url`, catalog use `none`, and no metadata catalog required.
Actual offline gathering requires cached source files or existing outputs; the
temporary test cache has already been removed. Do not run this fictional collection
online. The CLI currently ignores this gatherer's return value and reports aggregate
summaries only for `mass_quantities`; do not import an unimplemented `GatherResult`.

## 5. Apply the pattern to Standard Ebooks

Keep the `gather(*, offline=False, cache_dir=None)` entry point. If input URLs are
known, use `fixed_url` / `none`; if processing local files, declare `local` / `none`
explicitly in `REQUIREMENTS` after its comprehension. `none` means no Gutenberg
catalog, not no metadata. Source-specific discovery does not become Gutenberg
catalog discovery merely by changing the `catalog_use` label.

Replace the fixture extractor with independently tested parsing of Kenny's actual
file format and metadata. An EPUB archive is not decoded HTML: the demonstrated
HTML downloader cannot be handed an EPUB URL and expected to parse it. Use an
appropriate binary/local acquisition path and EPUB parser, preserve file identity
and ordered content, and define story boundaries using real fixtures. Do not apply
Gutenberg-specific boilerplate cleanup or invent Gutenberg IDs for another source.

Before product registration, test multiple authors/titles, missing metadata,
multi-story files, navigation/colophon exclusion, stable bucket names, cache misses,
warm reuse, failure logs and isolated output. Establish actual attribution/license
handling rather than copying the tutorial's fixture license. Coordinate the
[shared-result follow-up](../../project/development/gettenberg-post-adoption-backlog.md#gpa-e--shared-gather-result-contract-across-collections)
separately; it must not silently broaden error recovery or extraction behavior.
