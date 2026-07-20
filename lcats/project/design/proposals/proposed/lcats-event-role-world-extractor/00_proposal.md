---
id: PROP-LCATS-EVENT-ROLE-WORLD-EXTRACTOR
type: design_proposal
status: proposed
implementation_status: not_started
implemented_by: []
evidence: []
---

# LCATS Event-Role-World extractor proposal

## Problem and motivation

Prior LCATS work already extracts provenance and evidence spans, narrative
scene segments, the labels `narrative_scene`, `dramatic_scene`,
`dramatic_sequel`, and `other`, GACD/ERAC fields, and basic story metadata. A
new LCATS/Worldcon Academic paper should not reimplement scene/sequel
extraction. It should use that segment layer as its substrate and extract
storyworld semantics that may distinguish science fiction from other genres.

The proposed new layer is a **Science-Fiction Event-Role-World extractor**.

## Goals

For every existing story segment, the design supports extraction of:

1. entities, participants, and aliases;
2. entity types and actant roles;
3. predicate events and semantic roles;
4. temporal and spatial anchors;
5. causal, enabling, preventing, temporal, motivational, and explanatory links;
6. speech acts and explanation discourse;
7. optional perspective, belief, uncertainty, and emotion hypotheses; and
8. science-fiction world-model tags: `technology`, `scientific_concept`,
   `experiment`, `alien_or_nonhuman_agent`, `machine_agency`,
   `future_or_alternate_setting`, `space_travel`,
   `time_travel_or_temporal_anomaly`, `cosmic_scale`, `anomaly_or_novum`,
   `ontological_rule`, and `technical_constraint`.

## Non-goals

This proposal does not:

- reimplement scene/sequel extraction;
- implement the extractor in LRH;
- choose the Worldcon paper's final statistical method;
- require a graph database in the first implementation;
- treat causal, belief, emotion, novum, or ontological-rule annotations as
  hard facts; or
- require full Story Logic extraction in the first version.

## Design principles

1. Reuse the existing segment and evidence substrate.
2. Span-ground every extracted claim.
3. Separate stable annotations from interpretive hypotheses.
4. Use a layered pipeline rather than one mega-prompt.
5. Prefer strict schemas and validation over unconstrained JSON.
6. Keep canonical artifacts human-readable and export analysis tables for
   digital-humanities and statistical work.
7. Defer graph databases and deep case-based-reasoning adaptation until the
   extracted data justifies them.

## High-level architecture

```text
Existing LCATS story JSON
        |
        v
Existing story metadata + segment extractor
        |
        v
EventRoleWorldProcessor
        |
        +--> SurfaceFeatureAnnotator
        |       tokens, lemmas, POS, morphology, dependency summaries
        |
        +--> EntityParticipantAnnotator
        |       mentions, aliases, canonical entities, entity types, actant roles
        |
        +--> EventRoleAnnotator
        |       predicates, event type, semantic roles, event evidence
        |
        +--> AnchorAnnotator
        |       temporal anchors, spatial anchors, scale markers
        |
        +--> RelationAnnotator
        |       causal, enabling, preventing, temporal, explanatory links
        |
        +--> DiscourseSFAnnotator
        |       speech acts, explanation discourse, SF world-model tags
        |
        +--> HypothesisAnnotator
        |       belief, perspective, emotion/appraisal, optional and low confidence
        |
        v
Validation + metrics + export
        |
        +--> per-story JSON
        +--> per-segment JSONL table
        +--> graph export
        +--> CSV/Parquet feature tables for paper analysis
```

Graph export is an interchange artifact, not a commitment to a graph database.

## Suggested downstream module layout

This is a future LCATS implementation sketch, not an LRH implementation
requirement:

```text
lcats/lcats/analysis/
  event_role_world/
    __init__.py
    schema.py
    prompts.py
    processor.py
    entity_extractor.py
    event_extractor.py
    relation_extractor.py
    sf_tags.py
    validators.py
    metrics.py
    exporters.py
```

## Core schema sketch

These are object responsibilities and key fields, not implementation schemas:

- **`EvidenceSpan`** grounds a claim with start and end character offsets,
  optional paragraph IDs, quoted text, and an evidence source such as story,
  segment, model pass, or external annotation.
- **`EntityMention`** identifies a surface mention with an ID, entity ID,
  mention text, evidence span, and optional mention form or grammatical role.
- **`Entity`** reconciles participants through an ID, canonical name, aliases,
  mentions, entity type, actant roles, and confidence.
- **`SemanticRole`** binds an event to an entity or literal filler with a
  controlled role, evidence, and confidence.
- **`Event`** represents a salient predicate with an ID, predicate text,
  optional lemma, event type, semantic roles, temporal and spatial anchor IDs,
  evidence, modality, and confidence.
- **`TemporalAnchor`** records normalized or textual time, granularity,
  relative/absolute status, scale, evidence, and confidence.
- **`SpatialAnchor`** records a place or spatial frame, optional linked entity,
  containment or scale, evidence, and confidence.
- **`EventRelation`** links source and target event IDs with a controlled
  relation type, evidence, certainty (`explicit`, `strongly_implied`, or
  `weakly_inferred`), and confidence.
- **`SpeechAct`** links speaker, addressees, utterance evidence, act type, and
  optionally an event or explanation.
- **`ExplanationDiscourse`** marks explanatory passages with topic, mechanism
  or rationale type, linked entities/events, evidence, and confidence.
- **`SFWorldModelTag`** uses a controlled tag, linked supporting entity/event
  IDs where possible, evidence, confidence, and extractive/hypothesis status.
- **`Hypothesis`** optionally records belief, uncertainty, perspective, or
  emotion/appraisal with subject, proposition or target, evidence, confidence,
  and an explicit hypothesis marker.
- **`SegmentWorldAnnotation`** collects a segment ID, surface summary,
  entities/mentions, events, anchors, relations, discourse, SF tags,
  hypotheses, validation results, and extractor provenance.
- **`StoryWorldAnnotation`** contains story metadata, ordered segment
  annotations, story-level entity and alias reconciliation, cross-segment
  relations, validation report references, and export provenance.

Interpretive `anomaly_or_novum` and `ontological_rule` tags are hypotheses
unless the text states them explicitly. The same fact/hypothesis distinction
applies to every interpretive annotation.

## Recommended staged pipeline

1. **Input contract:** accept story JSON plus existing segments.
2. **Surface feature pass:** derive lexical, syntactic, and morphological
   features.
3. **Entity participant pass:** extract salient entities, aliases, entity
   types, and actant roles.
4. **Event-role pass:** extract salient events, predicates, semantic roles, and
   modalities.
5. **Anchor pass:** extract temporal anchors, spatial anchors, and scale.
6. **Relation pass:** extract causal, enabling, preventing, temporal,
   motivational, and explanatory links.
7. **Discourse/SF tag pass:** extract speech acts, explanations, and SF
   world-model tags.
8. **Optional hypothesis pass:** propose belief, uncertainty, perspective, and
   emotion/appraisal annotations.
9. **Validation and export:** emit canonical JSON artifacts and derived tables
   for analysis.

Each pass consumes validated outputs from earlier passes and retains its own
provenance. Story-level reconciliation follows segment-based extraction to
resolve aliases and cross-segment references without losing segment evidence.

## Low-level choices and tradeoffs

| Decision | Options and tradeoff | Recommendation |
| --- | --- | --- |
| Extraction strategy | LLM-only is flexible but less reproducible; NLP-first plus LLM normalization makes surface evidence inspectable; a Text2Story-style adapter provides a useful comparison but adds integration cost. | Use inspectable NLP features plus constrained normalization where useful. Treat Text2Story-style extraction as a reference or baseline, not an immediate dependency. |
| Context unit | Per-segment extraction is bounded and evidence-friendly; whole-story extraction improves global coherence but increases cost and drift; mixed extraction separates local evidence from reconciliation. | Extract by segment, then reconcile at story level. |
| Contract | JSON-only prototypes are fast but permit drift; strict schemas constrain evolution and enable validation. | Use strict schemas and validation as soon as practical. |
| Persistence | JSON/JSONL/CSV/Parquet are portable and analysis-friendly; SQLite helps querying; graph databases enable traversal but add operational and modeling costs. | Keep JSON canonical and JSONL/CSV/Parquet derived; defer graph databases. |
| Causality | Explicit-only links have high precision but low recall; adding strongly implied links improves coverage; weak inference is most speculative. | Include explicit and strongly implied links in the main layer and store weak inference separately as hypotheses. |

## Validation and metrics

### Artifact validation

- All entity, event, and relation IDs resolve.
- Every evidence span aligns to segment or story text.
- Causal links include evidence and certainty.
- SF tags include evidence and, where possible, linked entity/event IDs.
- Inferred claims are marked `inferred` or `hypothesis`.
- Exports are deterministic for the same validated input and configuration.
- Validation reports are retained with extracted artifacts.

### Candidate paper-facing metrics

- entity-type distributions by genre;
- nonhuman, machine, institution, and environment actants per 1,000 words;
- event-type and semantic-role distributions;
- instrumentality and technical-operation rates;
- temporal and spatial scale distributions;
- causal and explanatory link density;
- explanation discourse per 1,000 words;
- SF world-model tag counts; and
- technology or scientific concepts appearing as agent, instrument, or cause.

Metrics must report relevant denominators, extraction versions, and validation
coverage so genre comparisons remain auditable.

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| LLM-hallucinated causal links | Require aligned evidence, certainty, and confidence; compare against an explicit-link baseline. |
| Over-tagging SF categories | Use a small controlled inventory, grounded examples, and stratified human review. |
| Poor coreference or alias handling in older literary prose | Preserve mentions, reconcile at story level, and evaluate against a sampled alias baseline. |
| Ontology and schema sprawl | Version a minimal inventory and require evidence before adding fields or values. |
| Graph-extraction overreach | Keep JSON canonical, validate IDs first, and defer graph-database adoption. |
| Confusing interpretive hypotheses with extractive facts | Separate hypothesis fields, certainty, and confidence; exclude optional hypotheses from primary quantitative claims unless validated. |
| Duplicating prior scene/sequel work | Make existing segments the input contract and retain the stated non-goals. |

Lexical and segment-only baselines should accompany evaluation. A stratified
sample across genres, eras, and extraction-confidence bands should receive
human review.

## Resulting scientific claim

Compared with mystery, romance, and adventure, public-domain science fiction
may show distinctive patterns in nonhuman and technological actants, event
roles involving instruments and technical constraints, larger temporal and
spatial scale shifts, denser mechanistic causal links, and more scientific or
technical explanation discourse.

The extractor must be designed to test this claim, not assume it.

