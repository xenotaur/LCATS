---
execution_id: 2026_08_10_19_09_42_WI_PILOT_0060_MODEL_TIERING
prompt_id: PROMPT(WI-PILOT-0060:WI_PILOT_0060_MODEL_TIERING)[2026-08-10T18:54:49+00:00]
work_item: WI-PILOT-0060
status: landed
rerun_of:
pr: https://github.com/xenotaur/LCATS/pull/286
commit: e1434d9daf180ec4bafc04becf684588901ed3fd
agent: codex_app
instruction_source: project/work_items/proposed/WI-PILOT-0060.md
session_transcript: codex-app:019fea05-63b0-7e02-80d2-e570de36c7c3
created_at: 2026-08-10T19:09:42+00:00
---

# Summary

Evaluate per-stage model tiering for the cross-segment relation pilot's
genre-detection and segmentation stages against the WI-PILOT-0051 fixture
set. Add opt-in per-stage model overrides to `run_pilot.py`, run a bounded
real Anthropic comparison after explicit approval, and update Decision 5 in
`PROP-LCATS-PILOT-COST-SUSTAINABILITY` with a go/no-go recommendation.

# Result

- Added `StageModels` plumbing and optional per-stage CLI flags to
  `experiments/03_cross_segment_relation_pilot/run_pilot.py`:
  `--model-genre-detect`, `--model-segment`, `--model-entity`,
  `--model-event`, `--model-relation`, `--model-discourse`, and
  `--model-cross-segment`. The global `--model` remains the default for
  every stage unless an override is supplied.
- Updated segmentation, genre-detection, ERW extractor construction, and
  checkpoint fingerprints so the actual per-stage model choices are used
  and checkpoint-safe.
- Added fake-backend tests proving defaulting and per-stage call-site
  wiring before real spend.
- Added a bounded measurement script,
  `experiments/03_cross_segment_relation_pilot/measure_model_tiering.py`,
  plus tests and a separate validated fixture genre ground-truth file.
- Ran the explicitly-approved real comparison against the two WI-PILOT-0051
  fixture stories:
  - Baseline `claude-opus-4-8`: 4 calls, 18,748 input tokens, 2,365 output
    tokens, $0.152865; genre-detect raw/schema validity 2/2, genre accuracy
    2/2, truncation 0/2; segmentation schema validity 1/2, truncation 0/2.
    The segmentation miss was an alignment failure on `king_of_the_hill`, not
    truncation.
  - Candidate `claude-haiku-4-5-20251001`: 4 calls, 14,358 input tokens,
    2,106 output tokens, $0.024888; genre-detect raw/schema validity 2/2,
    genre accuracy 2/2, truncation 0/2; segmentation schema validity 2/2,
    truncation 0/2.
  - Savings: $0.127977 on this fixture set, an 83.72% reduction for the two
    measured stages.
- Updated Decision 5 with a bounded go recommendation for a follow-on
  configuration/defaulting change: use Haiku 4.5 for genre-detection and
  segmentation while keeping top-tier models for ERW/cross-segment stages.
  WI-PILOT-0060 itself does not default tiering on.
- Self-review note: `lrh-self-review` was not available in this Codex skill
  install, so an independent fresh subagent was used in diff-review mode
  without contacting GitHub. It found one caveat, now documented in Decision
  5: both models marked `king_of_the_hill` as `wellformed: false` while the
  ground truth marks it wellformed; this is outside the consumed
  `detected_genre` metric but worth recording.
- Process note: this session was interrupted and resumed after initial edits
  began; prompt ID and execution-record bookkeeping were caught up before PR
  creation rather than before the first file edit.

# Validation

- `lrh work-items readiness WI-PILOT-0060 --format md` from `lcats/`: ready,
  no blocking warnings.
- `lrh prompt check-execution --prompt-id
  "PROMPT(WI-PILOT-0060:WI_PILOT_0060_MODEL_TIERING)[2026-08-10T18:54:49+00:00]"
  --project-root .`: no execution records found.
- Environment drift checks:
  - Initial checks found `lcats` resolving to a sibling worktree and PATH
    resolving Homebrew `ruff`/`black`.
  - Repaired with `conda run -n LCATS scripts/develop` and validated with
    the LCATS conda environment's `bin` directory first on `PATH`.
  - `python -c "import lcats; print(lcats.__file__)"` resolved to this
    worktree's `lcats/src/lcats/__init__.py`.
- `scripts/version tools` under the LCATS env/PATH: Python 3.11.9,
  Ruff 0.15.0, Black 25.11.0, pip 26.0.1; LCATS package and CLI both
  `0.1.1.dev465+gc5ee83bd3.d20260810`.
- `scripts/format --check --diff` under LCATS env/PATH: 185 files unchanged.
- `scripts/lint` under LCATS env/PATH: Ruff checks passed; Black formatting
  check passed.
- `scripts/test` under LCATS env/PATH: 1705 tests OK.
- Experiment-specific checks under LCATS env/PATH:
  - `python -m unittest experiments/03_cross_segment_relation_pilot/run_pilot_test.py
    experiments/03_cross_segment_relation_pilot/measure_model_tiering_test.py`:
    41 tests OK after review-response tests were added.
  - `python -m black --check --diff` on changed experiment Python files:
    4 files unchanged.
  - `python -m ruff check` on changed experiment Python files: all checks
    passed.
- `git diff --check`: passed.
- `lrh validate`: 0 errors, 133 pre-existing warnings.

# Follow-up

- Follow-on adoption/configuration work should decide whether to make Haiku
  4.5 the default for genre-detection and segmentation in the pilot. This PR
  deliberately keeps all stages on the global model unless explicitly
  overridden.
- The `wellformed` mismatch observed for `king_of_the_hill` should be kept
  in mind for corpus-QA decisions; WI-PILOT-0060 only validated the
  genre-label signal consumed by the pilot's genre-detection scan.
