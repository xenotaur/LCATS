---
resolution: null
blocked_reason: null
blocked: false
id: WI-RULES-0016
title: Replace dead repair rules with measured mojibake encoding families
type: deliverable
status: proposed
priority: high
owner: unassigned
related_focus:
  - FOCUS-WORLDCON-2026
related_workstreams:
  - WS-SPECIALS-CLEANUP
related_design:
  - project/workstreams/proposed/WS-SPECIALS-CLEANUP.md
  - project/audits/2026-06-16-special-character-cleanup-workstream-audit.md
depends_on: []
forbidden_actions:
  - rewrite_corpus_json_in_place
  - modify_ci_pipeline
acceptance:
  - A dry-run over decoded story bodies from the live data/ tree produces at least one repair proposal for each of the three measured families (Ã-form, Mac-Roman √-form, Â-form)
  - The six unmatched cp1252-form rules are removed or corrected with a test proving each replacement matches real corpus bytes
  - Tests in tests/analysis_tests/repairs_test.py include real sampled story contexts, not synthetic strings
required_evidence:
  - test_output
  - lrh_validate
artifacts_expected:
  - lcats/lcats/analysis/corpus/repairs.py
  - lcats/tests/analysis_tests/repairs_test.py
---

# Work Item: WI-RULES-0016

## Summary
Replace `DEFAULT_REPAIR_RULES` in `lcats/lcats/analysis/corpus/repairs.py` with conservative rules for the three mojibake encoding families actually measured in the corpus, tested against real story contexts.

## Problem / Context
The 2026-07-09 assessment found the six existing rules target a cp1252-decoded form (`â€™` with U+20AC) that occurs zero times in either `data/` or `corpora/` — the repair engine is a silent no-op. The live `data/` tree contains 35 single-character upstream defects in three families: `Ã©`-form (é as `Ã©`, ë as `Ã«`, ê as `Ãª`, ï as `Ã¯`, à as `Ã` + NBSP), Mac-Roman `√`-form (é as `√©`, ö as `√∂`, ò as `√≤`, ü as `√º`, ñ as `√±`, è as `√®`, æ as `√¶`), and `Â`-form (° as `Â°`, ¢ as `Â¢`). See WS-SPECIALS-CLEANUP Background for measurements.

## Scope
- Rewrite the rule table to cover the three measured families.
- Extend the `repair-specials` dry-run path to scan decoded story JSON bodies.
- Keep the conservative, non-destructive proposal semantics unchanged.
- Test each rule against byte-exact snippets sampled from real stories.

## Required Changes
1. Replace `DEFAULT_REPAIR_RULES` in `lcats/lcats/analysis/corpus/repairs.py` with rules per measured family, one rule id per source sequence.
2. Update `lcats/tests/analysis_tests/repairs_test.py` (and `repairs_cli_test.py` if affected) with real sampled contexts, e.g. `resumÃ©`, `blas√©`, `60Â°`, `Ragnar√∂k`, `se√±orita`.
3. Extend `lcats repair-specials` (`lcats/lcats/analysis/corpus/repairs_cli.py`) to detect story JSON inputs and scan the decoded `body` field instead of raw file text. Raw story files store non-ASCII as `\uXXXX` escapes because both gather write paths call `json.dump` without `ensure_ascii=False` (`lcats/lcats/gatherers/downloaders.py:247`, `lcats/lcats/gatherers/parser.py:955`), so scanning raw JSON text matches nothing.
4. Verify via dry-run (`lcats repair-specials`) over decoded `data/mass_quantities/` story bodies that proposals are produced for the 35 known defects.

## Non-Goals
- Do not apply repairs to stored corpus files — application is WI-NORMALIZE-0017.
- Do not add ambiguous rules (e.g. bare `Ã` without a following byte that pins the decoding); ambiguous cases go to WI-OVERRIDES-0018 or review.
- Do not add an ftfy dependency without a separate decision — rules stay explicit and auditable.

## Acceptance Criteria
- Dry-run over live `data/` yields proposals for all three families (currently zero).
- Dead cp1252-form rules removed/corrected, each replacement covered by a test using real corpus bytes.
- `scripts/test` passes; no behavior change to proposal semantics.

## Validation
- `scripts/lint`
- `scripts/test`
- `lcats repair-specials data/mass_quantities/*.json --format jsonl | head` (after the story-JSON decoding extension in Required Changes; against raw JSON text this reports zero proposals and is not valid evidence)
- `lrh validate`

## Risk Notes
- The same wrong-byte-assumption mistake could recur: every rule's `source_text` must be verified against actual corpus bytes, not typed from memory.
- Evidence must come from decoded story bodies: raw story JSON stores defects as `\uXXXX` escapes, so a zero-proposal dry-run over raw file text is a false negative, not a clean corpus.
- Over-broad rules risk corrupting legitimate text (e.g. genuine `Ã` in rare loanwords); prefer sequence-anchored rules.
