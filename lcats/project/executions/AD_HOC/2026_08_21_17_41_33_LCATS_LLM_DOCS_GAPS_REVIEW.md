---
execution_id: 2026_08_21_17_41_33_LCATS_LLM_DOCS_GAPS_REVIEW
prompt_id: PROMPT(AD_HOC:LCATS_LLM_DOCS_GAPS_REVIEW)[2026-08-21T17:41:28+00:00]
work_item: AD_HOC
status: landed
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/331
commit: 
created_at: 2026-08-21T17:41:33+00:00
---

# Summary

`/lrh-review-response` round on PR #331, driven by `/lrh-land`'s Step 4.
No primary implementation record exists for this PR (confirmed via the
primary-record provenance check — only the `_SELFREVIEW` side record
matched `pr:` for this PR, with no sibling, so `rerun_of` is left empty
by design pending the backfill primary record `/lrh-land` Step 7 will
author). Addressed the automatic first-push review from
`chatgpt-codex-connector`.

# Result

Two review comments, both presence-confirmed, valid, and feasible to fix:

1. **P2 — "Label the genre result as a pilot-scale test"**
   (`docs/how-to/local-openai-endpoint.md`'s per-stage verdict table).
   The genre-detection row said "Held up at genre-census scale," but
   `WI-LLM-0066`'s own source
   (`lcats/experimental/model_comparison/ollama_gpt_oss_20b/README.md:270-297`)
   explicitly describes its result as a 20-story pilot/multi-genre
   sample, not the full ~1,868-story corpus, which has not run for any
   candidate. Confirmed the reviewer's citation directly before fixing.
   Fixed: reworded the row to "Held up at multi-story, multi-genre pilot
   scale (20 stories, not the full ~1,868-story corpus, which has not
   run for any candidate)," keeping the go/no-go recommendation and its
   ~20.8hr/$0 figures as a separate, clearly-labeled recommendation for
   the *future* full run, not an already-observed result.
2. **P2 — "Recompute the audit inventory from the finalized tree"**
   (`project/audits/docs/docs-audit-2026-08-21.md`'s headline metrics).
   The audit's file counts (881 total / 803 `project/`) and link count
   (229 non-HTTP) were captured before the commit that added the audit
   and self-review artifacts themselves, and the link-check methodology
   conflated "total links" with "non-HTTP links checked." Confirmed by
   independently re-running both counts: `find . -iname "*.md" -not
   -path "./.git/*" | wc -l` → 883 total, 805 under `lcats/project/`;
   and the audit's own supplied link-check script → 231 total
   `[text](path)` links, 109 non-HTTP targets subject to the filesystem
   check, 4 real broken links + 3 false positives (one more than the
   audit stated, because the audit file itself now contains the literal
   `[text](path)` pattern in its own embedded validation script — a
   self-referential false positive that only appears once the audit is
   part of the tree it's auditing). Fixed: updated every headline count
   in the audit (Summary, Scope and roots inspected, inventory table,
   layout diagram, Stale-links Method paragraph) to the reproducible
   finalized-tree numbers, and made the total-links-vs-checked-links
   distinction explicit so the methodology is reproducible going
   forward.

# Validation

- `lrh validate` → 0 errors against both edited files
- Re-ran the audit's own link-check script against the finalized tree:
  231 total links, 109 non-HTTP, 4 real broken (unchanged from the
  audit's substantive findings — only the false-positive count and
  headline totals needed correction)
- `find . -iname "*.md" -not -path "./.git/*" | wc -l` → 883;
  `find lcats/project -iname "*.md" | wc -l` → 805 (matches the
  reviewer's own cited numbers exactly)

# Follow-up

None — proceeds to `/lrh-confirm-fixes` per the `/lrh-land` chain.
