---
id: WI-DOCS-0014
title: Normalize CLI, LLM-backend, and assess reference docs
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
related_design:
  - project/design/unified-llm-backend-design.md
depends_on:
  - WI-DOCS-0013
blocked_by: []
blocked: false
blocked_reason: null
resolution: null
expected_actions:
  - create_file
  - edit_file
  - write_docs
forbidden_actions:
  - force_push
  - delete_branch
  - implement_wi_docs_0015
  - rewrite_unrelated_docs
acceptance:
  - "docs/how-to/run-assess.md exists with Section 9 content extracted from the corpus README, and Section 9 is replaced with a short pointer to it"
  - "docs/index.md's How-to guides link for lcats assess points at docs/how-to/run-assess.md, not the corpus-README anchor"
  - "docs/reference/cli-commands.md exists, documenting flags/arguments for all 13 lcats subcommands, verified against lcats <command> --help"
  - "docs/reference/llm-backend.md exists, documenting the LLMBackend Protocol and its Anthropic/OpenAI/Fake providers, derived from project/design/unified-llm-backend-design.md"
  - "docs/reference/README.md links both new reference pages"
  - "lrh validate reports 0 errors"
required_evidence:
  - manual_review
  - lrh_validate
artifacts_expected:
  - lcats/docs/how-to/run-assess.md
  - lcats/docs/index.md
  - lcats/docs/reference/cli-commands.md
  - lcats/docs/reference/llm-backend.md
  - lcats/docs/reference/README.md
  - lcats/lcats/analysis/corpus/README.md
---

# Work Item: WI-DOCS-0014

## Summary
Normalize LCATS's reference documentation: extract the `lcats assess` how-to content into its own
page, and add reference docs for the CLI's per-command flags and the `LLMBackend` abstraction —
Phase 3 of the 2026-07-07 docs audit.

## Problem / Context
Phase 2a (PR #111) linked `lcats assess` how-to content from `docs/index.md`, but left it living
inside Section 9 of `lcats/lcats/analysis/corpus/README.md` — an Explanation-dominant document —
as an interim measure "pending Phase 3 extraction" (per the audit). Separately, the audit found no
reference doc for individual CLI command flags (only the implemented/placeholder status matrix in
`docs/reference/cli-status.md`), and no reference doc for the `LLMBackend` Protocol delivered by
`WORKSTREAM-LLM-BACKEND`, despite `project/design/unified-llm-backend-design.md` already
describing its design. This item depends on `WI-DOCS-0013` landing first so the reference docs
describe already-accurate source material.

## Scope
- Move (not rewrite) the `lcats assess` how-to content out of the corpus README into
  `docs/how-to/`.
- Add two new reference pages: CLI command flags, and the `LLMBackend` abstraction.
- Do not touch the tutorial gap (`WI-DOCS-0015`) or re-run the Phase 2b accuracy fixes.

## Required Changes
1. Create `lcats/docs/how-to/run-assess.md` containing the content currently in Section 9 of
   `lcats/lcats/analysis/corpus/README.md` (modes, manual prompt validation, dry run) — copy and
   link, not rewrite, per the audit's Risks and Cautions note that this content was carefully
   reviewed.
2. Replace Section 9 of `lcats/lcats/analysis/corpus/README.md` with a one-line pointer to the new
   how-to page.
3. Update `docs/index.md`'s How-to guides entry for `lcats assess` to link
   `how-to/run-assess.md` instead of the corpus-README anchor.
4. Create `lcats/docs/reference/cli-commands.md`: run `lcats <command> --help` for all 13
   subcommands (`help`, `info`, `gather`, `inspect`, `display`, `survey`, `assess`, `stats`,
   `repair-specials`, `meta register`, `index`, `advise`, `eval`) and document flags/arguments for
   each, verified against actual `--help` output (not assumed from source).
5. Create `lcats/docs/reference/llm-backend.md`: document the `LLMBackend` Protocol and its
   `AnthropicBackend`/`OpenAIBackend`/`FakeBackend` implementations, derived from
   `project/design/unified-llm-backend-design.md`.
6. Link both new reference pages from `lcats/docs/reference/README.md`.

## Non-Goals
- Do not add tutorial content — that is `WI-DOCS-0015` (Phase 4).
- Do not redo any Phase 2b accuracy fix — that is `WI-DOCS-0013`.
- Do not rewrite Sections 1–8 of the corpus README (the Explanation content) — only Section 9
  moves.
- Do not add a full worked example beyond what already exists in Section 9's content.

## Acceptance Criteria
- `docs/how-to/run-assess.md` exists with the extracted content; Section 9 is a pointer, not a
  duplicate.
- `docs/index.md` links the new how-to page, not the old anchor.
- `docs/reference/cli-commands.md` exists and covers all 13 subcommands, verified against
  `--help` output.
- `docs/reference/llm-backend.md` exists and covers the `LLMBackend` Protocol and all three
  providers.
- `docs/reference/README.md` links both new pages.
- `lrh validate` reports 0 errors.

## Validation
- `scripts/version tools`
- `lrh validate`
- `lcats <command> --help` for each of the 13 subcommands, to verify `cli-commands.md` accuracy

## Dependencies / Order
Depends on `WI-DOCS-0013` landing first — the reference docs this item adds should describe
already-corrected source material (accurate README, correct provider description) rather than
documenting against text that's about to change underneath them.

## Risk Notes
- `docs/reference/cli-commands.md` will need re-verification if the CLI surface changes again
  before this item lands — same risk flagged on `WI-DOCS-0013`.
- Extracting Section 9 touches a file with recent, carefully-reviewed content (3 commits landed
  it); keep the extraction a copy-and-link operation, not a rewrite.
