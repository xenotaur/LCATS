---
execution_id: 2026_08_22_05_03_03_WS_GENRE_EVIDENCE_SIDECARS_FOLLOWON_WIS_REVIEW
prompt_id: PROMPT(AD_HOC:WS_GENRE_EVIDENCE_SIDECARS_FOLLOWON_WIS_REVIEW)[2026-08-22T05:02:23+00:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_08_22_05_12_46_WS_GENRE_EVIDENCE_SIDECARS_FOLLOWON_WIS_CLOSEOUT
pr: https://github.com/xenotaur/LCATS/pull/348
commit: 849e00c3e9c17a19fcbc8173db0f3c189ab8463a
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/348
session_transcript: claude-app:6a2dbae2-adca-4a2a-92fe-2e95d3b2a4e0
created_at: 2026-08-22T05:03:03+00:00
---

# Summary

Address the 6 automatic first-push review comments on PR #348
(Copilot + Codex, both real, all valid) - adding WI-GENRE-0075/0076/0077
and registering them in WS-GENRE-EVIDENCE-SIDECARS.md. `rerun_of` left
blank per the backfill-path convention (no primary record exists yet for
this PR).

# Result

Fetched via `lrh request review_response`: 2 Copilot findings, 4 Codex
findings, all triaged as present/valid/feasible and fixed:

1. **Copilot - inaccurate duplication-search evidence** (`WI-GENRE-0075`):
   the Duplication search claimed `promote.py` had only 3 functions when
   it has 6 (plus 4 dataclasses) - corrected to list the real function
   set, verified via a fresh `grep -n "^def \|^class "`.
2. **Copilot - stale "open question"** (`WS-GENRE-EVIDENCE-SIDECARS.md`):
   a bullet asking "what WI IDs should be minted" was immediately
   followed by the answer - removed, since the same information is
   already in the `## Proposed Work Items` section above it.
3. **Codex - missing CLI wiring scope** (`WI-GENRE-0075`): confirmed via
   direct read of `promote_cli.py` that `run()` unconditionally calls the
   wholesale `promote_collections()` path - added `promote_cli.py` to
   Scope/Required Changes/acceptance/`artifacts_expected` so the new mode
   is actually reachable via `lcats promote`, not just a library function.
4. **Codex - contradictory fresh-write acceptance criterion**
   (`WI-GENRE-0076`): confirmed via direct read of `_annotate_genre()`
   that its fresh-write path produces `result.to_dict()` (the legacy flat
   shape `is_legacy_flat_sidecar()`/`validate_sidecar()` itself rejects)
   - corrected the criterion so fresh writes must produce a valid
   `genre-sidecar-v1` record from the start; "unchanged" now scoped to
   the command's invocation/inputs, not its literal output shape.
5. **Codex - missing README v1-awareness** (`WI-GENRE-0076`): confirmed
   via direct read of `_write_readme()` that it only reads legacy
   top-level `detected_genre`/`detected_genre_confidence`/`verdict` keys
   - added a Required Change and acceptance criterion to update it for
   v1's nested `assessments[].result` shape.
6. **Codex - overclaimed "Done" status** (`WS-GENRE-EVIDENCE-SIDECARS.md`):
   confirmed via direct read of `genre_sidecar.is_legacy_flat_sidecar()`'s
   docstring (detection only) and `WI-GENRE-0003`'s own Non-Goals
   ("Do not implement production legacy flat-sidecar conversion") that
   marking legacy-sidecar *conversion* as "Done" was wrong - corrected to
   note detection-only is done, conversion itself is `WI-GENRE-0076`'s job.

No GitHub bot review was retriggered - both passes were the automatic
first-push reviews, reacted to passively per standing project policy.

# Validation

- `scripts/version tools` (from `lcats/`): realigned nothing this round
  (editable install and ruff/black pins both already correct).
- `scripts/format --check --diff`: 194 files unchanged.
- `scripts/lint`: all checks passed.
- `lrh validate`: 2 pre-existing, unrelated errors only (owner-field on
  `WI-PILOT-0057.md`); the 3 new/modified WI files carry only the
  standard `owner: unassigned` warnings every WI in this repo has.
- `git diff --check`: clean.
- Post-commit spot-check: `git show HEAD:.../WI-GENRE-0075.md | grep -c
  promote_cli.py` returned 5, confirming the fix content actually landed
  in the commit (not silently dropped by a pre-commit-hook stash, a
  recurring failure mode in this repo).

# Follow-up

- None beyond the primary backfill record's own follow-up (created at
  closeout time).
