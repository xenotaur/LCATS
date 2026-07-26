---
execution_id: 2026_07_26_15_06_26_WI_EVENT_0030_DOGFOOD_PLAYBOOK_REVIEW
prompt_id: PROMPT(AD_HOC:WI_EVENT_0030_DOGFOOD_PLAYBOOK_REVIEW)[2026-07-26T15:06:01-04:00]
work_item: AD_HOC
status: in_progress
rerun_of: 2026_07_26_14_55_34_WI_EVENT_0030_DOGFOOD_PLAYBOOK
pr: https://github.com/xenotaur/LCATS/pull/164
commit: 8701c6f8
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/164
session_transcript: pending
created_at: 2026-07-26T15:06:26-04:00
---

# Summary

Address PR #164 review feedback on the dogfood playbook and its `run_pilot.py` docstrings.

# Result

Three P2 comments addressed (all chatgpt-codex-connector):

- **`lcats/data` (the script's default `--data-dir`) is gitignored and absent on a fresh checkout.** Confirmed via `.gitignore` (`lcats/data` entry) and `git ls-files lcats/data` (0 tracked files). Fixed by having every Step 2 (smoke test) command pass `--data-dir corpora` explicitly — `corpora/` is the tracked, always-present release snapshot (confirmed via `git ls-files corpora`, 1880 files). Added a note to Step 4 (the real run) and the README's Usage section too, since the real run's default `lcats/data` target has the same gap unless the reader has already generated it via `lcats gather`.
- **Directory-mismatch bug**: Step 2a's `cd ..` leaves the reader at the repo root, but Steps 2b/2c/Troubleshooting then ran `pip install -e ".[dev,nlp]"` from there — `pyproject.toml` lives in `lcats/`, not the repo root. Fixed by making each of those command blocks self-contained (`cd lcats && pip install ... && cd ..`), so no step depends on directory state left over from a previous one.
- **False claim that the dry-run exercises the story-level cross-segment pass.** `run_story()`'s dry-run path creates exactly one stubbed segment with an empty fake LLM response, so `_run_erw_pipeline()`'s cross-segment guard (events in >= 2 distinct segments) never fires — the story-relation pass is never invoked. Corrected this claim in `running_the_pilot.md` (Step 2a), `README.md`'s dry-run section, and both affected docstrings in `run_pilot.py` (`main`'s `--dry-run` help text and `run_story`'s docstring), all now stating plainly that dry-run covers stages 2-7 only, not the cross-segment pass.

Verified the corrected `--data-dir corpora` command actually works: ran `run_pilot.py --dry-run --data-dir corpora --sample-size 2` for real, producing 2 included (non-excluded) stories per genre.

# Validation

- `black --check`/`ruff check` on `run_pilot.py` — clean.
- `scripts/test` — 1436 tests pass. `lrh validate` — 0 errors, 43 pre-existing unrelated warnings.
- Real run of the corrected `--dry-run --data-dir corpora --sample-size 2` command — succeeds, 2 included stories per genre, confirming the fix.

# Follow-up

- `session_transcript: pending` should be updated to `claude-app:<session-id>` after this session ends.
- Proceed to `/lrh-confirm-fixes https://github.com/xenotaur/LCATS/pull/164` to verify fixes against the current diff and resolve review threads, then the merge gate, then `/lrh-closeout`.
