---
execution_id: 2026_08_28_07_21_15_BACKLOG_UPDATE_PARAGRAPH_BOUNDARY_FINDING
prompt_id: PROMPT(AD_HOC:BACKLOG_UPDATE_PARAGRAPH_BOUNDARY_FINDING)[2026-08-28T07:21:04+00:00]
work_item: AD_HOC
status: landed
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/406
commit: d20b6c72
agent: claude_app
instruction_source: "user request in-session (\"please file a backlog item for [WI-SEGMENT-0098's finding]... unless you think it deserves its own WI\")"
session_transcript: claude-app:e8e46d5d-35d3-4ccc-9cba-137bd31bf3a5
created_at: 2026-08-28T07:21:15+00:00
---

# Summary

User asked to file a backlog item for `WI-SEGMENT-0098`'s real finding
(all 6 boundary-truncation cases undercount `end_par_id` by 1-2
paragraphs, consistently, never overcounting), unless it deserved its
own WI.

# Result

Checked `project/design/backlog.md` before adding anything new and found
a closely related, pre-existing entry: `"align_segment"'s paragraph-mis-
numbering failures - P2, real cause still unknown`, from an earlier
`WI-SEGMENT-0069` 30-story smoke test (6 of 21 cases, mixed
undercount/overcount directions, larger drift magnitudes). Rather than
file a duplicate entry, updated that existing one with a dated addendum
citing `WI-SEGMENT-0098`'s newer, cleaner sample, noting the
directionality disagreement between the two samples as an open question,
and cross-referencing `WI-SEGMENT-0098`'s design doc and execution
record.

Did not file a fresh WI: `WI-SEGMENT-0098`'s own Recommendation section
already states the combined evidence (12 real cases across two samples)
is still short of the ~100+-story dedicated sample the existing backlog
entry's own "why not a fresh investigation-type WI yet" gate calls for -
a backlog update is the right weight for this evidence increment, not a
new planning artifact.

Opened PR #406 (branch
`xenotaur/chore/backlog-update-paragraph-boundary-finding`, commit
`51b5a72e`).

**Review-round correction (PR #406, 1 finding confirmed real before
fixing):** a real formatting issue - a very long inline-code path
reference on its own line, inconsistent with the file's own wrapping
convention. Fixed by shortening the reference to the directory (dropping
the redundant full timestamped filename, since the dated entry text
already locates it) rather than mid-splitting the backtick span, which
would have inserted an unwanted space into the path text itself.

# Validation

- `lrh validate` - 0 errors (warning count varies run-to-run with
  concurrent landings elsewhere in the repo; `backlog.md` is explicitly
  not schema-validated, per its own header)

# Follow-up

- None - this is a plain notes-file update, not a planning artifact
  requiring further action.
