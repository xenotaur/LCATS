---
execution_id: 2026_06_29_22_07_59_LLM_BACKEND_DESIGN_PROPOSAL_REVIEW
prompt_id: PROMPT(AD_HOC:LLM_BACKEND_DESIGN_PROPOSAL_REVIEW)[2026-06-29T21:48:01-04:00]
work_item: AD_HOC
status: in_progress
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/99
commit: 31d0910
created_at: 2026-06-29T22:07:59-04:00
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/99
session_transcript: pending
---

# Summary

Addressed two open Codex review comments on PR #99 (the LLM backend unified
design proposal): one flagging that `lcats/lcats/extraction.py` was a
packaged-library LLM call path left out of the migration plan, and one
flagging an internal scope contradiction in WI-LLM-0007 (Scope said "no
existing files modified" while Notes said `pyproject.toml` needed an edit).

# Result

Both comments were valid and addressed:

1. **extraction.py migration gap** — Split the "Existing Call Patterns" table
   in `project/design/unified-llm-backend-design.md` into Pattern A1
   (exploratory `KMo/` scripts, excluded) and Pattern A2 (`extraction.py`,
   packaged library code with its own test suite, now in scope). Added a
   "Changes to Existing Code" subsection detailing the `extraction.py`
   migration. Extended `WI-LLM-0008` to cover `extraction.py` and
   `tests/extraction_test.py` alongside `JSONPromptExtractor`, retitled the
   work item, and added an acceptance criterion using
   `rg "chat.completions.create"` to confirm no packaged call site was missed.
   Updated the design doc's Non-Goals to clarify the `KMo/analyze.py`
   exclusion does not extend to `extraction.py`, which it imports.

2. **pyproject.toml scope contradiction** — Updated `WI-LLM-0007`'s Objective
   and Scope sections to explicitly list `pyproject.toml` as a modified file
   (adding the `openai` dependency), replacing the unconditional "no existing
   files modified" claim. Added a new "Dependency Scope" section to the
   design doc explaining why this edit is required (undeclared runtime
   dependency would otherwise break `OpenAIBackend` construction in clean
   installs). Added a corresponding acceptance criterion to WI-LLM-0007.

While validating, `lrh validate` also surfaced a real (if minor) issue in my
own new files: `depends_on` on WI-LLM-0008/0009/0010 was written as a scalar
or comma-separated string rather than a YAML list. Fixed all three to use
list syntax (e.g. `depends_on: [WI-LLM-0007]`).

# Validation

No Python files were touched in this PR (review-response changes are all to
`project/` markdown control-plane files), so `scripts/format`, `scripts/lint`,
and `scripts/test` are not applicable.

```
git rev-parse HEAD          — 31d0910
git status --short          — clean after commit
lrh validate                — 55 errors, 4 warnings (down from 58/4 baseline)
```

The 55 remaining errors are pre-existing, repo-wide schema drift: every work
item in the repo (including `WI-APPLY-0005`, `WI-META-0006`,
`WI-REVIEW-0003`, `WI-SPANOPS-0002`, `WI-PERSIST-0004`, `WI-REPAIR-0001`, none
of which this PR touches) is missing the `type`, `blocked`, `blocked_reason`,
and `resolution` frontmatter fields, and `contributors.md` lacks
`display_name`/`roles`/`type`. These predate this PR and are out of scope for
a review response targeting two specific reviewer comments — fixing them
would require a repo-wide schema migration outside this change's blast
radius. The 3-error reduction (58 → 55) is exactly the `depends_on` list-format
fix described above.

# Follow-up

- Repo-wide work item schema drift (missing `type`/`blocked`/`blocked_reason`/
  `resolution` fields, `contributors.md` missing required fields,
  `UNKNOWN_OWNER` for `unassigned`) should be tracked as a separate cleanup
  item; not addressed here as it is unrelated to the two review comments.
- No prior execution record was found for this branch
  (`llm-backend-design-proposal`) under any prompt-derived slug, because PR #99
  was created directly via the create-pr-command workflow rather than
  `/lrh-implement`. `rerun_of` is left empty per the skill's documented edge
  case for PRs created outside the standard implement flow.
- `session_transcript` is `pending` and should be updated to
  `claude-app:<session-id>` after this session ends.
