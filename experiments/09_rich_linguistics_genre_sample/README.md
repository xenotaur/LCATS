# Rich Linguistics Genre Sample Pilot

This experiment runs the rich linguistic sidecar pipeline over the fixed
146-story genre-balanced sample selected by
`experiments/05_metadata_genre_prefilter`.

The experiment mirrors source story buckets under `results/copied_buckets/`
before analysis. Generated `linguistics.json`, `linguistics.tokens.json`, and
`linguistics.lexicon.json` files stay inside that mirror and are not written to
`corpora/`.

`parquet_bridge.py` exports those canonical JSON artifacts into a compact
experiment-scoped Parquet package for reusable token statistics, and restores
the canonical JSON files when existing validators or downstream tools need
them.

## Audit Protocol

The pilot preregisters a human POS audit before scoring:

- backend: spaCy by default, with exact model/library provenance from each
  sidecar;
- labels: `NOUN`, `PROPN`, and `OTHER`;
- combined noun family: `NOUN` or `PROPN`;
- pass gate: combined noun-family precision >= 0.90 and recall >= 0.90;
- severe genre-slice failure: any genre with at least 10 audited rows has
  combined noun-family precision or recall below 0.80;
- Stanza comparison: warranted when the spaCy audit misses or is inconclusive
  against the registered gate, otherwise not required for the pilot;
- downstream noun figures: proceed only after scored human labels pass the
  quality gate.

Run without labels to generate the sample packet:

```bash
python experiments/09_rich_linguistics_genre_sample/run_rich_linguistics_sample.py --overwrite
```

Initialize the separate review ledger. The generated sample CSV is an
immutable input and must not be edited:

```bash
python experiments/09_rich_linguistics_genre_sample/audit_pos.py start
```

Inspect progress and retrieve the next unresolved row as JSON:

```bash
python experiments/09_rich_linguistics_genre_sample/audit_pos.py status
python experiments/09_rich_linguistics_genre_sample/audit_pos.py next
```

Record one human decision in the ledger. Use `reviewed` only with a final
`NOUN`, `PROPN`, or `OTHER` label. Unresolved decisions require an explanatory
note, and issue codes can be repeated when more than one problem applies:

```bash
python experiments/09_rich_linguistics_genre_sample/audit_pos.py record \
  --token-key "story/id#g42" \
  --disposition reviewed \
  --label NOUN \
  --issue-code context \
  --notes "Context supports the noun reading." \
  --reviewer "name"
```

Validate the complete ledger, then produce the scored human-audit report:

```bash
python experiments/09_rich_linguistics_genre_sample/audit_pos.py validate
python experiments/09_rich_linguistics_genre_sample/audit_pos.py score
```

Scoring refuses pending, uncertain, blocked, invalid, stale, or incomplete
records. It preserves issue metadata and delegates aggregate metrics and gate
decisions to the pilot's existing deterministic scorer. The result is written
to `results/pos_audit_scored.json` for the full-corpus gate.

Export the generated v2 token detail to Parquet:

```bash
python experiments/09_rich_linguistics_genre_sample/parquet_bridge.py export experiments/09_rich_linguistics_genre_sample/results/copied_buckets experiments/09_rich_linguistics_genre_sample/results/parquet
```

Restore canonical JSON from the Parquet package:

```bash
python experiments/09_rich_linguistics_genre_sample/parquet_bridge.py restore experiments/09_rich_linguistics_genre_sample/results/parquet /tmp/lcats_wi0007_restore
```
