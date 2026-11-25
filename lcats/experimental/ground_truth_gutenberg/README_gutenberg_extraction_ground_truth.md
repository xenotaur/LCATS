# LCATS Gutenberg opening ground-truth builder

This standalone script uses **the same Gettenberg source initialization sequence as the uploaded `main.py`**, so no factory or additional LCATS application code is necessary. Run it from an environment where `lcats` is installed/importable and where the Gutenberg catalog and original text cache have already been prepared by LCATS.

## Run

Place `new.zip` beside the script, then run:

```bash
python build_gutenberg_extraction_ground_truth.py \
    --archive new.zip \
    --output gutenberg_extraction_ground_truth.json
```

The defaults are `new.zip` and `gutenberg_extraction_ground_truth.json`, so simply running `python build_gutenberg_extraction_ground_truth.py` also works.

Optional flags, matching the relevant source-configuration overrides accepted by LCATS gathering:

```bash
python build_gutenberg_extraction_ground_truth.py \
    --archive /path/to/new.zip \
    --cache-dir /path/to/your/existing/cache \
    --max-lines 100
```

`--catalog-archive`, `--catalog-url`, `--main-root`, and `--generated-root` are also accepted when your gathering workflow uses non-default configuration. In ordinary installations, leave these unset.

**Offline safety:** the script forces `NetworkPolicy(online=False)` and `CatalogPreparation(..., offline=True)` and uses `service.prepare(approved=False)`. It never asks permission to initiate a first-time network setup. If the catalog or original story bytes have not been cached, Gettenberg may report a cache/setup error. Run your normal LCATS gather first to prepare the cache, or use the same local catalog configuration that was used for gathering. The script does not download missing texts.

## How source initialization works

The script reproduces the source setup from your `main.py`:

```python
routes = sources_cli.gutenberg_routes(main_root, generated_root)
request = sources_cli.catalog_request(archive=catalog_archive, url=catalog_url)
policy = resources.NetworkPolicy(online=False, allowed_origins=...)
service = preparation.CatalogPreparation(
    cache_dir, archive=catalog_archive, request=request,
    policy=policy, offline=True,
)
service.prepare(approved=False)
with service.manager.open() as catalog:
    source = gutenberg_source.GutenbergStorySource(
        catalog, service.store, routes=routes, policy=policy
    )
```

Each story is then read with `source.metadata(gutenberg_id)` and `source.read(metadata).cleaned.text`. The script **does not call LCATS's narrative/front-matter parser**; that would remove the very evidence the reviewers need.

## Result

The output is a JSON array sorted by Gutenberg ID. Each record contains `gutenberg_id`, `title`, `authors`, `original_opening`, `first_narrative_text`, `review_status`, and `physical_lines_included`. `original_opening` and `first_narrative_text` are **identical** at creation. Reviewers should edit only `first_narrative_text`, removing unwanted text, and change the status to `verified`.

The first 20 physical lines count blanks and preserve indentation and italic markers. If the opening contains no obvious long mixed-case prose line, the script adds blocks of 20 lines, up to 100 by default. This is a **context-extension heuristic**, not a front-matter classifier: it can stop early on a prose-like editorial blurb, or extend unnecessarily on a short-dialogue opening. Inspect flagged examples and rerun with `--max-lines 200` before annotation if needed; never rerun over an existing annotated JSON file.

Missing-cache or processing failures are recorded in a companion `gutenberg_extraction_ground_truth_errors.json`, and the command exits with code 1 if some IDs fail. The source cache, corpus, registry, parser, and gatherer are not modified. Existing JSON outputs are never overwritten.

## Tests

```bash
python -m unittest -v test_gutenberg_extraction_ground_truth
```

Six offline tests cover physical line counts, extra context, metadata provenance, missing-cache handling, the source setup constructor sequence, and the CLI. These mock Gettenberg; an end-to-end run against the installed LCATS cache has not been performed in this environment.
