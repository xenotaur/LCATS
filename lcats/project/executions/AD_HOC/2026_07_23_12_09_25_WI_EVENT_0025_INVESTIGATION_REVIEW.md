---
execution_id: 2026_07_23_12_09_25_WI_EVENT_0025_INVESTIGATION_REVIEW
prompt_id: PROMPT(AD_HOC:WI_EVENT_0025_INVESTIGATION_REVIEW)[2026-07-23T11:47:50-04:00]
work_item: AD_HOC
status: in_progress
rerun_of: 2026_07_23_04_21_57_WI_EVENT_0025
pr: https://github.com/xenotaur/LCATS/pull/146
commit: a4c218d
created_at: 2026-07-23T12:09:25-04:00
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/146
session_transcript: pending
---

# Summary

Addressed all 5 open review comments (chatgpt-codex-connector x3,
copilot-pull-request-reviewer x2) on PR #146, which delivers the
`WI-EVENT-0025` NLP-library evaluation. Three of the five required
substantive content correction, not just wording — this round involved
additional web research to fix claims that were unsupported or fabricated
in the original document.

# Result

- Comment (codex): the "defer" recommendation ignored that
  `WI-EVENT-0024`'s acceptance criteria literally require
  syntactic/morphological surface features, which the planned
  word/sentence-count heuristics cannot produce — and the document's own
  "Sketch" section fabricated a claim that heuristics "produce" POS-tag/
  parse-depth/morphology fields, which is false. Added a "Tension with
  WI-EVENT-0024's acceptance criteria" section that surfaces the gap
  explicitly and proposes two resolutions (narrow the criterion, or adopt
  a library now) without unilaterally deciding for that work item. Removed
  the fabricated claim from the Sketch section.
- Comment (codex): asserting that UDPipe's CC BY-NC-SA model license
  transfers to output annotations was an unsupported legal claim —
  model-use restrictions and output copyright are different questions.
  Rewrote the UDPipe section to describe the restriction on the model
  precisely, note the output-copyright question is unresolved by UDPipe's
  own docs, and cite the `bnosac/udpipe.models.ud` CC BY-SA alternative
  distribution as a mitigation.
- Comment (codex): "smallest model footprint" was asserted for spaCy
  without comparable figures for NLTK, Stanza, or UDPipe, despite
  dependency/model weight being an explicit `WI-EVENT-0025` acceptance
  criterion. Researched real, sourced figures: spaCy `en_core_web_sm`
  ~11-13MB, NLTK's `averaged_perceptron_tagger` ~2.4MB, UDPipe's English
  UD 2.1 model ~15.6MB, Stanza's PyTorch dependency alone ~200MB-1GB+.
  spaCy is not the smallest — added a footprint comparison table and
  revised the recommendation's reasoning to rest on maturity and
  feature-richness rather than an unsupported size ranking.
- Comment (copilot): both `pyproject.toml` citations were missing the
  `lcats/` prefix — verified the real path is `lcats/pyproject.toml` and
  fixed both instances.
- Comment (copilot): "once fetched once" duplicated wording — fixed.

All 5 comments were valid and addressed; none were skipped.

# Validation

- `lrh validate` — 0 errors, 31 pre-existing warnings unrelated to this
  file
- `scripts/format`/`scripts/lint`/`scripts/test` not applicable — no
  Python code touched (documentation-only change)
- All new factual claims (model/dependency sizes) grounded via web search
  before being written, with sources cited inline in the document

# Follow-up

- `session_transcript: pending` should be updated to `claude-app:<session-id>`
  after this session ends.
- The "Tension with WI-EVENT-0024's acceptance criteria" section's
  decision (narrow the criterion vs. adopt a library now) is unresolved
  and should be addressed before or during `WI-EVENT-0024`'s
  implementation.
- Recommend `/lrh-confirm-fixes` on PR #146 before merge to verify these
  fixes against the current diff and resolve the review threads.
