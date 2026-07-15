---
id: WS-DOCS
kind: planning_node
title: LCATS Documentation Completion (Docs Audit Phase 2b-4)
status: active
stage: planned
related_focus:
  - FOCUS-WORLDCON-2026
work_items:
  - WI-DOCS-0013
  - WI-DOCS-0014
  - WI-DOCS-0015
exit_criteria:
  - Repo-root README.md's CLI command table and LLM-provider description match current lcats/lcats/cli.py and lcats/lcats/llm/ (WI-DOCS-0013)
  - lcats/README.md's Requirements section matches STYLE.md's unittest-only testing framework and accurate Python version wording (WI-DOCS-0013)
  - docs/how-to/run-assess.md exists with Section 9 content extracted from the corpus README (WI-DOCS-0014)
  - docs/reference/cli-commands.md exists, verified against `lcats <command> --help` for every implemented command (WI-DOCS-0014)
  - docs/reference/llm-backend.md exists, derived from project/design/unified-llm-backend-design.md (WI-DOCS-0014)
  - docs/tutorials/quickstart.md exists and takes a new contributor from environment setup through a first successful `lcats survey` or `lcats assess --dry-run` run (WI-DOCS-0015)
---

# Workstream: LCATS Documentation Completion

## Purpose

Bring `lcats/docs/` and the repo-root `README.md` up to date with everything already implemented
in LCATS, so team collaborators can find accurate documentation for any shipped feature. This is
priority 3 of `FOCUS-WORLDCON-2026` (`project/focus/current_focus.md`): LCATS needs to be in a
clean, documented state for WorldCon 2026.

This workstream executes Phases 2b, 3, and 4 of the 2026-07-07 docs audit
(`project/audits/docs/2026-07-07-docs-audit.md`). Phase 1 (scaffold) and Phase 2a (navigation
fixes) already landed in PR #110 and PR #111.

## Work Items

| ID | Title | Status | Audit Phase |
|---|---|---|---|
| WI-DOCS-0013 | Fix accuracy issues in repo-root and lcats/README.md | proposed | Phase 2b |
| WI-DOCS-0014 | Normalize CLI, LLM-backend, and assess reference docs | proposed | Phase 3 |
| WI-DOCS-0015 | Add a quickstart tutorial | proposed | Phase 4 |

## Governing Audit

See `project/audits/docs/2026-07-07-docs-audit.md`, sections "Recommended phased PRs" (Phase 2b,
3, 4) and "Recommended target documentation structure". No formal `project/design/proposals/`
entry governs this workstream — the audit itself serves that role, since the scope is a
well-evidenced accuracy/coverage backlog rather than a new architectural decision.

## Notes

- `WI-DOCS-0013` has no dependencies and can start immediately.
- `WI-DOCS-0014` should follow `WI-DOCS-0013` (Section 3's reference docs should describe
  already-accurate source material).
- `WI-DOCS-0015` should follow `WI-DOCS-0013` and `WI-DOCS-0014` — the audit recommends the
  tutorial reuse content "already proven correct" by the earlier phases.
