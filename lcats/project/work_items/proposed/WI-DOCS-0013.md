---
id: WI-DOCS-0013
title: Fix accuracy issues in repo-root README.md and lcats/README.md
type: deliverable
status: proposed
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap: []
related_workstreams:
  - WS-DOCS
related_design: []
depends_on: []
blocked_by: []
blocked: false
blocked_reason: null
resolution: null
expected_actions:
  - edit_file
  - write_docs
forbidden_actions:
  - force_push
  - delete_branch
  - implement_wi_docs_0014
  - implement_wi_docs_0015
  - overhaul_unrelated_sections
acceptance:
  - "/README.md's CLI command table lists all 10 implemented commands (help, info, gather, inspect, display, survey, assess, stats, repair-specials, meta register) plus the 3 placeholders (index, advise, eval), 13 total, matching lcats/docs/reference/cli-status.md"
  - "/README.md's LLM Integration section mentions both Anthropic and OpenAI backends"
  - "lcats/README.md's Requirements section states an unambiguous Python version and does not reference installing pytest via conda"
  - "project/executions/README.md no longer references scripts/prompts/record-execution as if it exists, or explicitly notes it is intentionally deferred"
  - "lrh validate reports 0 errors"
required_evidence:
  - manual_review
  - lrh_validate
artifacts_expected:
  - README.md
  - lcats/README.md
  - lcats/project/executions/README.md
---

# Work Item: WI-DOCS-0013

## Summary
Fix four accuracy issues flagged by the 2026-07-07 docs audit (Phase 2b): the repo-root README's
stale CLI command table and OpenAI-only LLM description, `lcats/README.md`'s stale Python-version/
pytest wording, and `project/executions/README.md`'s reference to a nonexistent helper script.

## Problem / Context
The 2026-07-07 docs audit (`project/audits/docs/2026-07-07-docs-audit.md`, "Accuracy findings")
found that the repo-root `README.md` undercounts the CLI surface by 6 of 13 commands and describes
LLM integration as OpenAI-only, even though an Anthropic backend has existed since `WI-LLM-0007`
closed. `lcats/README.md`'s Requirements section still says "Python > 3.6(ish)" and lists
installing `pytest` via conda, though `STYLE.md` Section 8 mandates `unittest` only and the
canonical test command is `scripts/test`. `project/executions/README.md` references a
`scripts/prompts/record-execution` helper that was never built; 12 execution records have been
maintained manually since without it. Phase 2a of this audit (navigation fixes) already landed in
PR #111; this item is Phase 2b (accuracy fixes), the next item in the `WS-DOCS` workstream.

## Scope
- Correct factual claims in `/README.md` (repo root) and `lcats/README.md` against current source
  (`lcats/lcats/cli.py`, `lcats/lcats/llm/`, `STYLE.md`).
- Note the deferred helper-script gap in `project/executions/README.md` rather than leaving it
  silently wrong.
- Do not touch any other documentation file — that is Phase 3 (`WI-DOCS-0014`).

## Required Changes
1. `/README.md` (repo root) — replace the "CLI Commands" table with all 13 commands from
   `lcats/docs/reference/cli-status.md` (10 implemented, 3 placeholder), preserving the
   implemented/placeholder distinction.
2. `/README.md` (repo root) — update the "LLM Integration" bullet list under Features to mention
   both Anthropic and OpenAI, not OpenAI alone.
3. `lcats/README.md` — reword the Requirements section: state the Python version requirement
   unambiguously (match `pyproject.toml`'s `requires-python = ">=3.6"` without the informal
   "(ish)"), and remove or replace the `conda install -c anaconda pytest` line so it doesn't
   contradict `STYLE.md`'s `unittest`-only framework.
4. `project/executions/README.md` — either remove the `scripts/prompts/record-execution`
   reference or add a one-line note that it is intentionally deferred and records are currently
   written manually.

## Non-Goals
- Do not extract Section 9 of the corpus README into `docs/how-to/` — that is `WI-DOCS-0014`
  (Phase 3).
- Do not add new reference docs (CLI flags, LLM-backend reference) — that is `WI-DOCS-0014`.
- Do not add tutorial content — that is `WI-DOCS-0015` (Phase 4).
- Do not rewrite sections of either README that are still accurate (Quick Start, Python API
  example, Project Structure, etc.).

## Acceptance Criteria
- `/README.md`'s CLI command table lists all 10 implemented commands plus the 3 placeholders
  (13 total), matching `lcats/docs/reference/cli-status.md`.
- `/README.md` mentions both Anthropic and OpenAI as supported LLM providers.
- `lcats/README.md`'s Requirements section has unambiguous Python-version wording and no longer
  instructs installing `pytest`.
- `project/executions/README.md` no longer misrepresents `scripts/prompts/record-execution` as
  present.
- `lrh validate` reports 0 errors.

## Validation
- `scripts/version tools`
- `lrh validate`

## Risk Notes
- `/README.md` is the GitHub-visible landing page; double-check the CLI table against
  `lcats <command> --help` at implementation time, not just against `cli-status.md`, in case the
  CLI surface changed again since the audit.
