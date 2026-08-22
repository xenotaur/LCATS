---
id: PROP-WORLDCON-FAST-PATH-ANNOTATION
type: design_proposal_set
status: adopted
implementation_status: not_started
---

# Fast-Path Annotation Pipeline for the Worldcon 2026 Paper Dataset

This proposal set records the design for `lcats annotate`, a new command
that writes `genre.json`/`scenes.json` sidecars (plus a per-bucket
`README.md`) via the already-mature `lcats assess`/`scene_analysis`
extractors, giving the Worldcon 2026 paper a real dataset on a ~10-day
timeline without depending on the slower, costlier ERW event/relation
extractor.

## Documents

- [`00_proposal.md`](00_proposal.md) — background, prior-art check,
  design decisions (sidecar scope/format, per-bucket README, promote
  validation, the two prerequisite `max_tokens` bug fixes, per-collection
  file-discovery convention, the `lcats stats` selector fix), non-goals,
  and implementation plan.

Governed by [`WS-WORLDCON-FAST-PATH-ANNOTATION`](../../../../workstreams/resolved/WS-WORLDCON-FAST-PATH-ANNOTATION.md).
