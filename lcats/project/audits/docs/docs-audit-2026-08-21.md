---
id: AUDIT-DOCS-2026-08-21
audit_type: docs
schema_version: 1
status: proposed
repo_root: .
project_root: lcats
docs_root: lcats/docs
control_root: lcats/project
package_roots: ["lcats/src/lcats"]
framework: diataxis
recommended_next_prompt: organize_docs
recommended_phase: phase-2c-post-rename-cleanup
---

## Summary

This is a follow-up audit to
[`2026-07-07-docs-audit.md`](2026-07-07-docs-audit.md). That audit's
Phase 3 (reference normalization) and Phase 4 (tutorial gap closure)
have both substantially landed since: `docs/tutorials/quickstart.md`,
`docs/reference/cli-commands.md`, and `docs/reference/llm-backend.md`
all now exist, and `docs/how-to/run-assess.md` was extracted as
recommended. Real growth beyond that plan also landed:
`docs/how-to/secrets-hygiene.md`, `docs/how-to/local-openai-endpoint.md`
(added earlier in this session, closing this audit's originating
confirmed gap — `OpenAIBackend`'s undocumented `base_url` parameter and
the invisible `experimental/model_comparison/` local-model evaluation
work), `docs/reference/corpus-promotion.md`,
`docs/reference/gather-overrides.md`, `docs/reference/prepare-corpora-release.md`,
and `docs/explanation/story-bucket-layout.md`.

Two things happened since 2026-07-07 that this audit's findings mostly
trace back to. First, the package was renamed `lcats/lcats/` →
`lcats/src/lcats/` (a real `git mv`, history preserved), and the docs
prose was not fully updated to match — 9 stale-path occurrences across
4 files, plus 2 links in the corpus README that are now one directory
level short of correct because of the added `src/` level. Second, the
prior audit's Phase 3 item "extract Section 9 [of the corpus README]
into `docs/how-to/run-assess.md`; leave a short pointer in its place"
only did the extraction — the source section still carries the full
original content, and the two links meant to close that loop are
exactly the ones broken by the rename above.

Key findings:
- All counts below are measured against `main`'s tip at commit
  `88858ae3` (this audit PR's base commit, before any of this PR's own
  changes) — a fixed, reproducible reference point, not "the finalized
  tree including this audit," which is a moving target: every commit
  that lands this artifact (or its own review-response/self-review
  execution records) necessarily adds more files and links after the
  count was taken, so a count claiming to include itself can never
  actually be exact (this instability was caught in review — see Risks
  and cautions). 880 Markdown files exist at that commit (803 are
  `lcats/project/` control-plane, Meta by this skill's convention). 51
  human-facing files were classified into Diataxis quadrants; of 218
  total `[text](path)` links found, 96 are non-HTTP/non-fragment targets
  subject to a filesystem existence check — **4 real broken links
  found** (2 false positives excluded, both prose describing link-check
  methodology rather than real links). This artifact and its own
  execution records (self-review, review-response, confirm-fixes) are
  deliberately excluded from these counts by design, not omitted by
  oversight — see Risks and cautions for why a self-inclusive count is
  not achievable and Validation commands for follow-up PRs for how to
  re-run this check against a later commit.
- **Tutorial quadrant gap from the prior audit is resolved.**
  `docs/tutorials/quickstart.md` exists, requires no API key, and states
  every command in it was run for real before writing.
- **`annotate` is a fully implemented CLI subcommand
  (`lcats/src/lcats/cli.py:252`) with zero documentation anywhere** — not
  in `docs/reference/cli-status.md`, not in `docs/reference/cli-commands.md`,
  not in the repo-root `README.md` CLI table — despite real usage
  evidence in `lcats/experimental/annotation_feasibility_trial/` and
  resolved work items `WI-ANNOTATE-0050`/`WI-ANNOTATE-0054`. `promote`
  and `clean` are also implemented and missing from the repo-root
  README's table specifically (both are documented in
  `docs/reference/cli-commands.md`).
- **Repo-root `/README.md` still hasn't received the accuracy fixes the
  prior audit scoped for it** (Phase 2b): "Python 3.6+", "OpenAI API key
  (for LLM features)" with no mention of Anthropic, and an incomplete
  CLI table. `lcats/README.md`'s equivalent issues were fixed; the
  repo-root file was not.
- **Substantial recent work remains undocumented from `docs/`:**
  `experiments/04_genre_census/` and `experiments/05_metadata_genre_prefilter/`
  (both real, recently-landed, zero inbound links from `docs/index.md`,
  unlike `experiments/03_cross_segment_relation_pilot/` which is
  linked), and `lcats/experimental/model_comparison/`'s findings, which
  now have exactly one inbound `docs/` cross-reference (this session's
  `docs/how-to/local-openai-endpoint.md`) but no Explanation-quadrant
  page synthesizing them.
- **A real, unfixed bug surfaced by `experimental/annotation_feasibility_trial/`
  has no tracking work item.** The trial's own README recommends filing
  one for a segmentation offset-corruption defect
  (`text_segmenter.py`'s `build_paragraph_index`/`align_segment`, on
  single-newline-paragraph stories); `project/work_items/{proposed,active}/`
  contain no such item. This is a work-item gap, not a docs gap — noted
  here because it was discovered during the docs walk, but out of this
  skill's scope to create.

## Scope and roots inspected

- `repo_root` (`.`): top-level repository containing `Papers/`,
  `Resources/`, `corpora/`, `experiments/`, and the nested `lcats/`
  execution root. No `docs/` or `project/` exists at this level — both
  live nested under `lcats/`, unchanged from the prior audit.
- `project_root` / execution root (`lcats/`): the active Python project.
- `docs_root` (`lcats/docs/`): human-facing documentation hub. Grown
  substantially since 2026-07-07 (see Summary).
- `control_root` (`lcats/project/`): LRH control-plane, 803 files at
  commit `88858ae3` across `executions/` (648), `work_items/` (87),
  `design/` (27, incl. 10 proposals), `workstreams/` (16), `audits/`
  (5), `guardrails/` (4), `evidence/` (3), `prompts/` (2),
  `contributors/` (2), `context/` (2), plus single-file `status/`,
  `roadmap/`, `principles/`, `memory/`, `goal/`, `focus/`, and
  `project/README.md`. This PR's own additions (this audit file, and
  its self-review/review-response/confirm-fixes execution records) are
  excluded from this count by design — see Key findings above.
- `package_roots` (`lcats/src/lcats/`): **corrected from the prior
  audit's `lcats/lcats/`** — the package was renamed via `git mv`
  sometime after 2026-07-07. This rename is the root cause of most of
  this audit's Accuracy findings below.
- Also inspected: `experiments/` (7 subdirectories, up from 2 at the
  prior audit — `03_cross_segment_relation_pilot`, `04_genre_census`,
  `05_metadata_genre_prefilter` all new), `lcats/experimental/` (new
  since the prior audit — `model_comparison/` with 11 subdirectories,
  `annotation_feasibility_trial/`, `secrets_hygiene/`,
  `verify_assess_api/`), `.jules/` (agent learning logs, Meta),
  `Papers/` and `Resources/` (out of scope, unchanged).

Discovery method: recursive filesystem walk for `*.md` (880 files at
commit `88858ae3`, this PR's base commit — see Key findings above for
why counts are pinned to a fixed commit rather than "the tree including
this audit"), cross-checked against the discovery checklist in the
`lrh-doc-audit` skill's `references/audit-requirements.md`, covering
docs directories, top-level meta files, package/subsystem READMEs,
examples/experimental directories, CLI surface via
`lcats/src/lcats/cli.py` source inspection (`add_parser` calls), and the
control-plane directory. Delegated to a subagent for the
discovery/classification pass; findings independently spot-verified in
this session (grep confirmation of the `lcats/lcats` stale-path
occurrences, the `annotate` subcommand and its absence from all three
CLI-doc locations, and the exact broken-link line numbers).

**Correction history:** `chatgpt-codex-connector`'s PR #331 review
flagged that this artifact's first-committed headline counts (881
total / 803 project / 229 non-HTTP links) were captured before the
commit that added the audit and self-review artifacts, and so didn't
reproduce against that "finalized" tree. The first fix attempted to
recompute against "the finalized tree including this file," which
turned out to be an unstable target — the fix commit itself, plus its
own execution record, added yet more files the recomputed numbers
didn't include, reproducing the identical bug one level deeper (caught
by an independent `--subagent` confirm-fixes pass; see
`project/executions/AD_HOC/` for the round's execution record). The
counts in this artifact are now pinned to `88858ae3` — a fixed commit
that predates every one of this PR's own additions — which is
reproducible indefinitely, unlike "the tree including this audit,"
which can never be measured exactly at the moment of its own commit.

## Current documentation inventory

### Human-facing documentation (Diataxis-eligible)

| File | Quadrant |
|---|---|
| `/README.md` (repo root) | Mixed (tutorial + how-to + reference + explanation) |
| `lcats/README.md` | Mixed (how-to install/build + thin reference + links to hub) |
| `lcats/docs/README.md` | Meta (navigational landing page) |
| `lcats/docs/index.md` | Meta (navigational — Diataxis map) |
| `lcats/docs/reference/README.md` | Meta (navigational reference index) |
| `lcats/docs/reference/cli-status.md` | Reference |
| `lcats/docs/reference/cli-commands.md` | Reference |
| `lcats/docs/reference/llm-backend.md` | Reference |
| `lcats/docs/reference/corpus-promotion.md` | Reference (light rationale opener, command reference dominant) |
| `lcats/docs/reference/gather-overrides.md` | Reference |
| `lcats/docs/reference/prepare-corpora-release.md` | How-to (explicit manual runbook) |
| `lcats/docs/how-to/run-assess.md` | How-to |
| `lcats/docs/how-to/secrets-hygiene.md` | How-to |
| `lcats/docs/how-to/local-openai-endpoint.md` | How-to (this session's fix — well cross-linked both directions) |
| `lcats/docs/secrets-setup.md` | Mixed, How-to dominant |
| `lcats/docs/explanation/story-bucket-layout.md` | Explanation |
| `lcats/docs/tutorials/quickstart.md` | Tutorial |
| `lcats/AGENTS.md` | Meta |
| `lcats/STYLE.md` | Meta |
| `lcats/tests/AGENTS.md` | Meta |
| `lcats/tools/templates/improve_coverage.md` | How-to (AI-agent task template) |
| `.jules/bolt.md`, `.jules/sentinel.md`, `lcats/.jules/bolt.md` | Meta (agent learning logs; the third is a nested duplicate) |
| `lcats/scripts/README.md` | Mixed, Reference dominant |
| `lcats/tools/README.md` | Mixed, Reference dominant (carries 4 of the 9 stale `lcats/lcats/` occurrences) |
| `lcats/src/lcats/analysis/corpus/README.md` | **Mixed — flag for splitting, still unresolved from prior audit.** §1–8 Explanation, §9 How-to (superseded in practice by `docs/how-to/run-assess.md`, which now exists — §9 should become a short pointer; its 2 links back to `docs/` are currently broken) |
| `experiments/README.md` | Explanation (directory convention + placement rationale) |
| `experiments/01_classify_corpora/{README,dataset/README,results/README}.md` | Reference/How-to (unchanged from prior audit) |
| `experiments/02_llm_backend_comparison/README.md` | Mixed — How-to + Reference |
| `experiments/03_cross_segment_relation_pilot/README.md` | Mixed — Reference + status log |
| `experiments/03_cross_segment_relation_pilot/fixtures/README.md` | Reference |
| `experiments/03_cross_segment_relation_pilot/running_the_pilot.md` | How-to |
| `experiments/03_cross_segment_relation_pilot/results/stability_gate/stability_gate_report.md` | Reference |
| `experiments/04_genre_census/README.md` | Mixed — Reference (results table) + status log. **Not linked from `docs/index.md`.** |
| `experiments/05_metadata_genre_prefilter/README.md` | Mixed — How-to + Reference. **Not linked from `docs/index.md`.** |
| `lcats/experimental/model_comparison/README.md` | Mixed — Explanation (rationale, layout, methodology) + Reference (tranche results) |
| `lcats/experimental/model_comparison/{anthropic_opus,anthropic_haiku,openai_gpt55,gemini_flash,ollama_gemma4_12b,ollama_deepseek_r1_14b,ollama_gpt_oss_20b,ollama_qwen3_8b,ollama_qwen3_30b_a3b}/README.md` (9 files) | Mixed — How-to (setup/run) + Reference (results) |
| `lcats/experimental/model_comparison/wi_llm_0059/README.md` | Reference (investigation writeup) |
| `lcats/experimental/annotation_feasibility_trial/stats_report.md` | Reference (findings report — recommends a follow-up WI never filed) |
| `lcats/experimental/annotation_feasibility_trial/subset_manifest.md` | Reference (data manifest) |
| `lcats/experimental/secrets_hygiene/README.md` | How-to (properly cross-linked both directions with `docs/how-to/secrets-hygiene.md`) |
| `lcats/experimental/verify_assess_api/README.md` | How-to (small dogfood-check runbook) |

Not classified (data, not documentation): 24
`lcats/experimental/annotation_feasibility_trial/source/trial/*/README.md`
per-story trial metadata files. Out of scope, unchanged from prior
audit: `Papers/Story/kokoMindReadme.md` (third-party dataset README).

### Meta / project-management (not Diataxis-classified)

| Location | Count |
|---|---|
| `lcats/project/` (control plane, all subdirectories) | 803 at commit `88858ae3` (see Key findings above for why this PR's own additions are excluded) |
| `.jules/*`, `lcats/AGENTS.md`, `lcats/STYLE.md`, `lcats/tests/AGENTS.md` | 5 |

Total Markdown files discovered: 880 at commit `88858ae3`. Human-facing/classifiable: 51
(table above). Remainder is Meta (control-plane or agent-instruction
content), per this skill's guardrail against forcing `project/` into
the four quadrants.

## Current project and package layout

```
<repo_root>/
├── README.md                      ← still stale (Phase 2b from 07-07 not done)
├── Papers/, Resources/            ← external reference material (out of scope)
├── corpora/                       ← data only, no docs
├── experiments/                   ← 7 subdirs now (was 2); 04/05 have zero docs/ inbound links
└── lcats/                         ← execution root
    ├── README.md                  ← accuracy fixes landed (unlike repo-root README.md)
    ├── AGENTS.md, STYLE.md
    ├── docs/                      ← human-facing hub, grown substantially since 07-07
    │   ├── index.md, README.md
    │   ├── secrets-setup.md
    │   ├── tutorials/quickstart.md            (new — Phase 4 landed)
    │   ├── how-to/
    │   │   ├── run-assess.md                  (new — Phase 3 landed, but source pointer-ification not done)
    │   │   ├── secrets-hygiene.md             (new, beyond prior plan)
    │   │   └── local-openai-endpoint.md       (new, this session)
    │   ├── reference/
    │   │   ├── cli-status.md                  (has a stale lcats/lcats/ reference)
    │   │   ├── cli-commands.md                (new — Phase 3 landed; missing `annotate`)
    │   │   ├── llm-backend.md                 (new — Phase 3 landed; has 3 stale lcats/lcats/ references)
    │   │   ├── corpus-promotion.md            (new, beyond prior plan)
    │   │   └── gather-overrides.md            (new, beyond prior plan)
    │   └── explanation/
    │       └── story-bucket-layout.md         (new, beyond prior plan)
    ├── project/                   ← LRH control plane (unchanged structure, 803 files at this PR's base commit)
    ├── src/lcats/                 ← importable package — RENAMED from lcats/lcats/ since 07-07
    │   └── analysis/corpus/README.md          ← §9 still has full content + 2 broken links, not pointer-ified
    ├── experimental/              ← NEW since 07-07: model_comparison/, annotation_feasibility_trial/, secrets_hygiene/, verify_assess_api/
    ├── scripts/README.md, tools/README.md (has 4 stale lcats/lcats/ references)
    ├── tests/AGENTS.md
    ├── notebooks/, KMo/            ← unchanged, no docs, not flagged (per prior audit's reasoning)
```

## Diataxis classification

- **Tutorial: resolved.** `docs/tutorials/quickstart.md` closes the
  prior audit's top finding.
- **How-to: substantially grown.** `docs/how-to/` now has 3 pages
  (`run-assess.md`, `secrets-hygiene.md`, `local-openai-endpoint.md`),
  all well-formed. One residual issue: `run-assess.md`'s extraction
  source (`lcats/src/lcats/analysis/corpus/README.md` §9) was never
  turned into a short pointer as the prior audit's Phase 3 scoped, and
  its own links back to `docs/` are broken.
- **Reference: substantially grown, two residual gaps.** `cli-commands.md`
  and `llm-backend.md` both now exist (Phase 3 landed). Gaps: `annotate`
  is undocumented everywhere (cli-status.md, cli-commands.md,
  repo-root README's CLI table all omit it despite full implementation);
  9 stale `lcats/lcats/` path references across 4 files postdate the
  `src/` rename.
- **Explanation: still the thinnest quadrant, and now further behind
  reality.** Only `story-bucket-layout.md` exists as a dedicated
  `docs/explanation/` page. Two bodies of real, evidence-backed work
  have no Explanation-quadrant home: `lcats/experimental/model_comparison/`'s
  cross-provider local-model findings (governing proposal:
  `PROP-ERW-LOCAL-MODEL-EVALUATION`, still `status: proposed` despite
  `implementation_status: partial`), and the corpus-analysis
  architecture content still embedded in `lcats/src/lcats/analysis/corpus/README.md`
  §1–8 (recommended for extraction in the 07-07 plan's target structure,
  not done).
- **Mixed content flagged for splitting, still unresolved:**
  `/README.md` (repo root), `lcats/README.md`,
  `lcats/src/lcats/analysis/corpus/README.md`,
  `experiments/02_llm_backend_comparison/README.md`,
  `docs/secrets-setup.md`. New Mixed content since 07-07:
  `experiments/03_cross_segment_relation_pilot/README.md`,
  `experiments/04_genre_census/README.md`,
  `experiments/05_metadata_genre_prefilter/README.md`,
  `lcats/experimental/model_comparison/README.md` and its 9
  per-candidate READMEs.

## Navigation findings

1. **`lcats/src/lcats/analysis/corpus/README.md` §9 is not pointer-ified,
   and its 2 links back to `docs/` are broken** (see Stale links below).
   The prior audit's Phase 3 recommendation ("extract... leave a short
   pointer in its place") only did the extraction half.
2. **`annotate` has zero documentation** despite being a fully
   implemented subcommand (`lcats/src/lcats/cli.py:252`,
   `add_parser("annotate", ...)`) with real usage evidence in
   `lcats/experimental/annotation_feasibility_trial/` and resolved work
   items `WI-ANNOTATE-0050`/`WI-ANNOTATE-0054`. Absent from
   `docs/reference/cli-status.md`'s implemented-commands list,
   `docs/reference/cli-commands.md`'s command sections (verified: `grep
   -c annotate` on both returns 0), and the repo-root `README.md` CLI
   table.
3. **`experimental/model_comparison/`'s findings have exactly one
   inbound `docs/` cross-reference** (`docs/how-to/local-openai-endpoint.md`,
   this session) and no Explanation-quadrant synthesis page. The
   tranche-1 cross-provider table, the per-candidate failure-mode
   findings (silent-ignore vs. active-filter-rejection tool-call
   failures), and the governing proposal are real, substantial, and
   still effectively invisible from `docs/` except through that one new
   link.
4. **`experiments/04_genre_census/` and `experiments/05_metadata_genre_prefilter/`
   have zero inbound links from `docs/index.md`**, unlike
   `experiments/03_cross_segment_relation_pilot/`, which is linked.
   Both are real, recently-landed work (04 backs `WI-ASSESS-0051`; 05
   backs the just-merged `WI-GENRE-0004`, commit `777ef336`).
5. **`experimental/annotation_feasibility_trial/` surfaced a real
   correctness bug with no tracking work item.** Its own
   `stats_report.md` recommends filing a follow-up WI for a
   segmentation offset-corruption defect
   (`text_segmenter.py`'s `build_paragraph_index`/`align_segment`, on
   single-newline-paragraph stories); no such item exists in
   `project/work_items/{proposed,active}/`. This is distinct from the
   already-tracked "paragraph-mis-numbering root cause still unknown"
   backlog entry (commit `88858ae3`) — a different alignment-failure
   category. Not a docs gap; noted for the user to decide whether it
   warrants a separate `/lrh-work-item` action outside this audit.

## Accuracy findings

1. **9 stale `lcats/lcats/` → `lcats/src/lcats/` path references**,
   all postdating the package rename:
   - `lcats/docs/reference/llm-backend.md` lines 3, 10, 15 (prose and
     the package-layout code block header)
   - `lcats/docs/reference/cli-status.md` line 3
   - `experiments/README.md` line 33 (a table cell)
   - `lcats/tools/README.md` lines 16, 19, 22, 112 (usage examples and a
     "Normalized" path example)
2. **Repo-root `/README.md` did not receive the Phase 2b accuracy fixes
   the prior audit scoped for it.** Still says "Python 3.6+" (line 166)
   and "OpenAI API key (for LLM features)" (line 168, no Anthropic
   mention), and its CLI table (lines ~261–286) omits `promote`,
   `clean`, and `annotate` — 9 of 12 implemented commands listed, up
   from 4 of 13 at the prior audit, but still incomplete.
   `lcats/README.md`'s equivalent issues (Python version wording,
   pytest-via-conda) were fixed; this file was not.
3. **Verified accurate, no action needed:** `docs/reference/cli-status.md`'s
   implemented/placeholder split (aside from the missing `annotate`
   line) still matches the CLI surface; `docs/how-to/local-openai-endpoint.md`
   and `docs/reference/llm-backend.md`'s new `base_url` documentation
   (this session's fix) are accurate against
   `lcats/src/lcats/llm/openai_backend.py`; `docs/tutorials/quickstart.md`
   was independently spot-checked against its own claim that every
   command was run for real.

## Stale or ambiguous links

Method: every `[text](path)` link across all 880 Markdown files at
commit `88858ae3` (this PR's base commit — see Key findings above) was
extracted — 218 total. Of those, HTTP(S)/mailto targets and
pure-fragment (`#section`-only) links were excluded, leaving 96 non-HTTP
path targets subject to a filesystem existence check; `file.md#section`
links were checked against `file.md` only, with paths resolved relative
to the containing file's directory. This surfaces **4 real broken links
and 2 false positives** — both are prose describing the link-check
methodology itself, not real links: this audit's own prior 2026-07-07
edition, and an execution record that already notes it's a known false
positive. This artifact's own embedded validation script (below) is
deliberately excluded from the count it describes, for the same reason
the file-count methodology is pinned to a fixed commit rather than "the
tree including this file" — see Key findings above.

Real broken links:

1. `lcats/project/design/proposals/adopted/worldcon-fast-path-annotation/README.md:25`
   → `../../../../workstreams/proposed/WS-WORLDCON-FAST-PATH-ANNOTATION.md`.
   The workstream has since moved to
   `lcats/project/workstreams/resolved/WS-WORLDCON-FAST-PATH-ANNOTATION.md`;
   the link was never updated when it resolved.
2. `lcats/project/work_items/resolved/WI-STATS-0049.md:65` →
   `lcats/project/design/proposals/adopted/lcats-story-bucket-layout/00_proposal.md`.
   Written as if absolute-from-repo-root but resolved relative to the
   containing directory (`project/work_items/resolved/`), so it
   resolves to a nonexistent nested path.
3. `lcats/src/lcats/analysis/corpus/README.md:231` →
   `../../../docs/how-to/run-assess.md` — one `../` short. The file now
   lives 4 directories below `lcats/` (`src/lcats/analysis/corpus/`),
   not 3; the link wasn't updated when the `src/` level was inserted by
   the rename.
4. `lcats/src/lcats/analysis/corpus/README.md:233` →
   `../../../docs/reference/cli-commands.md` — same issue as #3.

## Project-control-plane vs human-docs boundary

Unchanged from the prior audit's assessment: `lcats/README.md`'s
"Documentation" section still separates "Docs hub" from "LRH
control-plane docs" with a link to `project/README.md`. One new
instance of the same traceability gap the prior audit flagged for the
LLM-backend workstream: `PROP-ERW-LOCAL-MODEL-EVALUATION` and
`experimental/model_comparison/` now have a docs/ entry point
(`docs/how-to/local-openai-endpoint.md`, this session), but no
Explanation-quadrant page carries the fuller narrative (methodology,
per-candidate results, the two real tool-calling failure modes found)
the way `docs/explanation/story-bucket-layout.md` does for its subject.

## Recommended target documentation structure

Do not implement in this operation — for `/lrh-doc-organize` to scope:

```
lcats/docs/
├── reference/
│   ├── cli-status.md               (fix: add annotate; fix stale lcats/lcats/ reference)
│   ├── cli-commands.md             (fix: add annotate section)
│   └── llm-backend.md              (fix: 3 stale lcats/lcats/ references)
└── explanation/
    ├── story-bucket-layout.md      (existing)
    ├── local-model-evaluation.md   (new — synthesize experimental/model_comparison/ + PROP-ERW-LOCAL-MODEL-EVALUATION)
    └── corpus-analysis-architecture.md  (new — extract §1-8 of the corpus README, still not done since 07-07)
```

Repo-root `/README.md` should receive the same accuracy-fix treatment
`lcats/README.md` already got (Python version, provider description,
complete CLI table) — this was scoped in the prior audit's Phase 2b and
still hasn't landed.

## Recommended phased PRs

### Phase 2c (post-rename + link cleanup, no content authored — lowest risk)
- Fix the 4 real broken links (exact locations above).
- Fix the 9 stale `lcats/lcats/` → `lcats/src/lcats/` path references.
- Turn `lcats/src/lcats/analysis/corpus/README.md` §9 into a short
  pointer to `docs/how-to/run-assess.md` (closes out the prior audit's
  half-done Phase 3 item).
- Add `annotate` (and confirm `promote`/`clean`) to
  `docs/reference/cli-status.md`, `docs/reference/cli-commands.md`, and
  the repo-root `README.md` CLI table.

### Phase 2d (accuracy fixes, repo-root README specifically)
- Apply the Phase 2b fixes the prior audit scoped but that never landed
  on `/README.md`: Python version wording, mention both LLM providers
  (not OpenAI-only).

### Phase 5 (navigation — link recent experiments/experimental work into the hub)
- Add links from `docs/index.md` to `experiments/04_genre_census/README.md`
  and `experiments/05_metadata_genre_prefilter/README.md`.

### Phase 6 (new Explanation content — requires authored prose, bigger)
- Write `docs/explanation/local-model-evaluation.md` synthesizing
  `experimental/model_comparison/`'s findings and
  `PROP-ERW-LOCAL-MODEL-EVALUATION`.
- Extract `lcats/src/lcats/analysis/corpus/README.md` §1–8 into
  `docs/explanation/corpus-analysis-architecture.md` (recommended by the
  07-07 audit, still not done).

## Proposed first PR scope

Scope Phase 2c only — link/path/reference fixes with no new prose
authored, matching this audit's lowest-risk, highest-confidence
findings, mirroring the prior audit's Phase 2a precedent:

1. Fix the 4 real broken links:
   `worldcon-fast-path-annotation/README.md:25` (retarget to
   `resolved/WS-WORLDCON-FAST-PATH-ANNOTATION.md`), `WI-STATS-0049.md:65`
   (fix the relative path depth), and
   `lcats/src/lcats/analysis/corpus/README.md:231,233` (add the missing
   `../`).
2. Fix the 9 stale `lcats/lcats/` → `lcats/src/lcats/` references in
   `docs/reference/llm-backend.md` (3), `docs/reference/cli-status.md`
   (1), `experiments/README.md` (1), `lcats/tools/README.md` (4).
3. Add `annotate` to `docs/reference/cli-status.md`'s implemented-commands
   list and as a new section in `docs/reference/cli-commands.md`,
   verified against `lcats annotate --help`.
4. Add `promote`, `clean`, and `annotate` to the repo-root `README.md`
   CLI table, and update its LLM-provider line to mention both Anthropic
   and OpenAI.
5. Turn `lcats/src/lcats/analysis/corpus/README.md` §9 into a short
   pointer to `docs/how-to/run-assess.md` (the extraction target already
   exists — this closes out the half-done Phase 3 item, item 1's fix to
   this file's broken links makes the pointer's own links correct too).
6. Add one link each from `docs/index.md` to
   `experiments/04_genre_census/README.md` and
   `experiments/05_metadata_genre_prefilter/README.md` — navigation
   only, no new prose.

Deliberately deferred (bigger, needs authored content, not
navigation/accuracy-only): `docs/explanation/local-model-evaluation.md`,
`docs/explanation/corpus-analysis-architecture.md`, and filing the
missing follow-up work item for the `annotation_feasibility_trial`
segmentation bug (a work-item action, not a docs PR — separate from
this skill's scope).

## Risks and cautions

- **This audit's own "missing convention source file" risk from
  2026-07-07 still applies unchanged**: `docs/reference/docs-audit-artifact-convention.md`
  still does not exist anywhere in the repository. This audit again
  followed the schema summarized directly in the `lrh-doc-audit` skill's
  own `references/audit-requirements.md`. Not fixed here per the
  "do not create content" guardrail.
- **Package-rename staleness is a live, recurring risk class, not a
  one-time fix.** The 9 `lcats/lcats/` references and the corpus
  README's 2 broken links are both direct casualties of the same
  `lcats/lcats/` → `lcats/src/lcats/` rename. Any future directory-depth
  change to the package layout should be paired with a repo-wide grep
  for the old path in docs prose and relative links, not just code
  imports.
- **`annotation_feasibility_trial`'s unfixed segmentation bug** is
  flagged here as a discovery, not resolved — the user should decide
  separately whether to run `/lrh-work-item` for it; this audit does not
  create it.
- **`PROP-ERW-LOCAL-MODEL-EVALUATION` remains `status: proposed`**
  despite `implementation_status: partial` and 9+ resolved work items
  citing it. A reader following `docs/how-to/local-openai-endpoint.md`'s
  link lands on a proposal document describing work that has already
  substantially shipped — worth the proposal's owner reconciling status
  separately; out of scope for a docs-only fix.
- Section 9 of the corpus README (targeted for pointer-ification in
  item 5 above) should be a copy-and-link, not a rewrite of
  `docs/how-to/run-assess.md`'s already-reviewed content — same caution
  the 07-07 audit gave when the extraction itself was scoped.
- **A docs audit's own headline counts cannot include itself, and
  attempting to "recompute against the finalized tree" doesn't fix
  this — it relocates the same bug one commit later.** This was found
  live on this PR: the first fix recomputed counts against "the tree
  including this audit and its self-review record," but the fix commit
  itself (plus the execution record documenting the fix) added more
  files the recomputed numbers didn't include — the identical
  before/after-commit mismatch the original review comment flagged, one
  level deeper. The only stable fix is pinning every count in this
  artifact to a fixed commit SHA that predates the artifact's own
  existence (here, `88858ae3`, this PR's base commit) rather than
  chasing "the finalized tree" as a moving target. Any future docs audit
  should adopt the same convention from the start — pin to the base
  commit, not "as of this write" — to avoid rediscovering this.

## Validation commands for follow-up PRs

```bash
# Re-run this audit's link check after any docs PR
python3 -c "
import re, os
link_re = re.compile(r'\[([^\]]*)\]\(([^)]+)\)')
broken = []
for dirpath, _, filenames in os.walk('.'):
    if '.git' in dirpath.split(os.sep):
        continue
    for fn in filenames:
        if not fn.endswith('.md'):
            continue
        f = os.path.join(dirpath, fn)
        for i, line in enumerate(open(f, encoding='utf-8', errors='replace'), 1):
            for m in link_re.finditer(line):
                target = m.group(2).strip()
                if target.startswith(('http://', 'https://', 'mailto:', '#')):
                    continue
                path_part = target.split('#')[0].strip('<>')
                if not path_part:
                    continue
                resolved = os.path.normpath(os.path.join(os.path.dirname(f), path_part))
                if not os.path.exists(resolved):
                    broken.append((f, i, target))
print(f'{len(broken)} broken links'); [print(b) for b in broken]
"

# Verify no stale lcats/lcats/ references remain in docs prose
grep -rn "lcats/lcats/" lcats/docs/ experiments/README.md lcats/tools/README.md

# Verify the CLI status/commands docs list every implemented subcommand
grep -n 'add_parser(' lcats/src/lcats/cli.py
grep -c "annotate" lcats/docs/reference/cli-status.md lcats/docs/reference/cli-commands.md README.md

# Verify lrh validate accepts this audit artifact
lrh validate
```
