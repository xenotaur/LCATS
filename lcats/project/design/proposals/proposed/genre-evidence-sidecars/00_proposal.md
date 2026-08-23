---
id: PROP-GENRE-EVIDENCE-SIDECARS
type: design_proposal
title: Append-Only Genre Evidence Sidecars for LCATS Corpus Sampling
status: proposed
created_on: 2026-08-12
updated_on: 2026-08-12
implementation_status: not_started
implemented_by: []
supersedes: []
superseded_by: null
related_design:
  - lcats/project/design/design.md
  - lcats/project/design/event-role-world-genre-target-reconciliation.md
  - lcats/project/design/proposals/adopted/worldcon-fast-path-annotation/00_proposal.md
  - lcats/project/design/proposals/adopted/lcats-pipeline-checkpointing/00_proposal.md
  - lcats/project/design/proposals/proposed/erw-local-model-evaluation/00_proposal.md
  - lcats/project/workstreams/proposed/WS-WORLDCON-FAST-PATH-ANNOTATION.md
  - lcats/project/work_items/proposed/WI-ASSESS-0051.md
  - lcats/project/work_items/resolved/WI-LLM-0066.md
---

## Summary

Adopt an append-only `genre.json` sidecar model for LCATS stories, where
each sidecar records labeled genre assessments from metadata rules, models,
and humans as timestamped evidence with pipeline/model/API provenance. The
implementation proceeds experiment-first through
`experiments/05_metadata_genre_prefilter/`, then promotes validated sidecar
tranches into `corpora/` once promotion and annotation semantics can preserve
and extend existing evidence safely.

## Background / Motivation

The Worldcon paper needs a reliable, reviewable way to build genre-balanced
story samples across the eight LCATS target genres. LCATS already has a
model-based genre assessor and a fast-path annotation command that writes
`genre.json` sidecars, but the current sidecar shape is closer to a single
assessment result than a durable evidence record. That is not enough for the
next phase: the project wants to combine Gutenberg metadata/rule evidence,
local model detections such as `gpt-oss:20b`, and possible human
adjudication.

The current repo state also argues against jumping straight to corpus
mutation. LCATS' design principles emphasize non-destructive defaults,
auditability, explainability, and separation of concerns
(`lcats/project/design/design.md`). Existing `lcats annotate` writes
`genre.json`/`scenes.json` directly into story buckets, and existing
`lcats promote` validates sidecar shape but still wholesale-replaces
destination collections. The sidecar schema and tranche-promotion semantics
therefore need to be designed and validated before the project relies on
them for persistent corpus updates.

The first safe move is an experiment-local metadata genre prefilter. That
experiment can validate LCATS story identity handling, Gutenberg metadata
availability, rule-label normalization, repeated Gutenberg ID diagnostics,
and the proposed append-only assessment shape without changing corpus
layout. Once that works, the same evidence model can move into production
`genre.json` sidecars and `lcats annotate` can append additional model or
human assessments without discarding previous evidence.

## Prior Art Check

### Duplication search

- In-repo: Related work exists, but no duplicate implementation or proposal
  was found. `lcats annotate` already writes `genre.json`/`scenes.json`
  sidecars; `lcats promote` validates basic sidecar parse/shape;
  `experiments/04_genre_census` records model-only genre census output;
  `WI-LLM-0066` scopes local `gpt-oss:20b` genre-census wiring. None define
  an append-only multi-assessment genre sidecar with metadata/model/human
  provenance.
- Sibling repos: None identified.
- External libraries: No external library replaces this design. General
  provenance practice is relevant, but the implementation is a project-local
  corpus sidecar and pipeline concern.
- Recommendation: Proceed, reusing existing LCATS discovery, assessment,
  checkpoint, annotate, and promote conventions where appropriate.

### Demand search

- Work items: `WI-ASSESS-0051` requests an 8-genre model census and
  per-story records; `WI-LLM-0066` requests local `gpt-oss:20b` wiring for
  that census. Both are related but not substitutes for multi-source
  sidecar evidence.
- Proposals: `PROP-WORLDCON-FAST-PATH-ANNOTATION` establishes the existing
  fast-path sidecar writer and promotion validation path. This proposal
  extends that direction from one-shot sidecar output toward append-only
  genre evidence.
- Backlog: No direct backlog entry found for append-only genre evidence
  sidecars. Related backlog/workstream material concerns sidecar discovery,
  stats correctness, checkpointing, and local model evaluation.
- Recommendation: Proceed; link this proposal to the Worldcon annotation,
  pipeline checkpointing, genre census, and local model evaluation tracks.

## Design Decisions

### Decision 1: Primary story identity

Options considered:
- Use Gutenberg book ID as the primary story identifier.
- Use LCATS story identity, derived from the story bucket path, and record
  Gutenberg ID only as provenance.

**Chosen: LCATS story identity is primary.** A single Gutenberg ID can
cover a collection volume from which many LCATS story buckets are extracted,
so Gutenberg ID is not a story identity. The sidecar should identify the
story by an LCATS-relative path or bucket ID, such as
`corpora/sherlock/scandal_in_bohemia`, and include Gutenberg ID under
assessment provenance when applicable.

### Decision 2: Evidence model for `genre.json`

Options considered:
- Fixed top-level slots such as `metadata_rules`, `model`, and `human`.
- A single overwritten "current genre" object.
- An append-only `assessments[]` ledger.

**Chosen: append-only `assessments[]`.** Each metadata, model, or human
assessment is a separate labeled record with timestamp, scope, method,
pipeline/model/API provenance, evidence, and result fields. This supports
rerunning a model several times, comparing multiple methods, downstream
voting, and later human adjudication without schema churn or destructive
updates.

The sidecar shape is:

```json
{
  "schema_version": "genre-sidecar-v1",
  "lcats_id": "corpora/sherlock/scandal_in_bohemia",
  "story_path": "corpora/sherlock/scandal_in_bohemia/story.json",
  "assessments": [],
  "current_adjudication": null
}
```

`genre-sidecar-v1` validation is implemented in
`lcats.analysis.corpus.genre_sidecar`. The validator is intentionally
structural: it accepts append-only metadata/model/human assessment records
with required identity, timestamp, scope, method/provenance/evidence/result
fields; accepts canonical metadata/model/human labels plus category-prefixed
future labels; requires model assessments to carry an explicit `run_id` or
`provenance.run_id` for repeated-run voting; validates optional
`current_adjudication`; and returns structured findings instead of raising for
ordinary malformed inputs. Legacy flat `AssessmentResult.to_dict()` sidecars
are detected and reported as non-v1 rather than converted in place.

A metadata assessment has this approximate shape:

```json
{
  "assessment_id": "metadata_rules__2026-08-12T01:22:00Z",
  "label": "gutenberg_metadata_rules",
  "generated_at": "2026-08-12T01:22:00Z",
  "scope": "gutenberg_volume",
  "method": {
    "name": "lcats.utils.genre.GENRE_RULES",
    "version": "pilot-v1"
  },
  "provenance": {
    "pipeline": "experiments/05_metadata_genre_prefilter",
    "api": null,
    "model": null,
    "gutenberg_id": 1661
  },
  "evidence": {
    "subjects": [],
    "raw_matches": [],
    "target_candidates": ["mystery"],
    "secondary_signals": []
  },
  "result": {
    "primary_genre": "mystery",
    "confidence": null,
    "verdict": "candidate"
  }
}
```

A model assessment appends another record rather than replacing the
metadata record:

```json
{
  "assessment_id": "model__gpt-oss-20b__run-001__2026-08-12T01:35:00Z",
  "label": "model_detect",
  "run_id": "model-genre-pilot-2026-08-12-run-001",
  "generated_at": "2026-08-12T01:35:00Z",
  "scope": "story",
  "method": {
    "name": "assess_story_detect_mode",
    "version": "assess_classifier_v2"
  },
  "provenance": {
    "pipeline": "lcats annotate",
    "backend": "openai-compatible",
    "api_base_url": "http://localhost:11434/v1",
    "model": "gpt-oss:20b",
    "checkpoint_run_id": "model-genre-pilot-2026-08-12-run-001",
    "temperature": 0.2
  },
  "evidence": {
    "summary": "A detective investigation centered on a coded clue.",
    "issues": []
  },
  "result": {
    "primary_genre": "mystery",
    "confidence": 0.97,
    "verdict": "detected",
    "secondary_genre": ""
  }
}
```

### Decision 3: Initial artifact location

Options considered:
- Write production `genre.json` files into story buckets immediately.
- Extend `experiments/04_genre_census`.
- Create a new `experiments/05_metadata_genre_prefilter/` runner first.

**Chosen: create `experiments/05_metadata_genre_prefilter/` first.** The
first runner is an experiment-local staging tool that writes JSONL manifests
and summaries under its own `results/` directory. It validates schema and
sampling behavior without changing `data/` or `corpora/`. `04_genre_census`
remains model-census oriented and population-weighted; this experiment is
metadata-prefilter and genre-sample oriented.

### Decision 4: Gutenberg metadata handling

Options considered:
- Let the runner call Gutenberg metadata APIs freely and build/download
  cache if missing.
- Require a cache preflight and refuse network/cache creation by default.
- Ignore Gutenberg metadata until model detection is available.

**Chosen: cache preflight plus no-network default.** The project already has
a local Gutenberg cache outside this worktree. Before any metadata pass, the
user and agent should sync the cache path or make it available to the
worktree. The experiment must report cache availability and skip metadata
enrichment when unavailable rather than silently downloading or building a
new cache.

This still allows an opportunistic whole-corpus metadata pass: if the cache
is local, available, and fast, the experiment may label all corpus stories
with metadata-rule evidence as an experiment result. That full metadata pass
does not block the 40-story or 200-story pilots.

### Decision 5: Metadata label normalization

Options considered:
- Treat `lcats.utils.genre.classify_exclusive()` as ground truth.
- Normalize all matching metadata rule labels into target candidates and
  secondary signals.
- Ignore non-target metadata labels.

**Chosen: normalize all matches as evidence.** The existing metadata rules
produce labels such as `SF`, `Humor / satire`, `Crime`, `Sea`,
`Historical`, and `War`, which do not map one-to-one to the eight target
genres. Direct mappings become target candidates:

- `SF` -> `science fiction`
- `Fantasy` -> `fantasy`
- `Horror` -> `horror`
- `Mystery` -> `mystery`
- `Western` -> `western`
- `Adventure` -> `adventure`
- `Romance` -> `romance`
- `Humor / satire` -> `humor`

Suggestive or non-target labels are retained as evidence, not ground truth:
`Crime` can support `mystery`; `Sea`, `Historical`, `War`,
`Children / juvenile`, and similar labels remain secondary signals unless a
later design explicitly upgrades them.

### Decision 6: Sampling strategy

Options considered:
- Start with the final 100-200 story sample.
- Start with a small, heterogeneous tooling pilot.
- Run a full metadata corpus pass first.

**Chosen: start with a 40-story tooling pilot, then expand.** The first
experiment selects roughly 10 Lovecraft, 10 Sherlock, 10 O. Henry, and 10
`mass_quantities` stories. Its purpose is to prove cache access,
manifesting, LCATS identity, metadata evidence, and sidecar schema. The
larger pilot follows with roughly 100-200 stories: about 30 stories in the
top five paper categories and at least 10 in the remaining categories,
subject to corpus availability and audit needs.

Repeated Gutenberg ID caps are optional sampling-quality parameters, not
identity rules. The runner should report repeated Gutenberg ID distribution
and support caps, but it should not imply that repeated Gutenberg metadata
invalidates distinct LCATS stories.

### Decision 7: Promotion and annotation semantics

Options considered:
- Commit sidecars directly under `corpora/`.
- Use current `lcats promote` wholesale collection replacement.
- Add sidecar-tranche promotion and append-mode annotation.

**Chosen: add sidecar-tranche promotion, legacy conversion, and append-mode
annotation before committing persistent sample sidecars.** Direct `corpora/`
edits bypass the project's release gate. Current promotion wholesale-replaces
destination collections, which is too blunt for adding a tranche of
`genre.json` sidecars to existing story buckets. A later implementation must
let `lcats promote` safely promote selected sidecars, and `lcats annotate`
must be able to read an existing sidecar, append a new assessment, and write a
new version without discarding previous evidence.

Append mode must explicitly handle legacy flat `genre.json` sidecars already
produced by the current writer. When the loaded sidecar has the existing flat
`AssessmentResult.to_dict()` shape and no `assessments` array, the upgrader
must wrap that flat result as the first `genre-sidecar-v1` assessment with
its original available metadata/provenance preserved, then append new
assessments after it. Initializing an empty ledger over a legacy file is not
acceptable because it would silently discard existing model evidence. Schema
and promotion validation should include this legacy-to-v1 conversion case
before append mode is used for corpus promotion.

### Decision 8: Local model genre assessment

Options considered:
- Fold local model detection into the first metadata experiment.
- Implement metadata sidecars first, then add model assessments through a
  separate experiment/API and eventually `lcats annotate`.
- Defer model detection entirely.

**Chosen: metadata first, model second, with explicit run identity for
independent repeats.** `gpt-oss:20b` is promising for genre detection, but
local-model integration and repeated model runs are separate concerns from
metadata cache access and sidecar schema validation. After the metadata
sidecar path is proven, a follow-on experiment or API can append model
assessments using `assess_story()` detect mode and record full
backend/model/API provenance.

Repeated model assessments need an explicit `run_id` or nonce in both the
assessment record and the checkpoint/fingerprint identity. The current
annotation path can intentionally reuse cached results for the same story,
model, prompt, and configuration, which is correct for resumability within a
single run but not sufficient for independent repeated assessments. The model
assessment implementation should therefore distinguish "resume the same run"
from "start an independent run for voting" by including the run identity in
the cache key while still allowing checkpoint reuse inside that run.

### Decision 9: Human adjudication

Options considered:
- Make human adjudication mandatory before any sidecar is promoted.
- Represent human review as another assessment and leave adjudication
  optional.
- Store human review outside `genre.json`.

**Chosen: represent human review in the same assessment ledger, with
optional `current_adjudication`.** A human assessment is a labeled
assessment record with reviewer/time/notes provenance. If the project needs
a single current label, `current_adjudication` can point to or summarize the
selected assessment/consensus, but absence of adjudication should not block
metadata or model evidence from being recorded.

## Non-Goals

- Does not implement the design. This proposal scopes the architecture and
  workstream only.
- Does not run Gutenberg metadata extraction, local model calls, or event
  extraction.
- Does not download or build the Gutenberg cache. Cache sync and no-network
  preflight are required before metadata use.
- Does not replace `WI-ASSESS-0051`'s genre census or `WI-LLM-0066`'s
  local-model census wiring. Those remain related but separate.
- Does not make `gpt-oss:20b` production-ready for ERW entity extraction or
  segmentation.
- Does not define the Worldcon paper's final statistical analysis methods.
  The proposal only creates the genre evidence substrate those tools can
  use.
- Does not require a new schema-validation library. Validation depth is left
  to work-item design and may begin with parse/shape checks consistent with
  existing promote behavior.

## Implementation Plan

This is a multi-stage workstream. Suggested delivery order:

1. **Cache preflight and experiment 05 scaffold.** Create
   `experiments/05_metadata_genre_prefilter/` with a no-network cache
   readiness check, LCATS story discovery, Gutenberg ID parsing, and dry-run
   manifest output.

2. **Metadata rule evidence and 40-story pilot.** Add metadata-rule
   assessment generation when a local Gutenberg metadata cache is available.
   Select the 40-story heterogeneous tooling pilot and write
   `candidates.jsonl`, `pilot_40_manifest.jsonl`, and `summary.json`.

3. **Sidecar schema validation.** Define and test the `genre-sidecar-v1`
   parse/shape rules, including `schema_version`, LCATS identity,
   `assessments[]`, timestamps, scope, method/provenance, legacy flat
   sidecar conversion, and optional adjudication.

4. **Sidecar-tranche promotion.** Extend `lcats promote` or add a scoped
   promotion mode so selected sidecars can be promoted into `corpora/`
   without wholesale collection replacement.

5. **Promote the pilot 40 sidecars.** Materialize metadata-rule `genre.json`
   sidecars for the pilot stories, promote them through the new tranche
   path, and commit them.

6. **Expand metadata sample.** Select and promote the larger 100-200 story
   sample, targeting roughly 30 stories in the top five paper categories and
   at least 10 in remaining categories, with repeated Gutenberg ID and
   author/collection distribution reported.

7. **Append-mode `lcats annotate`.** Teach `lcats annotate` to load an
   existing `genre.json`, convert legacy flat sidecars to the append-only v1
   ledger when needed, append model or human assessments, and write the
   updated sidecar through checkpoint-safe/atomic publication.

8. **Local model genre assessment.** Add a follow-on experiment or API to
   append `gpt-oss:20b` model assessments with full backend/model/API
   provenance and explicit run identity for independent repeats, then wire it
   into `lcats annotate`.

9. **Human review/adjudication support.** Add a minimal way to append human
   assessments and, when desired, set `current_adjudication`.

10. **Event extraction and analysis follow-ons.** Once genre sidecars are
    stable, apply the same experiment-first pattern to event extraction and
    then build Worldcon analysis tools over the promoted sample.

## Cross-References

- `lcats/project/design/design.md` - LCATS non-destructive, auditable
  pipeline principles.
- `lcats/project/design/event-role-world-genre-target-reconciliation.md` -
  genre/sample motivation for Worldcon work.
- `lcats/project/design/proposals/adopted/worldcon-fast-path-annotation/00_proposal.md`
  - existing fast-path annotation sidecar direction.
- `lcats/project/design/proposals/adopted/lcats-pipeline-checkpointing/00_proposal.md`
  - checkpoint-safe staged execution precedent.
- `lcats/project/design/proposals/proposed/erw-local-model-evaluation/00_proposal.md`
  - local model evaluation context.
- `lcats/project/work_items/proposed/WI-ASSESS-0051.md` - current
  8-genre model census.
- `lcats/project/work_items/resolved/WI-LLM-0066.md` - local
  `gpt-oss:20b` genre-census wiring.

## Open Questions

- Exact LCATS ID string form: relative bucket path with or without the
  leading `corpora/` prefix.
- Exact `assessment_id` generation: deterministic hash of source inputs vs.
  human-readable label plus timestamp.
- Whether `current_adjudication` should copy the chosen result or reference
  assessment IDs only.
- Whether full-corpus metadata-rule labeling should become a committed
  experiment result if cache access is fast and high quality.
- Exact CLI surface for sidecar-tranche promotion and append-mode
  annotation.
