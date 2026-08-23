---
execution_id: 2026_08_23_00_12_22_WORDS_COMMAND_REVIEW
prompt_id: PROMPT(AD_HOC:WORDS_COMMAND_REVIEW)[2026-08-23T00:11:57+00:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_08_22_23_34_26_WORDS_COMMAND
pr: https://github.com/xenotaur/LCATS/pull/363
commit: 65f83868
created_at: 2026-08-23T00:12:22+00:00
agent: claude-sonnet-5
instruction_source: https://github.com/xenotaur/LCATS/pull/363
session_transcript: claude-app:bd65a2ed-883b-400d-b621-0268bc17e85a
---

# Summary

`/lrh-review-response`-equivalent round on PR #363 (`WI-VISUALIZE-0085`),
run manually via `gh`/`lrh` CLI since the `lrh-review-response` Skill
invocation was denied by permission this session. Addresses 10 review
comments (across two threads-per-finding, `chatgpt-codex-connector` +
`copilot-pull-request-reviewer`) covering 5 distinct real issues, missed by
an earlier confirm-fixes pass whose thread read raced the bots' first-push
review (see the preceding `_CONFIRM` record's Follow-up note).
`rerun_of` points to the primary implementation record
(`2026_08_22_23_34_26_WORDS_COMMAND`) since no prior `_REVIEW` record
exists for this branch.

# Result

All 10 comments passed presence/validity/feasibility triage; all were
Clear-satisfied by direct code inspection (real, current-branch issues,
each independently confirmed against the diff before fixing). Fixed:

- **P1 — join-completeness was one-directional.** `run_words` only
  checked `candidates.jsonl` IDs against the corpus, not the reverse; a
  truncated `candidates.jsonl` could silently omit corpus stories from a
  genre subset while the check still passed. Now compares both key sets
  (`corpus_ids - candidate_ids` and `candidate_ids - corpus_ids`) and
  raises with both directions reported.
- **P2 — duplicate `story_id` in `candidates.jsonl` silently overwritten.**
  `load_candidates_genre_membership` now raises `ValueError` on any
  repeated `story_id` instead of keeping the last row.
- **P2 — `--top-k` accepted 0/negative.** `run_words` now validates
  `top_k >= 1` before calling `word_frequencies`.
- **P2 — empty frequency set reached `WordCloud`, raising a third-party
  traceback.** `run_words` now raises a clear `ValueError` before
  rendering when `frequencies` is empty.
- **P2 (Copilot) — story text bypassed `lcats.stories.Story`, hand-parsing
  `story.json`.** `load_corpus_stories` now builds a `Story` via
  `Story.from_dict` and reads `.body`, while still deriving `story_id`
  from `discovery.iter_collection_story_files` paths (the identity
  `Corpora.get_corpora()` cannot provide — unchanged, per the WI's own
  acceptance criteria).
- **P2 — `words --help` didn't disclose preprocessing defaults.** The
  `words` subcommand description now states the lowercased/ASCII-alphabetic/
  minimum-length-3/stopword-filtered defaults explicitly.

# Validation

- `scripts/format --check --diff`: 210 files unchanged, 0 diff.
- `scripts/lint`: ruff and black both pass.
- `scripts/test`: 1957 tests, `OK` (5 new tests added, one per fix).
- `lrh validate`: 0 errors, 204 pre-existing warnings unrelated to this
  change.
- Real CLI runs against the checked-in corpus: whole-corpus (1868 stories)
  and `--genre fantasy` both still succeed post-fix (confirms the real
  `candidates.jsonl`/corpus pair has complete bidirectional coverage);
  `--top-k 0` now fails with a clear `ValueError` instead of a traceback;
  `words --help` now shows the preprocessing-defaults sentence.
- Pushed directly to `xenotaur/feat/words-command` (commit `1a5160cc`).

# Follow-up

- `session_transcript` is `pending` — update to the durable session
  pointer when available.
- Next: `/lrh-confirm-fixes`-equivalent re-verification against the fresh
  diff, resolving the 10 threads this round addressed, then re-check CI
  and REVIEW-LANDED coverage on the resulting commit before the final
  merge-readiness verdict.
