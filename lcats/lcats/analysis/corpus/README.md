# Corpus Analysis Subsystem

## 1. Overview

The corpus analysis subsystem is LCATS's text-quality and artifact-detection layer
for raw story corpora.

It exists to answer a practical question before deeper narrative reasoning begins:

- Is this story text structurally usable?
- If not, where are the likely defects?
- Which issues can be repaired safely, and which require human judgment?

Within LCATS, this subsystem sits between corpus ingestion and higher-level
narrative/case reasoning. It produces inspectable findings and conservative repair
proposals without mutating source text by default.

In short, corpus analysis is designed to make downstream narrative intelligence
more reliable by making preprocessing explicit, reviewable, and deterministic.

## 2. Design Principles

The subsystem follows four core design rules:

- **Non-destructive by default**
  - Detection and proposal generation never require rewriting source corpora.
  - Repair logic is expressed as suggestions/operations first.

- **Auditability and explainability**
  - Findings include spans, evidence, and human-readable rationale fields.
  - Review decisions are explicit and serializable.

- **Deterministic transformations**
  - Detector execution and repair suggestion ordering are deterministic.
  - Span operations are sorted and overlap-checked before apply.

- **Separation of responsibilities**
  - Detection finds suspicious patterns.
  - Classification assigns likely-good/repairable/review-needed status.
  - Transformation represents proposed edits as explicit span operations.
  - Review/override captures human decisions without hidden side effects.

## 3. System Architecture

The architecture is intentionally modular and centered around explicit data
contracts.

### 3.1 Classification system

Two related paths are implemented:

- **Detector-oriented QA findings**
  - Protocol + finding model: `models.Detector`, `models.Finding`.
  - Orchestration: `qa.run_detectors(...)` with a default detector stack.
  - Detector families:
    - Unicode/special character anomalies (`detectors/unicode.py`)
    - Boundary contamination near file start/end (`detectors/boundary.py`)
    - Structural artifacts such as chapter headings/ToC remnants
      (`detectors/structural.py`)

- **Special-character classification for repair pipeline**
  - `specials.classify_character(...)` assigns one of:
    - `likely_good`
    - `likely_repairable`
    - `review_needed`
  - Classification includes evidence strings describing why a character was
    bucketed.

### 3.2 Repair proposal system

Repair generation is conservative and rule-based:

- `repairs.DEFAULT_REPAIR_RULES` defines known high-confidence mojibake fixes.
- `repairs.suggest_repairs(...)` maps `likely_repairable` findings to
  `RepairSuggestion` objects when an unambiguous source span is identified.
- Duplicate or ambiguous spans are intentionally ignored rather than guessed.

### 3.3 Span operation model

Proposed edits are represented as canonical, deterministic span operations:

- `span_ops.SpanOperation` captures operation identity, type, start/end offsets,
  original text, replacement text, and provenance metadata.
- `span_ops.SpanOperationProvenance` preserves rule id, source, evidence,
  rationale, confidence, and finding offset for review traceability.
- `span_ops.from_repair_suggestions(...)` and
  `repairs.suggestions_to_canonical_span_operations(...)` provide deterministic
  conversion from repair proposals into canonical operations.
- `span_ops.validate_operation_set(...)` enforces valid ranges, explicit
  operation semantics, deterministic ordering, and non-overlapping spans.
- `span_ops.serialize_operations(...)` / `deserialize_operations(...)` provide
  stable JSON interchange for downstream review and application stages.

### 3.4 Review / override system

Human decision support is library-first and data-structured:

- `ReviewDecisionStore` stores:
  - `repair_decisions` (`approved`, `rejected`, `unresolved`)
  - `allowed_special_cases` for recurring expected special characters
- Span-operation review models store one decision per span operation with
  `pending`, `approved`, `rejected`, and `overridden` states.
- Overrides preserve the reviewed operation and reviewer-specified replacement
  operation plus required rationale.
- Review application utilities:
  - `apply_review_to_specials(...)` suppresses findings covered by allowed cases.
  - `apply_review_to_repairs(...)` partitions suggestions into approved/rejected/
    unresolved groups.
  - `operation_for_application(...)` returns approved operations or override
    replacements while rejecting pending/rejected decisions.
- Approved application is handled by `application.apply_reviewed_operations(...)`,
  which audits every considered decision, applies only `approved` and
  `overridden` operations, skips `pending`/`rejected` decisions, validates spans
  and overlaps before transformation, and returns transformed text separately
  from the original input.
- Decisions support deterministic JSON-serializable payloads through `to_dict()` /
  `from_dict()` and serialization helpers.

## 4. Data Flow

The current end-to-end flow is:

1. **Raw corpus input**
   - Text is read from corpus/story sources by analysis CLI and processing
     utilities.

2. **Detection**
   - Detector stack scans text for boundary, structural, and unicode anomalies.

3. **Classification**
   - Special-character findings are classified into likely-good,
     likely-repairable, or review-needed buckets with evidence.

4. **Repair proposal generation**
   - Only likely-repairable findings that match known conservative rules and
     unique spans become `RepairSuggestion` records.

5. **Span operations**
   - Suggestions are translated into canonical span operations for later review
     and application.

6. **Human review**
   - Review decisions can suppress expected findings and group repair proposals
     by approval state.

7. **Approved application**
   - Reviewed span operations are applied only after eligibility filtering.
   - Deterministic ordering follows canonical span-operation sort semantics.
   - Conflicts, invalid spans, and source-text mismatches fail without partial
     output, preserving the original text in the result.

8. **Future persistence**
   - Decision models are serializable today; first-class persisted review stores
     and workflow tooling are planned but not yet integrated as a complete
     product workflow.

## 5. Current Capabilities (Implemented)

Implemented today:

- Deterministic detector orchestration with a default suite of boundary,
  structural, and unicode checks.
- Structured finding model (`kind`, `severity`, `span`, `message`, `evidence`).
- Special-character reporting with classification and evidence annotations.
- Conservative mojibake repair-rule mapping for known broken punctuation
  sequences.
- Repair suggestions with stable span references and rationale metadata.
- Canonical span operation conversion with deterministic ordering semantics.
- Span-set validation with explicit overlap and structural checks.
- Human review decision model for repairs, allowed special cases, and canonical
  span operations.
- Decision-aware suppression, grouped reviewed repair outputs, and
  application-eligibility helpers for span operation reviews.
- Non-destructive approved application from review decisions to transformed text,
  including structured reports for considered, applied, skipped, and failed
  operations.
- Deterministic JSON-serializable review decision payload support (`to_dict`/
  `from_dict` plus serialization helpers).

## 6. Planned Features (Near-term Roadmap)

Planned near-term enhancements:

- First-class persistence conventions for review decisions and application
  outputs (e.g., standard
  on-disk location and lifecycle in corpus workflows).
- Tighter CLI integration for loading/applying decision stores during survey and
  repair reporting flows.
- Expanded conservative repair rule coverage where precision can be maintained.
- Stronger reporting ergonomics for reviewer handoff (clear unresolved queues,
  rule-level summaries, and artifact outputs).

## 7. Not Yet Implemented / Intentionally Deferred

The following are explicitly not implemented in the current subsystem:

- **Automatic in-place corpus rewriting as a default behavior**
  - Current design prioritizes proposal generation and controlled application.

- **Interactive review UI/editor experience**
  - Review is currently library/data-model driven, not UI-driven.

- **Comprehensive persistence workflow productization**
  - Serialization exists, but full persistence orchestration is still pending.

- **Learning-based/opaque repair generation**
  - Repair logic remains deterministic and rule-based; no probabilistic model is
    used.

- **Broad auto-correction beyond high-confidence rules**
  - Ambiguous or low-confidence transformations are intentionally deferred to
    human review paths.

## 8. Relationship to Future LCATS Goals

LCATS aims to support narrative intelligence, case-based reasoning, and
inspectable retrieval pipelines. Corpus analysis is foundational to that goal:

- It improves narrative signal quality before scene/sequence/case reasoning.
- It provides transparent provenance for preprocessing decisions.
- It supports reproducible ingestion so retrieval and adaptation stages can rely
  on stable, explainable input text.

As LCATS evolves toward richer narrative reasoning workflows, this subsystem is
intended to remain the conservative gatekeeper: detect clearly, propose safely,
and make human overrides explicit.

## 9. Story Assessment (`lcats assess`)

`lcats assess` is the LLM-powered curation layer that sits on top of the
detector pipeline. It calls the Claude API with a structured tool schema,
runs pre-flight QA via `run_preflight`, and returns an `AssessmentResult`
with verdict, genre detection, and quality annotations.

### Modes

| Mode | Command | When to use |
|---|---|---|
| Detect | `lcats assess <files> --format human` | Unknown/mixed corpus — model identifies genre independently |
| Lens | `lcats assess <files> --genre horror --format human` | Curation run — model detects genre then evaluates the claimed genre |

Both modes always return `detected_genre` and `detected_genre_confidence`.
Lens mode additionally returns `genre_verdict` in `[confirmed, disputed, wrong]`
(detect mode sets it to `detected`).

### Manual prompt validation

Before running a full corpus assessment with new or modified system prompts,
spot-check on 2–3 representative stories per mode:

```bash
# Detect mode — pick one story you know well
lcats assess data/path/to/story.json --format human

# Lens mode — same story with its expected genre
lcats assess data/path/to/story.json --genre "science fiction" --format human
```

**What to verify:**

- `detected_genre` matches your expectation for the story.
- `detected_genre_confidence` is high (≥0.8) for clear cases and lower for
  genuinely borderline ones.
- `genre_verdict` in lens mode is `confirmed` for a clear match, `disputed`
  for a borderline match, `wrong` for a clear mismatch.
- `verdict` (`include`/`exclude`/`review`) aligns with your curation judgment.
  In lens mode: `disputed` should produce `review`, not `include`.
- `summary` accurately describes the story in one or two sentences.
- `issues` lists any pre-flight QA findings you would also flag by hand.

A good spot-check set includes: one story that clearly belongs to the target
genre, one that belongs to a different target genre, and one that is
borderline or mixed. If the model misclassifies the clear case or returns
implausible confidence scores, the system prompt needs adjustment before a
bulk run.

### Dry run

Use `--dry-run` to verify file discovery and pre-flight QA without making
API calls:

```bash
lcats assess data/ --dry-run                     # detect mode
lcats assess data/ --genre western --dry-run     # lens mode
```
