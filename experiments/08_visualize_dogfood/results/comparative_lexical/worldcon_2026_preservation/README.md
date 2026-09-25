# Worldcon 2026 Comparative Lexical Figure Preservation

This subtree preserves the final non-POS complement-overlay figures prepared
for the LCATS Worldcon 2026 poster and presentation, together with their
numeric CSVs and historical generating scripts.

These files predate the reusable `lcats visualize compare` implementation.
They are retained as evidence of the figures actually reviewed and used, not
as a second supported visualization API and not as completion of
`WI-VISUALIZE-0094` or `WI-VISUALIZE-0095`.

## Preserved figures

| Directory | Target panels | Stories | Usable tokens |
|---|---|---:|---:|
| `science_fiction_vs_complement/` | Science Fiction versus its non-SF complement | SF 20; complement 126 | SF 41,334; complement 311,833 |
| `science_fiction_vs_fantasy/` | SF and Fantasy, each over its own complement | SF 20; Fantasy 20; each complement 126 | SF 41,334; Fantasy 23,955; complements 311,833 and 329,212 |
| `horror_vs_humor/` | Horror and Humor, each over its own complement | 20 each; complements 126 each | Horror 58,239; Humor 44,079; complements 294,928 and 309,088 |
| `mystery_vs_romance/` | Mystery and Romance, each over its own complement | 20 each; complements 126 each | Mystery 55,148; Romance 56,421; complements 298,019 and 296,746 |
| `western_vs_adventure/` | Western and Adventure, each over its own complement | Western 20; Adventure 6; complements 126 and 140 | Western 58,732; Adventure 15,259; complements 294,435 and 337,908 |

The declared universe is the checked-in 146-story genre-balanced manifest.
Every complement is computed independently as `U - S` using the manifest's
single `selection_genre` label. The sample contains 353,167 usable tokens.

All figures share the same 20 terms, selected as the most frequent terms over
the complete 146-story universe after lowercasing, alphabetic tokenization,
minimum length three, and removal of both LCATS and scikit-learn English
stopwords. Rates are occurrences per million usable tokens. Paired figures use
one visible numerical scale, but each gray baseline is the complement of the
genre in its own panel; the two gray baselines are therefore not identical.

## Provenance

- Source checkout used for the preserved generation: `d7f4ff81a6763f9af206bb1dbae88341954ec69d`.
- Selection manifest: `experiments/05_metadata_genre_prefilter/results/full_scan/genre_balanced_manifest.jsonl`.
- Manifest SHA-256: `c1425ce2102d7c5c97f7c639f5cd2f887e2bffea537f9c3983cc9d22b00645f7`.
- Aggregate SHA-256 over sorted `story_id:sha256(story_bytes)` pairs for the
  146 consumed story files: `71faecb7057002c32d3171a13ee78c97c066970fecc8383b18f5a5aed5f63e17`.
- Tokenization source: `lcats/src/lcats/analysis/story_analysis.py`.
- Tokenization-source SHA-256: `1e1feff9d18b5342973a5b1a00c0a3c6c2dd12a34484cd69fe571cfeaccb46fa`.
- `preservation_manifest.json` records the universe, term list, group sizes,
  denominators, and generator-to-output mapping.
- `SHA256SUMS` records the exact preserved output bytes.

The PNGs were visually reviewed at native resolution, the PDFs were rendered
with Poppler and checked for clipping/overlap, the SVGs were parsed with
editable text preserved, and every saved per-million rate and percentage
difference was independently recomputed to six decimal places.

## Historical generators

The scripts in `generators/` are the code used to create these layouts. Their
scratch-workspace paths were replaced by repository-relative paths, formatting
was normalized, and CSV writers now request LF line endings; the numerical and
rendering logic is unchanged. They intentionally retain the exact presentation
typography and chart design.

From the repository root, using the project Python environment:

```bash
python experiments/08_visualize_dogfood/results/comparative_lexical/worldcon_2026_preservation/generators/make_genre_sample_sf_reference_overlay_poster.py
python experiments/08_visualize_dogfood/results/comparative_lexical/worldcon_2026_preservation/generators/make_genre_sample_sf_vs_fantasy_complement_overlay_poster.py
python experiments/08_visualize_dogfood/results/comparative_lexical/worldcon_2026_preservation/generators/make_genre_sample_complement_pair_overlays_presentation.py
```

The generators assert the 146-story sample and expected genre memberships and
recompute every plotted rate. Regeneration can change PDF metadata or SVG
serialization across Matplotlib versions, so `SHA256SUMS` identifies the
preserved reviewed files rather than promising byte-identical regeneration.

## Limitations and migration

- The scripts are experiment-local historical generators. Reusable selection,
  comparison, provenance, and rendering behavior belongs in
  `lcats/src/lcats/visualize/`.
- The historical CSVs contain the displayed rates and percent differences but
  do not implement the complete `comparison_manifest.json` contract now
  produced by `lcats visualize compare`.
- The paired layouts are the motivating real-world examples for
  `WI-VISUALIZE-0095`; that work item should absorb the reusable multi-panel
  composition rather than generalizing these scripts in place.
- `WI-VISUALIZE-0094` should later regenerate the canonical indexed package
  from the production pipeline, with authoritative CSVs, comparison manifests,
  output hashes, and recorded selected/rejected variants.
- The manually selected noun chart is deliberately excluded. POS/noun figures
  enter the canonical package only if the rich-linguistics pilot authorizes
  them under the governing workstream.

Do not cite visible differences as statistical significance. These are
descriptive comparisons for this fixed sample and vocabulary.
