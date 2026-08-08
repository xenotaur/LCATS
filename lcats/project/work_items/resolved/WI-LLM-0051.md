---
resolution: "Implemented and merged in PR #254 (commit b51e1443). Ollama's tool_choice gap on the segmentation stage is real and reproduced at 0/5 baseline success across 2 models x 2 stories, including 3 identical-config repeats. A first draft concluded a retry had \"no observed chance of succeeding\" based only on the identical-config repeats never differing - Codex's automatic first-push review correctly flagged this as unsound (it never actually tested the WI's own named mitigation). Corrected: tested an explicit system-prompt reminder directly (5 calls, 2/5 succeeded, 40%) and implemented it as an automatic retry-once path in common/harness.py's run_segmentation(), verified end-to-end with a real successful call. See PROP-ERW-LOCAL-MODEL-EVALUATION's Decision 3 update (2026-08-08) for the full verdict."
blocked_reason: null
blocked: false
id: WI-LLM-0051
title: Investigate Ollama's forced tool_choice reliability for the ERW benchmark harness
type: investigation
status: resolved
owner: unassigned
contributors: []
assigned_agents: []
related_focus: []
related_roadmap: []
related_workstreams: []
related_design:
  - lcats/project/design/proposals/proposed/erw-local-model-evaluation/00_proposal.md
  - lcats/experimental/model_comparison/ollama_qwen3_8b/README.md
depends_on: []
blocked_by: []
expected_actions:
  - create_file
  - edit_file
  - run_tests
  - create_pr
  - write_docs
forbidden_actions:
  - force_push
  - delete_branch
  - merge_pr
acceptance:
  - "A documented, reproducible attempt to trigger the original run-1 failure mode (finish_reason='stop', no tool call, despite tool_choice forcing a specific function) against the current, corrected harness methodology"
  - "A written verdict in PROP-ERW-LOCAL-MODEL-EVALUATION or a follow-on note: either the gap is reproduced and characterized (frequency, trigger conditions), or a good-faith attempt found no reproduction and that is stated plainly, not silently dropped"
  - "If reproduced: common/harness.py gains a documented retry-once-on-empty-tool-result path, or an explicit decision not to add one with rationale"
artifacts_expected:
  - lcats/project/design/proposals/proposed/erw-local-model-evaluation/00_proposal.md
  - lcats/experimental/model_comparison/common/harness.py
required_evidence:
  - manual_review
  - test_output
---

## Summary

Investigate whether Ollama's OpenAI-compatible `tool_choice`
forced-function-name support has a real, reproducible gap - the leading
candidate explanation for the original `ollama_qwen3_8b` run-1 failure
(`finish_reason='stop'`, no tool call at all) that was not reproduced
across the 3 runs following the harness's methodology fix (PR #223). If
real and non-trivial in frequency, hardening `common/harness.py`'s
calling code with a bounded retry is in scope; if not reproducible after
a good-faith attempt, document that finding plainly rather than leaving
it as a permanently open, unresolved question.

## Problem / Context

`PROP-ERW-LOCAL-MODEL-EVALUATION`'s Decision 3 update names this as an
open, uncorroborated risk: community reports on Ollama's own GitHub (e.g.
issue #4386) describe gaps in forced-function-name `tool_choice` support,
and the original run-1 failure is exactly what a silently-ignored
`tool_choice` would look like. But 3 fixed-methodology runs (real segment
input, correct temperature) all succeeded, so the gap - if real - did not
manifest under those 3 samples. Named as follow-on item #3 in the
proposal's Implementation Plan. Left unresolved, this is a standing
"maybe" that will keep surfacing every time a new local candidate is
evaluated, without ever being settled.

### Prior Art Check

**Duplication search:** In-repo, no existing test or harness exercises
this specifically (the fix in PR #223 addressed a different,
already-confirmed bug - `raw_output_preview` never capturing text on this
exact failure path - not the underlying `tool_choice`-honored-or-not
question itself). External: Ollama's own GitHub issue #4386 and related
issues are the only external reference found; no fix confirmed merged as
of this session's research. Recommendation: proceed - this is a genuine
gap, not duplicated work.

**Demand search:** `PROP-ERW-LOCAL-MODEL-EVALUATION`'s Implementation
Plan directly requests this as follow-on item #3. Recommendation: this
work item satisfies that request.

## Scope

- Attempt to reproduce the original run-1 failure mode under controlled,
  varied conditions (e.g. repeated runs, different segments, different
  local models already available from `WI-LLM-0049` if landed) against
  the current, corrected harness methodology.
- Use `common/harness.py`'s `raw_output_preview` field (now fixed to
  actually capture the model's text on this failure path, per PR #223)
  to inspect what the model actually produced on any reproduced failure.
- If reproduced with meaningful frequency: design and implement a
  bounded retry (e.g. retry once with an explicit reminder in the user
  message, or fall back to Ollama's native `/api/chat` endpoint for a
  second attempt) in `common/harness.py` or the affected candidate's
  `benchmark.py` - scoped to the benchmark harness, not
  `lcats.llm.openai_backend.OpenAIBackend` itself (a retry belongs in the
  caller, not silently inside the shared production backend).
- If not reproduced after a good-faith attempt (e.g. 10+ varied runs):
  document that finding explicitly in
  `PROP-ERW-LOCAL-MODEL-EVALUATION` or a follow-on note, rather than
  leaving the Open Question unanswered indefinitely.

## Required Changes

- A documented investigation (in the proposal, a new AD_HOC finding note,
  or this work item's own execution record) with real, reproducible
  evidence either way.
- `common/harness.py` changes only if a retry path is actually
  warranted by the findings - do not add speculative resilience code for
  an unconfirmed problem.

## Non-Goals

- Does not modify `lcats.llm.openai_backend.OpenAIBackend`'s production
  exception-raising behavior beyond what PR #223 already fixed (the
  `raw_output_preview` capture) - any retry logic belongs in the
  benchmark harness/candidate layer, not the shared backend.
- Does not attempt to fix or work around the gap inside Ollama itself -
  out of this repo's control.
- Does not block on this before other follow-on work items
  (`WI-LLM-0049`, `WI-LLM-0050`) - independent investigation.

## Acceptance Criteria

- A documented, reproducible attempt to trigger the original failure
  mode against the corrected harness methodology.
- A written verdict (reproduced-and-characterized, or
  good-faith-not-reproduced) recorded in the proposal or a follow-on
  note.
- If reproduced: a retry path added and tested, or an explicit,
  reasoned decision not to add one.

## Validation

- `scripts/test tests/llm_tests`
- `lrh validate`
- Multiple real benchmark runs (varied segments/candidates) attempting
  reproduction, with `raw_output_preview` inspected on any failure

## Risk Notes

- This is inherently a negative-result-tolerant investigation - a
  "could not reproduce after N attempts" outcome is a valid, useful
  result, not a failed work item. Do not force a retry-path
  implementation if the evidence doesn't support one.
