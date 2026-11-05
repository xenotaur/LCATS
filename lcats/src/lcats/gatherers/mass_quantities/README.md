# LCATS mass_quantities / Gettenberg integration

These files adapt the legacy LCATS `gutenberg_extractor.clean_gutenberg_story` to the newer, explicitly sourced Gettenberg gathering framework.

## Installation

Place `parser.py` in the LCATS module location that corresponds to `lcats.gatherers.parser` (as referenced in your new `gatherer.py`). Place `gatherer.py` at your mass-quantities gathering location. Keep the existing `lcats.gatherers.mass_quantities.gutenberg_extractor` module in place.

This package contains copies under their final names (`parser.py`, `gatherer.py`) in addition to the integration test. Do not overwrite your current files without a backup or version-control commit.

## Preserved Gettenberg behavior

- Caller-owned, explicit `source` required (no `api.get_metadata` or `api.load_etext`).
- `source.metadata(story)` and `source.read(metadata)`; uses `prepared.cleaned.text` and `prepared.provenance()`.
- `inspect_story`, `gather_story`, `gather_story_result`, `StoryGatherResult`.
- Existing output reuse, normalization, bucket naming, atomic publication, provenance.
- `gather_batch`, `BatchResult`, run logs, source-404 and cleanup-refusal classifications.

## Restored behavior

`_inspect_metadata` delegates the narrative extraction to:

```python
body = clean_gutenberg_story(
    text,
    title=list(metadata.titles),
    authors=list(metadata.authors),
    pseudonyms=list(metadata.aliases),
    remove_the_end=True,
)
```

The parser uses the legacy metadata eligibility filters and chapter/length tests. The old `body_of_text` heuristics are not used.

## Important limitations

1. Source and catalog construction are controlled by your application/CLI; these uploads did not include the concrete Gettenberg source constructor. Continue passing your already configured `source` to the batch API.
2. Existing outputs are reused without extraction or revalidation. For a full re-extraction following a cleaner change, arrange an explicit rebuild using your normal safe collection workflow; do not assume the gather command overwrites existing stories.
3. The integration tests mock Gettenberg/LCATS dependencies, because the complete LCATS package and real configured source were not provided. They verify the interface, extraction call, rejection short-circuit, and batch forwarding, but not a live download or your actual filesystem configuration.
4. The new Gettenberg resource decoder determines which text is made available for extraction. Its error/refusal behavior is retained; the extractor does not bypass resource decoding.
5. The original `chaptered` and story eligibility checks remain heuristic, just as in the uploaded parser. They may reject some valid short or chaptered literary works.

## Testing

Place the test alongside the package files and the existing `gutenberg_extractor.py` when running standalone:

```sh
python test_gettenberg_integration.py -v
```

It imports copies of the integration modules with mocked LCATS dependencies, plus the genuine extractor.
