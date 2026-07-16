---
resolution: "Implemented and merged in PR #124 (commit 35c8d88). Fixed the overbroad 'â.' mojibake pattern (classifier now requires UTF-8 continuation-byte adjacency); added the '째->°' override and a 48-codepoint corpus allowlist wired as CLI default; captured EV-0002 evidence. Simulated regeneration over all 1,971 stories yields zero mojibake findings."
blocked_reason: null
blocked: false
id: WI-RESIDUAL-0019
title: Review residual defects and regenerate a clean data/ tree
type: operation
status: resolved
priority: high
owner: unassigned
related_focus:
  - FOCUS-WORLDCON-2026
related_workstreams:
  - WS-SPECIALS-CLEANUP
related_design:
  - project/workstreams/proposed/WS-SPECIALS-CLEANUP.md
depends_on:
  - WI-RULES-0016
  - WI-NORMALIZE-0017
  - WI-OVERRIDES-0018
forbidden_actions:
  - rewrite_corpus_json_in_place
  - force_push
acceptance:
  - Every one of the measured residual defects has an explicit disposition — repaired by rule, covered by an override, or allowlisted with rationale
  - After cache-clear and full regeneration, lcats survey --mode specials over data/ reports zero unaddressed mojibake findings
  - Legitimate characters (é, æ, ñ, °, ¢, £, accented names) are allowlisted so they stop generating survey noise
required_evidence:
  - manual_review
  - validation_output
  - lrh_validate
artifacts_expected:
  - allowlist config file(s)
  - override entries
  - dated survey-output evidence artifact
---

# Work Item: WI-RESIDUAL-0019

## Summary
Run the finished repair pipeline over the corpus, human-review the residual findings at rule level, record decisions as allowlist/override entries, and regenerate `data/` until the specials survey is clean.

## Problem / Context
This is the execution pass that turns the WI-RULES-0016/0017/0018 machinery into a clean corpus. The 2026-07-09 scan already extracted the 35 residual contexts (nearly all unambiguous accented-character fixes; 2–3 judgment calls such as `Ângstrom`). Review is at rule/story level, not per-occurrence — expected effort is about an hour of human time. The earlier overbroad-exclusion problem is fixed here by seeding the allowlist (`specials.AllowlistConfig`, `lcats/lcats/analysis/corpus/specials.py`) with legitimate characters.

## Scope
- Dry-run repair + survey over freshly regenerated data/.
- Human disposition of every residual finding (repair rule, override, or allowlist).
- Final cache-clear, regeneration, and clean survey run captured as evidence.

## Required Changes
1. Run `lcats repair-specials` dry-run and `lcats survey --mode specials` over regenerated `data/`; collate findings.
2. Human review: approve rules, add override entries (WI-OVERRIDES-0018 format), extend the allowlist config for legitimate characters.
3. Clear cache, regenerate `data/`, re-run the survey; iterate until zero unaddressed findings.
4. Record the final survey output as evidence (e.g. under `project/evidence/` with a dated filename).

## Non-Goals
- Do not edit story JSON by hand — all fixes flow through rules, overrides, or allowlist.
- Do not touch the stale `corpora/` snapshot.
- Do not review non-mojibake issue classes (transcriber notes, missing quotations) — separate triage via lcats assess, outside this workstream.

## Acceptance Criteria
- Zero unaddressed mojibake findings on a fresh regeneration.
- Every disposition is traceable (rule id, override entry, or allowlist entry with rationale).
- Evidence artifact committed with a dated filename per control-plane convention.

## Validation
- `lcats survey --mode specials data/ --no-progress`
- `lcats repair-specials data/mass_quantities/*.json --format jsonl` (requires the story-JSON decoding extension from WI-RULES-0016; raw story files store defects as `\uXXXX` escapes, so raw-text scans are false negatives)
- `lrh validate`

## Risk Notes
- Regeneration re-downloads from Project Gutenberg; upstream file changes may shift findings between runs — record the regeneration date with the evidence.
- Human review is the bottleneck; keep the queue rule-level to avoid per-occurrence fatigue.
