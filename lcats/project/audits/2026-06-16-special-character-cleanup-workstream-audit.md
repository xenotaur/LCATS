# Special-character cleanup workstream audit — LCATS

- Prompt ID used: `PROMPT(AD_HOC:SPECIAL_CHARACTER_WORKSTREAM_AUDIT)[2026-06-16T00:00:00+00:00]`
- Prompt ID normalization: requested `LCATS-2026-06-16-special-character-workstream-audit`; normalized to the observed `PROMPT(AD_HOC:<REQUEST_NAME>)[timestamp]` convention used by existing prompt records.
- Audit date: 2026-06-16
- Scope: `project/`, `lcats/`, `lcats/lcats/`, `lcats/scripts/`, `lcats/tools/`, `lcats/tests/`, and related README/control-plane files.

## 1. Summary

This is a planning/audit PR for the release-oriented special-character cleanup. It does not rewrite corpus text or suppress findings.

The immediate goal is to reuse LCATS's existing corpus survey, special-character detection, repair proposal, span operation, and review-planning work rather than inventing a parallel cleanup system. LCATS already has several useful pieces; the release pass should connect them with a small correction ledger and targeted survey improvements.

## 2. Problem statement

`lcats survey --mode specials --no-progress` currently reports many suspicious characters in corpus story text. Some represent likely mojibake or encoding artifacts, including patterns such as `√©`, `√®`, `√∂`, `√≤`, `√º`, `√±`, `Ã©`, `Ã«`, `Ãª`, `Ã¶`, `Ã¯`, `Â¢`, `째` in temperature contexts, and leading `U+FEFF` before Gutenberg start markers.

The same survey can also surface characters that should not be blanket-fixed, including source typography and legitimate Unicode: `¶`, `✠`, `❦`, `·`, `●`, `○`, `■`, accented Latin text such as `é`, `ö`, `è`, `ë`, `ê`, `ï`, `ñ`, `ü`, `ò`, and symbols such as `°` and `¢` after repair.

Important distinction: the current specials TSV is occurrence-oriented and may report one suspicious character inside a larger damaged sequence. For example, a report row for `√` or `©` may really indicate the multi-character sequence `√©`, and a row for `Ã` may indicate a sequence such as `Ã©`. A release cleanup should therefore classify spans/sequences first, then decide whether to repair, allow, remove, or review them.

## 3. Relevant implemented code

### Survey and CLI entry points

- `lcats/lcats/cli.py` exposes `lcats survey` for corpus quality checks and `lcats repair-specials` for dry-run repair proposals. This is the public interface release work should extend instead of adding an unrelated command.
- `lcats/lcats/analysis/corpus/cli.py` implements `survey` parsing, `--mode specials`, allowlist/exclusion flags, output modes, progress controls, and the in-process special-character check. It defaults `--mode specials` to the `special-characters` check, adds default exclusions from the Unicode detector, and returns a nonzero exit code when findings remain.
- `lcats/lcats/analysis/corpus/output.py` converts special-character rows and detector findings into human/TSV output. Any new severity or category should preserve this row-oriented report path.
- `scripts/utils/extract_special_chars.py` delegates to the canonical specials CLI. Keep it as compatibility glue; do not put new cleanup logic there.
- `scripts/utils/corpora_quality_check.py` delegates to the canonical corpus survey command. It can be used by older workflows while release work focuses on `lcats survey`.

### Special-character classification and quality detectors

- `lcats/lcats/analysis/corpus/specials.py` is the direct implementation used by `lcats survey --mode specials`. It provides `AllowlistConfig`, per-character classification, contextual TSV rows, and mojibake-pattern evidence. It currently recognizes common `Ã`, `Â`, `â`, `ð`, and replacement-character patterns but does not cover the reported `√...` or `째` cases.
- `lcats/lcats/analysis/corpus/detectors/unicode.py` contains a detector-oriented model that already classifies multi-character mojibake sequences as `mojibake-sequence` with `severity="error"`, safe excluded characters, rare review characters, and default exclusions. This is the best existing model to reuse when upgrading survey classification from character rows to sequence-aware categories.
- `lcats/lcats/analysis/corpus/qa.py` orchestrates QA detectors and defaults to `special-characters` and `boundary-contamination`. It shows the existing path for combining special-character checks with other release-readiness checks.
- `lcats/lcats/analysis/corpus/models.py` defines structured findings with kind, severity, span, message, and evidence. New sequence classifications should prefer this structured shape where possible.

### Repair proposals, span operations, and review hooks

- `lcats/lcats/analysis/corpus/repairs.py` implements conservative, non-destructive repair suggestions for known mojibake fragments, stable dry-run text/JSONL reports, and application helpers over explicit spans. Its current default rules cover broken smart punctuation (`â€™`, `â€œ`, `â€\u009d`, `â€“`, `â€”`, `â€¦`) but not the newly observed `√...`, `Ã...` accented letters, `Â¢`, `째`, or `U+FEFF` cases.
- `lcats/lcats/analysis/corpus/repairs_cli.py` exposes dry-run repair proposal generation through `lcats repair-specials`. This can become the release-facing preview command for manifest-backed proposed fixes before any corpus mutation.
- `lcats/lcats/analysis/corpus/span_ops.py` defines canonical span operations and validation. It already supports deterministic ordering, provenance, and non-overlap checks, which are exactly the safeguards needed for automated or semi-automated corpus edits.
- `lcats/lcats/analysis/corpus/review.py` defines serializable review decisions, allowed special cases, and helpers for suppressing allowed findings or partitioning repairs into approved/rejected/unresolved groups. This should be reused for source-confirmed typography and ambiguous cases rather than replaced.
- `lcats/lcats/analysis/corpus/README.md` documents the subsystem's implemented/planned split, including special-character classification, repair suggestions, span operations, and human review decisions. It should remain the architectural reference for follow-up implementation PRs.

### Corpus ingestion, extraction, and boundary cleanup

- `lcats/lcats/gatherers/downloaders.py` handles HTTP/file loading and encoding fallback behavior. It is relevant because some artifacts likely originate at source download/decode time.
- `lcats/lcats/gettenberg/api.py`, `lcats/lcats/gettenberg/cache.py`, `lcats/lcats/gettenberg/headers.py`, and `lcats/lcats/gettenberg/metadata.py` are the Gutenberg fetch/cache/header layers. `headers.py` strips Gutenberg headers/footers from bytes; leading `U+FEFF` before start markers should be evaluated against this layer before applying downstream text-only fixes.
- `lcats/lcats/gatherers/extractors.py` extracts story text between Gutenberg HTML separator IDs and joins tags. It is relevant for deciding whether a special character is story content, boilerplate, or extraction residue.
- `lcats/lcats/gatherers/parser.py` contains title/author/transcriber detection and body-boundary logic. It already has transcriber-note detection tests; release cleanup should reuse those heuristics for `boilerplate_or_transcriber_note` decisions.
- Corpus-specific gatherers under `lcats/lcats/gatherers/*/gatherer.py` and conversion scripts under `lcats/lcats/gatherers/*/convert.rb` may be the source of existing JSON text. Do not change them broadly in the audit PR, but use them to trace recurrent artifacts before choosing repairs.
- `lcats/lcats/analysis/corpus/processing.py` can mirror JSON corpus processing into output directories without mutating source files. It is useful for dry-run before/after experiments and should be preferred over ad hoc one-off rewrite scripts.

### Tests already covering relevant behavior

- `lcats/tests/analysis_tests/specials_test.py` and `lcats/tests/analysis_tests/specials_cli_test.py` cover special-character extraction and CLI behavior.
- `lcats/tests/analysis_tests/repairs_test.py` and `lcats/tests/analysis_tests/repairs_cli_test.py` cover non-destructive repair proposal behavior.
- `lcats/tests/analysis_tests/span_ops_test.py` covers canonical span operation validation.
- `lcats/tests/analysis_tests/review_test.py` covers review decisions, allowlisted special cases, and grouping of reviewed repairs.
- `lcats/tests/analysis_tests/corpus_survey_test.py`, `lcats/tests/analysis_tests/corpus_surveyor_test.py`, and `lcats/tests/analysis_tests/corpus_package_test.py` cover survey/package behavior.
- `lcats/tests/gatherers_tests/parser_test.py`, `lcats/tests/gatherers_tests/downloaders_test.py`, and `lcats/tests/gatherers_tests/lovecraft_gatherer_test.py` cover source extraction, encoding fallback, transcriber-note detection, and Gutenberg boundary behavior.
- `lcats/tests/gettenberg_tests/*_test.py` covers Gutenberg API/cache/header/metadata behavior.
- `lcats/tests/utils_tests/extract_special_chars_test.py` and `lcats/tests/utils_tests/corpora_quality_check_test.py` verify legacy script delegation.

## 4. Relevant planned workstreams and docs

### Reuse now

- `project/work_items/resolved/WI-REPAIR-0001.md` records the implemented conservative repair engine. Reuse its rules-and-spans model; extend rule coverage only when cases are high-confidence.
- `project/work_items/active/WI-SPANOPS-0002.md` describes precise span operation primitives. Reuse for any deterministic fixer or manifest application.
- `project/work_items/active/WI-REVIEW-0003.md` describes human review and override decisions. Reuse for source-confirmed typography and ambiguous cases.
- `project/work_items/active/WI-APPLY-0005.md` describes safe deterministic application of approved operations. Reuse if follow-up PR B/D applies fixes; this audit PR should not implement application.
- `lcats/lcats/analysis/corpus/README.md` is the current corpus quality architecture reference and already defines conservative, reviewable, deterministic cleanup principles.

### Broader/future work

- `project/work_items/proposed/WI-PERSIST-0004.md` proposes persistence for corpus state, repair plans, and review outcomes. It should inform manifest schema, but the release cleanup should not wait for a full persistence system.
- `project/work_items/active/WI-META-0006.md` is metadata/control-plane related and not a direct blocker unless follow-up PRs formalize a new work item.
- `project/audits/docs/2026-05-26-docs-audit.md` and `project/prompts/PROMPT-AD_HOC-REQUEST_ORGANIZE_DOCS-2026-05-27-scaffold.md` are useful precedent for audit structure and prompt-record naming, but they are documentation-organization work rather than corpus cleanup implementation.
- `lcats/docs/reference/` is a documentation hub scaffold, but this PR adds the audit under `project/audits/` because the deliverable is control-plane planning rather than user-facing docs.

## 5. Gap analysis

### LCATS already has

- A public survey command with `--mode specials`, TSV/human output, allowlist and exclusion flags, default exclusions, and nonzero exit behavior when findings remain.
- Per-character classification with evidence and context.
- A detector model that already understands some multi-character mojibake sequences and severity levels.
- A conservative repair proposal engine with dry-run output.
- Canonical span operation structures with provenance and validation.
- Review-decision and allowlisted-special-case data models.
- Tests for survey, specials, repairs, span operations, review, gatherers, downloaders, and Gutenberg helpers.

### Missing for the near-term release cleanup

- A checked-in correction ledger/manifest for known special-character cases, including exact damaged text, intended text, classification, scope/path, rationale, confidence, and whether source confirmation exists.
- Sequence-aware classification for the current reported artifacts: `√©`, `√®`, `√∂`, `√≤`, `√º`, `√±`, `Ã©`, `Ã«`, `Ãª`, `Ã¶`, `Ã¯`, `Â¢`, `째`, and `U+FEFF` near Gutenberg markers.
- A clear release gate that separates hard errors (`mojibake_sequence`), warnings (`boilerplate_or_transcriber_note`, unresolved rare symbols), info (`source_confirmed_character`, `allowed_unicode`), and unresolved review queues.
- Tests that exercise these exact observed cases and prove that legitimate repaired Unicode is preserved.
- A small before/after audit workflow for capturing survey snapshots without committing large generated outputs.

### Defer to the larger review workflow

- Interactive review UI/editor workflows.
- Full persistence/history model for all review decisions.
- Learning-based or opaque repair generation.
- Broad corpus regeneration from source gatherers unless a specific artifact is proven to come from ingestion.
- Large-scale transcriber-note policy beyond the targeted release cleanup cases.

## 6. Recommended execution plan

### PR A: correction ledger / manifest for known special-character cases

Expected files/modules:
- Add a small manifest under a project-controlled location, for example `lcats/lcats/analysis/corpus/special_character_manifest.json` or `project/evidence/special-character-cleanup-manifest.md`.
- Update `lcats/lcats/analysis/corpus/README.md` only if needed to document the manifest's role.
- Add tests under `lcats/tests/analysis_tests/` if the manifest parser is code-backed.

Acceptance criteria:
- Every known damaged sequence has an entry with `classification`, `damaged_text`, `intended_text` when known, `rationale`, `confidence`, and `review_status`.
- Source-confirmed typography entries explicitly record why they are preserved.
- The manifest distinguishes corpus text, boilerplate, and transcriber-note contexts.
- No corpus text is changed.

### PR B: deterministic fixer or normalization tool using the manifest

Expected files/modules:
- Extend `lcats/lcats/analysis/corpus/repairs.py` to generate suggestions from the manifest.
- Extend `lcats/lcats/analysis/corpus/repairs_cli.py` / `lcats repair-specials` for manifest-backed dry runs.
- Reuse `lcats/lcats/analysis/corpus/span_ops.py` for operation validation and deterministic ordering.
- Add or update `lcats/tests/analysis_tests/repairs_test.py`, `repairs_cli_test.py`, and `span_ops_test.py`.

Acceptance criteria:
- The fixer defaults to dry-run/report mode.
- Only high-confidence `mojibake_sequence` manifest entries produce automatic replacement suggestions.
- Operations are span-validated, non-overlapping, deterministic, and auditable.
- Legitimate Unicode and source-confirmed typography do not produce replacement suggestions.

### PR C: survey improvements for release gating

Expected files/modules:
- Extend `lcats/lcats/analysis/corpus/specials.py` and/or align it with `lcats/lcats/analysis/corpus/detectors/unicode.py` so survey output reports sequence categories, not only component characters.
- Update `lcats/lcats/analysis/corpus/cli.py` and `lcats/lcats/analysis/corpus/output.py` only as needed to expose category/severity cleanly.
- Add tests in `lcats/tests/analysis_tests/specials_test.py`, `specials_cli_test.py`, and `corpus_survey_test.py`.

Acceptance criteria:
- `√...`, `Ã...`, `Â¢`, `째`, and `U+FEFF` marker cases are classified with stable categories and severities.
- Allowed/source-confirmed characters appear as info or are suppressed only through documented allow decisions.
- Remaining unknowns are easy to count and review from TSV output.
- `lcats survey --mode specials --no-progress` is usable as a release gate.

### PR D: targeted corpus cleanup and tests

Expected files/modules:
- Apply approved manifest-backed span operations to affected corpus JSON files only.
- Add regression fixtures/tests under `lcats/tests/analysis_tests/` and, if boundary or source extraction behavior changes, `lcats/tests/gatherers_tests/` or `lcats/tests/gettenberg_tests/`.
- Optionally add a compact evidence note under `project/evidence/` with before/after command summaries.

Acceptance criteria:
- Known mojibake sequences are removed from the corpus or explicitly classified/allowed.
- Legitimate source typography remains intact.
- Survey output has no release-blocking `mojibake_sequence` findings.
- Any remaining special characters are source-confirmed, allowed Unicode, boilerplate/transcriber-note decisions, or documented ambiguous cases.

## 7. Recommended classification model

Use lightweight categories that map cleanly to survey severity and release gates:

| Category | Meaning | Recommended severity/gate |
| --- | --- | --- |
| `mojibake_sequence` | Multi-character damaged encoding sequence with high-confidence intended text. | `error`; blocks release until repaired or explicitly rejected with rationale. |
| `source_confirmed_character` | Unusual typography confirmed in the source text, such as `¶` in a known source-confirmed line. | `info`; allowed when manifest/review rationale exists. |
| `allowed_unicode` | Legitimate Unicode in story text after repair or already correct, such as lexical Latin diacritics, `°`, or `¢`. | `info` or suppressed through documented allowlist; never auto-repaired. |
| `boilerplate_or_transcriber_note` | Finding belongs to Gutenberg boilerplate, start/end marker residue, or transcriber note rather than story content. | `warning` until removed or bounded by source/extraction policy; may block release if residue is in story body. |
| `ambiguous_needs_review` | Insufficient evidence for automatic repair or allow. | `warning`; does not get auto-fixed and should remain in a targeted review queue. |

Mapping principle: only `mojibake_sequence` with a high-confidence replacement should become an automatic repair proposal. `source_confirmed_character` and `allowed_unicode` preserve text. `boilerplate_or_transcriber_note` should usually be handled through extraction/boundary cleanup rather than character replacement. `ambiguous_needs_review` should feed the existing review model.

## 8. Testing and validation plan

Existing commands to run from the `lcats/` execution root:

```bash
scripts/test
scripts/lint
scripts/format --check
lcats survey --mode specials --no-progress
```

Existing targeted tests useful for follow-up PRs:

```bash
python -m unittest tests.analysis_tests.specials_test tests.analysis_tests.specials_cli_test
python -m unittest tests.analysis_tests.repairs_test tests.analysis_tests.repairs_cli_test
python -m unittest tests.analysis_tests.span_ops_test tests.analysis_tests.review_test
python -m unittest tests.analysis_tests.corpus_survey_test
python -m unittest tests.gatherers_tests.parser_test tests.gatherers_tests.downloaders_test
python -m unittest tests.gettenberg_tests.headers_test
```

Missing tests to add in follow-up PRs:

- Sequence-aware classification fixtures for `√©`, `√®`, `√∂`, `√≤`, `√º`, `√±`, `Ã©`, `Ã«`, `Ãª`, `Ã¶`, `Ã¯`, `Â¢`, `째`, and `U+FEFF` before Gutenberg markers.
- Preservation tests for legitimate `é`, `ö`, `è`, `ë`, `ê`, `ï`, `ñ`, `ü`, `ò`, `°`, `¢`, `¶`, `✠`, `❦`, `·`, `●`, `○`, and `■` where source-confirmed or allowed.
- Manifest parser/validator tests if a machine-readable correction ledger is added.
- Survey release-gate tests proving `mojibake_sequence` is `error`, while allowed/source-confirmed cases are `info` or suppressed only by documented review/allow decisions.
- Before/after survey snapshot workflow tests should be lightweight. Store command summaries or small fixtures, not large generated TSVs, unless project conventions change.

Recommended audit artifact workflow for follow-up cleanup PRs:

```bash
lcats survey --mode specials --no-progress --format tsv --output /tmp/lcats-specials-before.tsv
# run manifest-backed dry run or approved cleanup
lcats survey --mode specials --no-progress --format tsv --output /tmp/lcats-specials-after.tsv
```

Do not commit large snapshot files by default. Summarize counts by category/severity in PR bodies or compact `project/evidence/` notes.

## 9. README updates

No README updates are needed in this audit PR. `project/audits/` already exists and contains the prior documentation audit, so the new audit location follows the current convention without requiring a new index.

## 10. Execution record

The requested `scripts/prompts/record-execution` command is not present in this repository snapshot. The nearest observed convention is a lightweight prompt execution record under `project/prompts/`, so this PR adds a matching record:

- `project/prompts/PROMPT-AD_HOC-SPECIAL_CHARACTER_WORKSTREAM_AUDIT-2026-06-16.md`

## 11. Soft idempotence check

Before writing this audit, repository files were searched for this exact prompt ID and related special-character workstream/audit language. No exact prior execution record or audit for this prompt was found. Existing overlapping repair/review work is referenced above instead of duplicated.
