---
id: PROP-LCATS-KNIGHT-NOVUM-ANALYSIS-SIDECAR
type: design_proposal
title: Knight and Novum Analysis Pipeline and Science-Fiction Sidecar
status: adopted
created_on: 2026-08-20
updated_on: 2026-08-21
implementation_status: not_started
implemented_by: []
supersedes: []
superseded_by: null
related_design:
  - lcats/project/design/design.md
  - lcats/project/design/event-role-world-genre-target-reconciliation.md
  - lcats/project/design/proposals/adopted/lcats-event-role-world-extractor/00_proposal.md
  - lcats/project/design/proposals/adopted/lcats-pipeline-checkpointing/00_proposal.md
  - lcats/project/design/proposals/adopted/lcats-story-bucket-layout/00_proposal.md
  - lcats/project/design/proposals/adopted/worldcon-fast-path-annotation/00_proposal.md
  - lcats/project/design/proposals/proposed/genre-evidence-sidecars/00_proposal.md
  - lcats/project/workstreams/proposed/WS-GENRE-EVIDENCE-SIDECARS.md
  - lcats/project/work_items/proposed/WI-GENRE-0004.md
---

## Summary

Adopt a checkpointed science-fiction analysis pipeline that prepares each
story once, extracts a shared theory-neutral evidence layer, and applies
independent Damon Knight and Darko Suvin adjudicators. Publish the evidence,
the seven-feature Knight profile, and the candidate-novum analysis in one
versioned, append-oriented `science-fiction.json` story-bucket sidecar after
an experiment-local 30-story feasibility pilot and a gated 100–200-story
Worldcon pilot.

## Background / Motivation

LCATS needs interpretable measures of how stories instantiate science-fiction
features, not merely a categorical genre label. Two complementary critical
frameworks have been selected. Damon Knight identifies seven recurring
elements whose mixture makes a story recognizable as science fiction:
science; technology and invention; future, remote-past, or time-travel
settings; extrapolation; scientific method; other places and visitors from
them; and natural or human-made catastrophe. Darko Suvin distinguishes
science fiction through a fictional novum that is cognitively validated and
narratively hegemonic, with estrangement arising from the difference between
the fictional world and the reader's empirical norm.

These frameworks overlap in the evidence they require, but they do not make
the same theoretical claim. A story can contain several Knight features
without a Suvinian hegemonic novum, or can organize itself around a single
qualified novum without exhibiting a large number of Knight features. The
pipeline should therefore reuse story reading, paragraph indexing, chunking,
and evidence extraction without merging the two judgments or forcing their
outputs to agree.

The current LCATS repository provides much of the required substrate:

- canonical bucket discovery treats only `<story>/story.json` as source and
  excludes sibling analysis JSON;
- `lcats annotate` separates checkpoint data from materialized sidecars,
  fingerprints model/prompt/schema/input state, and publishes sidecars
  atomically;
- the Event-Role-World (ERW) pipeline provides evidence spans, structured
  storyworld annotations, and an interpretive `anomaly_or_novum` tag;
- `genre-sidecar-v1` establishes an append-only assessment/validation pattern;
  and
- the Worldcon sampling work is moving toward a deterministic, genre-balanced
  100–200 story manifest with experiment-local output and a gated paid run.

What is missing is a specialized, theory-grounded analysis that qualifies and
scores Knight's categories and Suvin's novum, preserves the evidence and
provenance necessary to audit those judgments, and fits the bucket/sidecar
promotion model. Core implementation and a small contrastive pilot can
proceed independently of `WI-GENRE-0004`; only the larger Worldcon pilot
depends on its final sample manifest.

## Prior Art Check

### Duplication search

- In-repo: Related infrastructure exists, but no duplicate Knight/Suvin
  analysis or `science-fiction.json` sidecar was found. The adopted ERW
  proposal includes evidence spans, SF world-model tags, and
  `anomaly_or_novum`, but it does not operationalize Knight's seven features,
  test Suvin's novelty/cognitive-validation/hegemony conjunction, or produce
  the proposed sidecar. `lcats annotate` and the genre-evidence proposal
  establish reusable checkpoint, atomic-write, provenance, and append-only
  sidecar patterns.
- Sibling repos: None identified as implementing this LCATS-specific literary
  analysis. The Logical Robotics Harness supplies proposal and execution
  governance, not the analysis runtime.
- External libraries: No general-purpose library was identified that
  operationalizes Knight and Suvin with story-grounded evidence. General JSON
  validation, annotation-agreement, and model-evaluation libraries may support
  implementation, but do not replace the domain design.
- Recommendation: Proceed, explicitly reusing existing LCATS evidence,
  checkpoint, backend, bucket, and sidecar facilities where their contracts
  fit. Treat ERW output as an optional evidence source or comparison baseline,
  not a mandatory prerequisite.

### Demand search

- Work items: `WI-GENRE-0004` requests the deterministic 100–200 story
  Worldcon sample and bounded model validation that Phase 3 can consume, but
  it does not request Knight/Novum analysis. No proposed work item directly
  requests this scoring pipeline.
- Proposals: `PROP-LCATS-EVENT-ROLE-WORLD-EXTRACTOR`,
  `PROP-WORLDCON-FAST-PATH-ANNOTATION`, and
  `PROP-GENRE-EVIDENCE-SIDECARS` request adjacent evidence, annotation, and
  sidecar capabilities. None specify the two theoretical analyses proposed
  here.
- Backlog: No matching Knight/Novum scoring entry was found.
- Recommendation: Link the eventual workstream to `WI-GENRE-0004` as a Phase
  3 sample dependency and to the ERW/genre-sidecar work as reusable prior art;
  do not close or subsume those artifacts.

## Theoretical Contracts

### Knight profile

The primary Knight artifact is a seven-dimensional evidence profile, not a
genre probability or an invented pass/fail threshold. Each criterion records:

- `status`: `present`, `ambiguous`, `absent`, or `not_assessable`;
- `materiality`: `central`, `substantial`, or `incidental` when applicable;
- supporting evidence and counterevidence references;
- rationale; and
- confidence as provenance metadata, not as a replacement for evidence.

The deterministic summary is an interval:

- `definite_count`: number of `present` criteria; and
- `possible_count`: number of `present` plus `ambiguous` criteria.

Thus an output can be reported as, for example, `4–5 of 7`. LCATS must not
represent this value as Knight's probability that a story is science fiction,
nor attribute a numerical pass threshold to Knight. If a later study develops
a weighted index, it receives an explicitly LCATS-specific name, rubric
version, and validation history.

Before `knight-seven-v1` is frozen, the implementation workstream must
transcribe and cite the exact seven category descriptions from the selected
primary edition of Knight's essay. Secondary summaries may support
interpretation but do not govern the rubric text.

### Suvin novum analysis

For every candidate novum, adjudicate three required dimensions:

- `N` — **ontological novelty**: a meaningful storyworld change relative to
  the relevant author/implied-reader norm;
- `C` — **cognitive validation**: a coherent, nonsupernatural explanatory
  horizon, which need not be a detailed engineering derivation; and
- `H` — **narrative hegemony**: the candidate determines the story's
  overriding narrative logic rather than serving as incidental decoration.

Qualification is conjunctive: `qualified_novum = N AND C AND H`. The system
must not use a three-point additive score in which strength on one dimension
can compensate for failure on another.

After qualification, record estrangement as a reader-facing and storyworld
consequence profile. Character reaction is useful evidence but is not
mandatory: characters may treat the novum as ordinary while it remains
estranging to an implied reader. Support multiple candidates and allow either
a `dominant_novum` or a `novum_system` when several changes operate together.
The MVP output is categorical and evidence-grounded. Any later scalar, such
as a bottleneck `min(N, C, H)` value, is a separate research decision gated on
human-agreement results.

## Design Decisions

### Decision 1: Share preparation and evidence, not theoretical judgment

Options considered:

- one model call that extracts evidence and emits both scores;
- two fully independent end-to-end pipelines; and
- shared deterministic preparation and theory-neutral evidence extraction,
  followed by separate Knight and Suvin adjudicators.

**Chosen: shared extraction plus separate adjudicators.** This pays the
story-reading and evidence-extraction cost once while preserving the
different theories' contracts. A one-call black box couples errors, makes
score derivation difficult to audit, and pressures the outputs toward false
agreement. Fully separate pipelines maximize independence but duplicate
cost, anchors, and preparation.

Because shared extraction can create correlated omissions, each adjudicator
receives one bounded theory-specific follow-up retrieval opportunity when the
shared evidence appears incomplete. Both pilots also run independent
Knight-only and Suvin-only extraction on a stratified audit subset. Material
recall loss against that benchmark blocks scaling.

### Decision 2: Use adaptive whole-story and paragraph-aligned processing

Options considered:

- individual paragraphs without surrounding context;
- fixed-size token chunks;
- mandatory scene/sequel segments; and
- whole-story processing when safe, otherwise paragraph-aligned adaptive
  chunks.

**Chosen: adaptive whole-story/paragraph-aligned processing.** Stable
paragraph IDs provide canonical evidence anchors. Short stories retain global
context through a whole-story call; longer stories use versioned chunk plans
with overlap and preferred chapter/section boundaries. The provisional
starting configuration is approximately 3,000 target tokens, a 4,000-token
hard ceiling, and one paragraph of overlap, to be tuned from Phase 2 evidence
rather than treated as a permanent constant.

Scene/sequel data may be consumed through an optional adapter for navigation
or comparison, but cannot be a prerequisite. Requiring scenes would add a
costly and fallible dependency and would exclude otherwise analyzable stories.
Paragraph-only isolated classification is also rejected because explanations,
consequences, and narrative hegemony often span multiple paragraphs.

### Decision 3: Extract a small theory-neutral evidence graph

The shared extractor records storyworld changes, scientific or technical
explanations, inquiry methods, temporal/spatial displacement, extrapolative
consequences, catastrophes, character reactions, and reader-facing contrasts.
It does not emit Knight or Suvin decisions.

Each evidence item contains:

- a stable evidence ID and controlled neutral type;
- an exact quotation;
- paragraph IDs and optional character offsets;
- a short non-theoretical paraphrase;
- optional entity/event links;
- extraction confidence; and
- source chunk and run provenance.

Deterministic validation must locate every quotation in the indexed story,
reject or quarantine unlocatable evidence, de-duplicate chunk overlap without
discarding conflicts, and preserve the story hash used for alignment. Existing
ERW evidence may be adapted when available, but the MVP does not require a
full ERW run because its richer multi-pass cost and scene dependency are not
necessary for these two analyses.

### Decision 4: Keep model judgments structured and scoring deterministic

Model calls use strict structured-output schemas for evidence candidates and
criterion judgments. Python code computes all Knight counts, Novum
conjunctions, current pointers, and validation results. The model cannot
calculate or override authoritative summaries.

Validation enforces at least:

- every evidence reference exists and belongs to the same story hash;
- a `present` Knight criterion has supporting evidence;
- absence, ambiguity, and pipeline failure remain distinct;
- `qualified_novum=true` only when N, C, and H are all present;
- a dominant novum references an existing qualified candidate;
- a partial Knight or Suvin failure does not corrupt the other analysis; and
- `current` pointers select only complete, valid records.

### Decision 5: Publish one `science-fiction.json` sidecar

Options considered:

- `scoring.json` containing both analyses;
- separate evidence, Knight, and Novum sidecars;
- extending `genre.json`; and
- one domain-specific `science-fiction.json` envelope containing shared
  evidence and independently versioned analyses.

**Chosen: one `science-fiction.json` sidecar.** It makes the shared evidence
and its dependent analyses one atomic research artifact, prevents dangling
cross-file references during promotion, and gives the file a specific domain
meaning. `scoring.json` is too generic. Extending `genre.json` would blur
theory-based analysis with the authoritative genre-evidence ledger. Multiple
promoted files add transaction and promotion-order problems without an MVP
benefit.

The logical records inside the sidecar are append-only; physical publication
is an atomic whole-file rewrite by one orchestrator. Internal chunk/stage
checkpoints remain separate and are not promoted into story buckets.

An illustrative envelope is:

```json
{
  "schema_version": "science-fiction-sidecar-v1",
  "lcats_id": "collection/story",
  "story_path": "collection/story/story.json",
  "story_sha256": "...",
  "evidence_sets": [],
  "analyses": {
    "knight": [],
    "suvin_novum": []
  },
  "current": {
    "evidence_set_id": null,
    "knight_analysis_id": null,
    "suvin_novum_analysis_id": null
  },
  "comparisons": [],
  "validation": {}
}
```

Every run records backend/model, model version when available, prompt and
tool-schema hashes, rubric version, code commit, chunk configuration,
generation parameters, token use, cost, timestamp, and parent evidence-set
ID. Human adjudications receive their own record identity and lineage rather
than overwriting model results.

### Decision 6: Follow the existing validator pattern before adding a schema dependency

Implement `validate_science_fiction_sidecar()` as a pure-Python structural
and semantic validator following `genre_sidecar.py`. Do not add a production
JSON Schema dependency solely for Phase 1: LCATS does not currently depend on
one, and cross-record reference and story-hash checks require Python logic
regardless. A published JSON Schema may be added at full-corpus integration if
external consumers need language-neutral validation. If added, one schema
must be generated from or contract-tested against the authoritative model to
prevent validator drift.

### Decision 7: Use explicit stage contracts and partial-success semantics

The pipeline stages are:

| Stage | Output | Failure behavior |
| --- | --- | --- |
| `sf_prepare` | normalized text, paragraph index, story hash, chunk manifest | fail on missing/unusable body; never mutate source |
| `sf_evidence_chunk_n` | neutral evidence candidates for one chunk | retry/checkpoint per chunk; no scoring |
| `sf_evidence_aggregate` | anchored, de-duplicated evidence set | reject unlocatable quotes; retain conflicts |
| `sf_knight` | seven criteria and deterministic count interval | can complete if Novum fails |
| `sf_suvin_novum` | candidates, N/C/H decisions, estrangement profile | can complete if Knight fails |
| `sf_bundle` | validated sidecar envelope and current pointers | publish only a valid envelope |

Fingerprints include all effective inputs: story content and relevant
metadata, model/backend, token limits, prompts, tool schemas, rubric and
post-processing versions, and chunk configuration. A successful checkpoint
can rematerialize output without repeating a paid model call. The orchestrator
is the sole sidecar writer; parallelism is across stories, not concurrent
writes to one story.

### Decision 8: Keep pilots experiment-local until promotion is designed

Phases 1–3 write only beneath
`lcats/experimental/science_fiction_analysis_trial/` (or a workstream-approved
equivalent). They do not modify `lcats annotate`, `lcats promote`, `data/`, or
`corpora/`.

Current promotion wholesale-replaces collections and validates a fixed set of
legacy sidecars. Append-oriented analyses may evolve on a different cadence,
so production integration requires an explicit sidecar-tranche or otherwise
transaction-safe promotion design. This is a later integration gate, not a
reason to delay core code or pilots.

## High-Level Architecture

```text
story.json
    |
    v
prepare + paragraph index + story hash
    |
    v
shared theory-neutral evidence extraction
    |
    v
anchor validation + overlap-aware consolidation
    |                                      |
    v                                      v
Knight adjudicator                 Suvin adjudicator
    |                                      |
    +------------------+-------------------+
                       v
             bundle + semantic validation
                       |
                       v
              science-fiction.json
```

Recommended production module layout:

```text
lcats/src/lcats/analysis/science_fiction/
    __init__.py
    models.py
    preparation.py
    evidence.py
    knight.py
    novum.py
    sidecar.py
    pipeline.py
lcats/tests/analysis/science_fiction/
    test_preparation.py
    test_evidence.py
    test_knight.py
    test_novum.py
    test_sidecar.py
    test_pipeline.py
lcats/experimental/science_fiction_analysis_trial/
    README.md
    select_subset.py
    run_trial.py
    rubric/
    results/
```

The domain modules are production-quality and backend-independent, while
selection manifests, run reports, and generated pilot sidecars remain
experiment-local until the integration gate.

## Options and Disqualifying Limitations

| Option | Advantage | Limitation | Verdict |
| --- | --- | --- | --- |
| One combined extraction/scoring call | lowest call count | couples theories, obscures omissions, prevents reliable deterministic checking | disqualified for authoritative output |
| Two independent end-to-end pipelines | maximum independence | duplicates story reading, cost, anchors, and preparation | retain only as an audit benchmark |
| Shared extraction + separate adjudication | reuse with theory independence | shared omissions can affect both | chosen; mitigate with follow-up retrieval and independent audit |
| Isolated paragraph classification | simple anchors | loses cross-paragraph explanation, consequence, and hegemony | disqualified as universal policy |
| Mandatory scene extraction | semantically meaningful units | additional paid/fallible dependency; excludes stories without valid scenes | disqualified as prerequisite |
| Adaptive whole-story/paragraph chunks | preserves global context when possible and scales | thresholds require pilot tuning | chosen |
| Additive three-point Novum score | easy to chart | permits compensation for failed cognitive validation or hegemony | theoretically disqualified |
| Knight pass/fail threshold | easy classification | threshold is not established by Knight | attribution error; disqualified |
| One sidecar | atomic references and simple promotion | requires single-writer discipline | chosen |
| Multiple promoted analysis files | independent file evolution | cross-file transactions and dangling IDs | defer unless later evidence justifies |

## Evaluation and Quality Gates

Evaluation must separate software correctness, extraction quality, theoretical
agreement, and operational cost. Every pilot reports:

- schema validity and explicit completion/failure rates;
- exact evidence-anchor validity;
- criterion-level precision, recall, F1, and confusion matrices against
  adjudicated human labels;
- candidate-novum identification and N/C/H agreement;
- evidence-span overlap or agreement;
- shared-versus-independent extraction recall delta;
- run-to-run stability on a predeclared subset;
- latency, input/output tokens, and measured cost per story and stage;
- human review time and a qualitative failure taxonomy; and
- results by positive, boundary, negative, story-length, and chunking strata.

For human annotation, report raw agreement and per-label confusion matrices
alongside a predeclared chance-corrected coefficient such as Krippendorff's
alpha. Do not choose thresholds after seeing results. Criterion-specific
quality gates must be registered before paid pilots and interpreted with
confidence intervals and label prevalence, especially for rare categories.

## Non-Goals

- Does not classify `science-fiction.json` as the authoritative genre record;
  `genre.json` retains that role.
- Does not invent a Knight genre threshold, probability, or weighted score.
- Does not reduce Suvin's novum to an additive checklist.
- Does not require or reimplement scene/sequel extraction.
- Does not require a full ERW run, graph database, or complete Story Logic
  representation.
- Does not change `lcats annotate`, `lcats promote`, or corpus contents during
  the pilots.
- Does not run paid models without a reviewed manifest, cost estimate, and
  explicit approval.
- Does not select or alter the Worldcon sample; Phase 3 consumes the manifest
  governed by `WI-GENRE-0004` unless the paper protocol is separately amended.
- Does not create workstreams or work items in this proposal PR.
- Does not settle a later supervised genre classifier that might consume these
  features; that would require a separate proposal and evaluation design.

## Implementation Plan

This is a large, multi-stage effort and should be delivered through a new
workstream after proposal adoption. Individual work items should be defined
under that workstream, not embedded as implementation authorization in this
proposal.

### Phase 1: Core technical deliverables and unit tests

1. Freeze `knight-seven-v1` and `suvin-novum-v1` rubric documents with
   primary-source citations, operational definitions, positive/negative
   examples, ambiguity rules, and `not_assessable` rules.
2. Implement typed evidence, Knight, Novum, provenance, and sidecar records.
3. Implement deterministic paragraph indexing, adaptive chunk planning,
   hashes, and exact-quotation alignment.
4. Implement backend-independent shared extraction and bounded theory-specific
   follow-up interfaces.
5. Implement strict Knight and Suvin output schemas plus deterministic Python
   scoring and semantic validation.
6. Implement checkpoint fingerprints, resume/rematerialization, explicit
   partial-failure records, and atomic single-writer publication.
7. Implement an experiment runner with `--dry-run`, deterministic manifest,
   cost estimation, resume support, and no corpus write path.
8. Add no-cost fixtures for clear SF, no-novum controls, supernatural
   contrasts, ambiguous cognitive validation, multiple-novum systems,
   cross-boundary evidence, duplicate overlap, malformed output, stale story
   hashes, and interrupted stages.

Required tests cover deterministic IDs/hashes/chunks, gap-free coverage,
quotation rejection/alignment, deterministic aggregation, all Knight
state/count combinations, the Novum N/C/H conjunction, partial success,
referential integrity, current-pointer validity, checkpoint reuse with zero
backend calls, atomic publication, schema-version rejection, and byte-stable
output when nondeterministic fields are fixed.

Phase 1 exits only when repository tests, format/lint, and `lrh validate` pass;
all fixture sidecars validate; every published evidence span is locatable; no
experiment code can write outside its output root; and the reviewed
rubric/sample/cost manifest exists before a paid call.

### Phase 2: Initial contrastive pilot (~30 stories)

Select a deterministic sample of approximately:

- 10 clear science-fiction positives spanning different Knight elements and
  novum types;
- 10 boundary/adjacent cases such as fantasy, cosmic horror, catastrophe,
  alternate history, gadget stories, or ambiguous cognitive validation; and
- 10 negative controls from realist, mystery, romance, humor, or adventure
  fiction.

Reuse suitable entries from the existing 24-story annotation feasibility
trial, adding SF and boundary cases required by the new rubrics. Two human
annotators independently label at least a stratified 12-story calibration
subset; preferably both label all 30. They work without seeing model results,
then adjudicate disagreements into a gold record.

Run the recommended pipeline on all 30 stories, independent Knight-only and
Suvin-only extraction on a stratified 8–10 story audit subset, repeated runs
on 5–10 stories, and both whole-story and chunked long-story modes.

Provisional Phase 2 gates are:

- at least 90% of stories complete both analyses, with every failure explicit;
- 100% valid evidence anchors and sidecars;
- no material shared-extraction recall loss on the independent audit subset,
  with the tolerance predeclared before the run (initial planning value: no
  more than five absolute percentage points);
- no systematic theory error such as fantasy repeatedly passing cognitive
  validation or incidental gadgets repeatedly passing hegemony;
- adequate human/model agreement for the paper's intended use, with weak
  criteria revised and rerun before scaling; and
- measured cost and throughput support Phase 3.

### Phase 3: Worldcon 100–200 story pilot

Consume the exact deterministic sample manifest produced for the Worldcon
study. Freeze rubrics, code commit, prompts, schemas, backend/model,
generation parameters, and chunk configuration. Write the reviewed manifest
and per-stage cost estimate before obtaining explicit approval for paid calls.

Run resumably with bounded concurrency and retries, quarantine invalid output,
human-review all failures and a predeclared stratified audit sample, and
compare results with Phase 2 by story length, source collection, genre,
publication era, and chunk mode. Publish experiment-local sidecar-shaped
records, machine-readable metrics, a failure taxonomy, measured cost report,
and a datasheet-style description of sample motivation, composition,
selection, limitations, and intended use.

Phase 3 exits only when:

- at least 95% complete after bounded retries, with the remainder explicitly
  failed or `not_assessable`;
- 100% of published outputs validate and match current story hashes;
- no material regression from Phase 2 exceeds predeclared confidence bounds;
- the audit supports the claims intended for the Worldcon paper;
- cost and throughput are measured, reproducible, and acceptable; and
- a decision record chooses integration, revision/repetition, or stop.

### Later full-corpus integration gate

Full-corpus integration is not a fourth pilot. It occurs only after Phase 3
passes and receives separate approval:

1. add the canonical `science-fiction.json` filename constant;
2. add sidecar validation to survey/promotion, including story-hash and
   current-pointer checks;
3. choose an opt-in `lcats annotate --science-fiction` stage or a separate
   `lcats analyze-science-fiction` command based on cost-control clarity;
4. implement sidecar-only tranche promotion or prove an alternative atomic
   promotion path safe for append-oriented records;
5. canary one collection, then several representative collections;
6. require a reviewed corpus manifest, estimated cost, pinned model/config,
   concurrency budget, rollback plan, and explicit paid-run approval;
7. append new analysis records when models or rubrics change and update
   `current` pointers only after validation; and
8. publish corpus-wide coverage, quality, and failure reports.

## Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| Shared extraction omits evidence needed by both theories | bounded theory-specific retrieval; independent extraction audit subset; block scale-up on material recall loss |
| LLM rationales substitute for textual evidence | require exact anchors; reject unlocatable quotations; compute scores deterministically |
| Knight count is mistaken for a genre probability | make the profile authoritative; label the count interval descriptively; prohibit a Knight-attributed threshold |
| Suvin's theory is weakened into a checklist | enforce the N/C/H conjunction and separate estrangement consequences |
| Historical or reader norms are under-specified | version rubric guidance; allow ambiguity/not-assessable; record assumptions and human adjudication |
| Chunking changes judgments | version chunk plans; include whole-story/chunk comparisons; analyze by chunk mode |
| Scene or ERW failures block analysis | keep both as optional adapters, never prerequisites |
| Sidecar append loses concurrent updates | one orchestrator per story; atomic whole-file rewrite; add optimistic concurrency only if production use requires it |
| Pilot results leak into corpus prematurely | experiment runner has no `data/` or `corpora/` write path; separate integration approval |
| Model or prompt drift breaks reproducibility | fingerprint every effective input and retain append-only analysis history |
| Paid run exceeds budget | dry-run estimates, per-stage checkpoints, bounded retries, explicit approval gates |

## Open Questions

- What exact primary-edition wording and page references will govern
  `knight-seven-v1`?
- What criterion-specific agreement and accuracy thresholds match the exact
  Worldcon paper claims? These must be registered before the pilot results are
  observed.
- Should ERW evidence be adapted in Phase 1 as an optional input, or deferred
  until the independent pipeline has a clean baseline?
- Should the later production entry point be an opt-in `annotate` stage or a
  dedicated command? Phase 3 cost/operational evidence should decide.
- Does external consumption justify a published JSON Schema at integration,
  or is the Python structural/semantic validator sufficient?

## Cross-References

- Canonical principles: `lcats/project/design/design.md`
- Storyworld/genre reconciliation:
  `lcats/project/design/event-role-world-genre-target-reconciliation.md`
- ERW evidence and SF-tag substrate:
  `lcats/project/design/proposals/adopted/lcats-event-role-world-extractor/00_proposal.md`
- Checkpointing:
  `lcats/project/design/proposals/adopted/lcats-pipeline-checkpointing/00_proposal.md`
- Bucket layout:
  `lcats/project/design/proposals/adopted/lcats-story-bucket-layout/00_proposal.md`
- Fast-path sidecar annotation:
  `lcats/project/design/proposals/adopted/worldcon-fast-path-annotation/00_proposal.md`
- Append-only genre evidence:
  `lcats/project/design/proposals/proposed/genre-evidence-sidecars/00_proposal.md`
- Worldcon sample work:
  `lcats/project/work_items/proposed/WI-GENRE-0004.md`

## Sources Informing the Design

- Damon Knight, “What Is Science Fiction, Anyway?”, in *In Search of
  Wonder*, 3rd ed. The implementation must freeze the exact primary-edition
  wording before rubric version 1.
- Douglas Robillard, “Uncertain Futures: Damon Knight's Science Fiction”
  (1984), which summarizes Knight's seven elements and characterizes them as
  a mix rather than a numerical threshold.
- Darko Suvin, “Science Fiction and the Novum” (1977), especially the
  definition of a narratively hegemonic novum validated by cognitive logic
  and the discussion of totalizing deviation and estrangement.
- Ron Artstein and Massimo Poesio, “Inter-Coder Agreement for Computational
  Linguistics,” *Computational Linguistics* 34(4), 2008, for agreement measure
  assumptions and reporting.
- Timnit Gebru et al., “Datasheets for Datasets,” *Communications of the ACM*
  64(12), 2021, for documenting sample motivation, composition, collection,
  limitations, and intended use.
- NIST AI Risk Management Framework 1.0 and Generative AI Profile for
  lifecycle test/evaluation/verification/validation, documentation, and human
  oversight practices.
