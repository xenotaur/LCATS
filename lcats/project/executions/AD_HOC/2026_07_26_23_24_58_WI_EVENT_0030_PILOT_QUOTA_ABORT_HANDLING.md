---
execution_id: 2026_07_26_23_24_58_WI_EVENT_0030_PILOT_QUOTA_ABORT_HANDLING
prompt_id: PROMPT(AD_HOC:WI_EVENT_0030_PILOT_QUOTA_ABORT_HANDLING)[2026-07-26T23:24:50-04:00]
work_item: AD_HOC
status: in_progress
rerun_of:
pr: https://github.com/xenotaur/LCATS/pull/166
commit: 50ef2c2b
agent: claude_app
instruction_source: chat session (live dogfooding of WI-EVENT-0030's run_pilot.py, Step 4)
session_transcript: pending
created_at: 2026-07-26T23:24:58-04:00
---

# Summary

Real Step-4 dogfooding of `run_pilot.py` hit an exhausted Anthropic account
balance mid-run (400 `invalid_request_error`, "Your credit balance is too
low"). The script had no concept of a fatal, account-level API error - it
treated the credit exhaustion as a per-story exclusion and burned through
every remaining candidate/story making the same doomed call, producing a
confusing `included=0` report for every genre with no top-level indication
of why. Add fatal-error detection and a clean early abort, reusing the
`should_abort_batch` convention already established in
`lcats/analysis/corpus/processing.py`.

# Result

- `lcats/lcats/analysis/llm_extractor.py`'s `_classify_api_error` only
  recognized OpenAI's billing-error shape (`insufficient_quota` code, HTTP
  402). Anthropic's actual "credit balance too low" error is a 400
  `invalid_request_error` with neither of those markers, so it fell through
  to `category="unknown"`, `should_abort_batch=False`. Added a
  `"credit balance" in message` check to the existing quota branch so it now
  classifies as `category="quota_exceeded"`, `should_abort_batch=True`.
- `experiments/03_cross_segment_relation_pilot/run_pilot.py` had no
  equivalent check at any of its three API call sites (genre-detection via
  `assess_story`, segmentation, and the ERW extractor pipeline). Added a new
  `FatalPilotError` exception and a `_check_fatal()` helper matching
  substrings for exhausted quota/credit and bad/expired credentials, wired
  into all three call sites. `main()` now catches `FatalPilotError` at both
  the sample-building stage and the per-story loop, prints a clear
  "aborting - bad credentials or exhausted balance" message, and still
  writes out `pilot_stories.jsonl`/`pilot_usage.jsonl`/`pilot_summary.json`
  for whatever partial results were gathered before the abort (new exit
  code 3), instead of silently grinding through the whole remaining sample.
- Fixed a small pre-existing type wrinkle noticed while doing this:
  `_segment_story`'s error could be the classified `api_error` dict rather
  than a string, so `row["exclude_reason"] = f"segmentation failed:
  {seg_error}"` was dumping the raw dict repr into the exclusion reason.
  Now extracts `.get("message", str(seg_error))` first.
- Did not add an LCATS-level retry loop for `can_retry=True` responses
  (rate limits/5xx): the Anthropic Python SDK already retries these
  automatically (2 retries with exponential backoff, driven by the
  server-supplied `x-should-retry` response header - confirmed directly in
  a live `ANTHROPIC_LOG=debug` capture, where every 400 in that run carried
  `x-should-retry: false` and was correctly not retried). A second, bespoke
  retry layer on top would risk conflicting with that; the SDK's own
  `max_retries` client option is the correct extension point if more
  resilience is ever wanted.

# Validation

- `scripts/format --check --diff` / `scripts/lint` on both changed files -
  clean.
- `scripts/test` - 1436 tests pass.
- `lrh validate` - 0 errors, 43 pre-existing unrelated warnings.
- Manual check: `_check_fatal()` raises on Anthropic's real "credit balance
  too low" message and on OpenAI's `insufficient_quota`, and does not raise
  on an ordinary per-story message ("segmentation produced no segments").
- Manual check: `JSONPromptExtractor._classify_api_error()` on a payload
  shaped exactly like the real captured error (`status=400,
  type=invalid_request_error, message="Your credit balance is too low..."`)
  now returns `category="quota_exceeded"`, `should_abort_batch=True`.

# Follow-up

- `session_transcript: pending` should be updated to `claude-app:<session-id>`
  after this session ends.
- The original "stall then resume" during genre-detection (reported before
  the credit exhaustion was found) is still unresolved - the
  `ANTHROPIC_LOG=debug` capture available so far covers only a later run
  where every call failed identically and fast (non-retryable), so it never
  exercised the SDK's retry path. Re-run with credits restored (and
  `ANTHROPIC_LOG=debug` still on) to settle it.
- Still pending: WI-EVENT-0030's actual real run (Step 4), results
  write-up (Step 6), and closeout to `resolved/` (Step 7) - none of this
  PR's changes complete those, they only make a future attempt fail loud
  and fast instead of silently.
