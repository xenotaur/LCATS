---
id: AUDIT-DOCS-2026-07-07
audit_type: docs
schema_version: 1
status: proposed
repo_root: .
project_root: lcats
docs_root: lcats/docs
control_root: lcats/project
package_roots: ["lcats/lcats"]
framework: diataxis
recommended_next_prompt: organize_docs
recommended_phase: phase-2-reference-and-navigation
---

## Summary

This is a follow-up audit to [`2026-05-26-docs-audit.md`](2026-05-26-docs-audit.md). That
audit's Phase 1 ("scaffold") landed: `lcats/docs/` now exists with an index page and an accurate
CLI status matrix, and `lcats/README.md` links to both. Phases 2 (reference normalization) and 3
(tutorial gap closure) from that plan have not started — no work item currently tracks them.

Since the prior audit, one large workstream closed (`WORKSTREAM-LLM-BACKEND`, unified Anthropic +
OpenAI backend) and a new CLI command (`lcats assess`) shipped with substantial how-to content
added directly to `lcats/lcats/analysis/corpus/README.md`. That content is not linked from the
docs hub.

Key findings:
- 78 Markdown files existed in the repository at the start of this audit's discovery pass (before
  this artifact was written); the repository now contains 79 including this file. 0 broken
  internal links (verified by filesystem check against every non-HTTP link target).
- **Tutorial quadrant is empty** — `docs/index.md` explicitly states tutorials are not scaffolded.
  This matches actual repository state (no `docs/tutorials/` directory exists).
- **The top-level repository README (`/README.md`) is stale and disconnected** from the
  `lcats/docs/` hub built in Phase 1. It undercounts the CLI surface by 6 of 13 commands and
  describes LLM integration as OpenAI-only, though an Anthropic backend has existed since
  `WI-LLM-0007` closed.
- **`docs/secrets-setup.md` is orphaned** — not linked from `docs/index.md`, `docs/README.md`, or
  `docs/reference/README.md`, despite living inside the docs hub.
- **How-to content exists but isn't in `docs/how-to/`** — the newest and most detailed how-to
  content in the repo (`lcats assess` usage, manual prompt validation, dry-run) lives in Section 9
  of the corpus-analysis README, an Explanation-dominant document. `docs/index.md`'s "How-to
  guides" section says "not scaffolded," which is no longer accurate.
- No reference doc exists for CLI flags/options per subcommand, or for the `LLMBackend`
  Protocol/provider surface added by the now-closed LLM backend workstream.

## Scope and roots inspected

- `repo_root` (`.`): top-level repository containing `Papers/`, `Resources/`, `corpora/`,
  `experiments/`, and the nested `lcats/` execution root. No `docs/` or `project/` exists at this
  level — both live nested under `lcats/`.
- `project_root` / execution root (`lcats/`): the active Python project (`pyproject.toml`,
  `setup.py`), containing the `lcats` package, `docs/`, `project/`, `scripts/`, `tools/`, `tests/`,
  `notebooks/`, `KMo/`.
- `docs_root` (`lcats/docs/`): human-facing documentation hub, scaffolded 2026-05-27.
- `control_root` (`lcats/project/`): LRH control-plane, 19 subdirectories, actively maintained
  (most recent execution record dated 2026-07-05).
- `package_roots` (`lcats/lcats/`): the importable `lcats` package. One subsystem-level README at
  `lcats/lcats/analysis/corpus/README.md`; no other package-level READMEs.
- Also inspected: `experiments/` (sibling to `lcats/`, per `STYLE.md`'s documented repo layout —
  correctly placed outside the execution root), `.github/workflows/` (CI, not docs), `Papers/` and
  `Resources/` (external reference material collections, out of scope for this audit — not
  project-authored documentation).

Discovery method: recursive filesystem walk for `*.md`, cross-checked against the discovery
checklist in the `lrh-doc-audit` skill's `references/audit-requirements.md` (this is the invoking
skill's own reference material — not a path inside this repository) covering docs directories,
top-level meta files, package READMEs, examples/notebooks, CLI surface via `lcats/lcats/cli.py`
source inspection, docstring presence via AST walk, and the control-plane directory.

## Current documentation inventory

### Human-facing documentation (Diataxis-eligible)

| File | Quadrant |
|---|---|
| `/README.md` (repo root) | Mixed (tutorial + how-to + reference + explanation) |
| `lcats/README.md` | Mixed (how-to install/build + thin reference + links to hub) |
| `lcats/docs/README.md` | Meta (navigational landing page) |
| `lcats/docs/index.md` | Meta (navigational — Diataxis map) |
| `lcats/docs/reference/README.md` | Reference (index) |
| `lcats/docs/reference/cli-status.md` | Reference |
| `lcats/docs/secrets-setup.md` | Mixed, How-to dominant (setup steps + a short "why" explanation section) |
| `lcats/scripts/README.md` | Mixed, Reference dominant (per-script option reference with usage recipes) |
| `lcats/tools/README.md` | Mixed, Reference dominant (tool inventory + usage) |
| `lcats/tools/templates/improve_coverage.md` | How-to (AI-agent task template) |
| `lcats/lcats/analysis/corpus/README.md` | **Mixed — flag for splitting.** Sections 1–8 are Explanation (design principles, architecture, data flow, implemented/planned split). Section 9 (`lcats assess`) is How-to (usage recipes, manual validation checklist, dry-run instructions). |
| `experiments/README.md` | Explanation (directory convention + asset placement rationale) |
| `experiments/01_classify_corpora/README.md` | Not read in full this pass — Reference/How-to (experiment description) |
| `experiments/01_classify_corpora/dataset/README.md` | Not read in full this pass — Reference (dataset description) |
| `experiments/01_classify_corpora/results/README.md` | Not read in full this pass — Reference (results description) |
| `experiments/02_llm_backend_comparison/README.md` | Mixed — How-to (run instructions, manual smoke test) + Reference (baseline results tables) |

### Meta / project-management (not Diataxis-classified, per this skill's convention)

| Location | Count | Examples |
|---|---|---|
| `lcats/AGENTS.md`, `lcats/tests/AGENTS.md` | 2 | Agent operating instructions |
| `lcats/STYLE.md` | 1 | Canonical style guide |
| `lcats/project/` (control plane, all subdirectories) | ~54 | `README.md`, `audits/*` (3), `context/*` (2), `contributors/*` (2), `design/*` (4), `evidence/*` (1), `executions/*` (12), `focus/*`, `goal/*`, `guardrails/*` (4), `memory/*`, `principles/*`, `prompts/*` (2), `roadmap/*`, `status/*`, `work_items/*` (12), `workstreams/*` (1) |

Total Markdown files discovered: 78 (pre-existing state, before this audit artifact was written;
the repository now contains 79 including this file). Total classified into Diataxis quadrants
(including Mixed): 17. Remainder (~61) is control-plane Meta content, consistent with this skill's
guardrail to not force `project/` into the four quadrants.

Not discovered anywhere in the repository: a `docs/reference/docs-audit-artifact-convention.md`
file. The `lrh-doc-audit` skill's own `references/audit-requirements.md` (not a file in this
repository) names `docs/reference/docs-audit-artifact-convention.md` as the authoritative in-repo
source for the v1 artifact schema, but no such file exists here (searched full tree). This audit
follows the schema as summarized directly in the skill's `audit-requirements.md` instead. Flagged
under Risks and Cautions.

## Current project and package layout

```
<repo_root>/
├── README.md                      ← stale, disconnected from lcats/docs/
├── Papers/, Resources/            ← external reference material (out of scope)
├── corpora/                       ← data only, no docs
├── experiments/                   ← README.md + per-experiment READMEs (in scope, correctly placed)
└── lcats/                         ← execution root
    ├── README.md                  ← links to docs hub (Phase 1 output)
    ├── AGENTS.md, STYLE.md        ← meta/contributor guidance
    ├── docs/                      ← human-facing hub (new, Phase 1 output)
    │   ├── index.md, README.md
    │   ├── secrets-setup.md       ← orphaned from index.md
    │   └── reference/
    │       ├── README.md
    │       └── cli-status.md      ← accurate, verified against cli.py
    ├── project/                   ← LRH control plane (19 subdirs, actively maintained)
    ├── lcats/                     ← importable package
    │   └── analysis/corpus/README.md  ← only package-level README; Mixed content
    ├── scripts/README.md
    ├── tools/README.md, tools/templates/
    ├── tests/AGENTS.md
    ├── notebooks/                 ← 17 notebooks, no README, no doc coverage
    └── KMo/                       ← 3 legacy scripts, no README
```

`lcats/notebooks/` and `lcats/KMo/` contain code with no accompanying documentation of any kind
(not even a README). `AGENTS.md` explicitly instructs agents not to edit notebooks unless asked,
which is consistent with treating them as legacy/exploratory rather than a documentation gap to
close — noted, not flagged as a gap.

## Diataxis classification

- **Tutorial: absent.** `docs/index.md` states "Tutorials are not scaffolded in this phase," and
  no `docs/tutorials/` directory exists. The top-level `/README.md` "Quick Start" section is the
  closest thing to a tutorial in the repository, but it is a Quick Start embedded in a Mixed
  README, not a standalone, reproducible, complete-outcome walkthrough.
- **How-to: thin and split across two locations.** `docs/how-to/` does not exist. The most
  substantial how-to content in the repository — `lcats assess` usage, spot-check workflow,
  dry-run — lives in Section 9 of `lcats/lcats/analysis/corpus/README.md`, not in the docs hub.
  `docs/secrets-setup.md` is a second, orphaned how-to page. `scripts/README.md` and
  `tools/README.md` contain how-to content but are Reference-dominant.
- **Reference: growing, but incomplete.** `docs/reference/cli-status.md` is accurate (verified
  directly against `lcats/lcats/cli.py` subparsers — all 13 commands match). No reference exists
  for individual command flags/options, for the `LLMBackend` Protocol and its two providers
  (`anthropic_backend.py`, `openai_backend.py`), or for the package's public API surface (`Story`,
  `Corpora`, `Pipeline`, `ExtractionTemplate`, etc. — referenced only in the top-level `/README.md`
  Python API example).
- **Explanation: the strongest quadrant, but concentrated in one file.** `lcats/lcats/analysis/
  corpus/README.md` Sections 1–8 are a well-structured explanation of the corpus-analysis
  subsystem, including an explicit implemented/planned/deferred split. Outside that file, human-
  facing explanation content is essentially absent — the LRH `project/` directory carries
  equivalent conceptual weight (design rationale, architecture decisions) but is classified as
  Meta per this skill's convention, not Explanation, so it doesn't count toward this quadrant. See
  "Project-control-plane vs human-docs boundary" below.
- **Mixed content flagged for splitting:** `/README.md` (repo root), `lcats/README.md`,
  `lcats/lcats/analysis/corpus/README.md`, `experiments/02_llm_backend_comparison/README.md`,
  `docs/secrets-setup.md`.

## Navigation findings

1. **`/README.md` (repo root) does not link to `lcats/docs/`, `lcats/project/`, `lcats/STYLE.md`,
   or `lcats/AGENTS.md` anywhere.** A visitor landing on the GitHub repo root — the most likely
   entry point — has no path to the Phase 1 docs hub or the control plane. `grep` for `docs/`,
   `docs hub`, `Diátaxis`, and `Diataxis` in `/README.md` returns zero matches.
2. **`docs/secrets-setup.md` is unreachable from the docs hub.** Neither `docs/index.md`,
   `docs/README.md`, nor `docs/reference/README.md` links to it. The only inbound links found
   repo-wide are from `project/executions/` and `project/work_items/resolved/WI-INFRA-0011.md` —
   control-plane records, not the human-facing hub.
3. **`docs/index.md`'s "How-to guides" section is stale.** It reads "How-to guides are not
   scaffolded in this phase," written at Phase 1 (2026-05-27). Since then, `lcats assess` how-to
   content was added directly to the corpus README (commits `a5caa75`, `8253e7e`, `3e37311`) and
   `docs/secrets-setup.md` (a how-to page) was added by `WI-INFRA-0011`. The index page was not
   updated to reflect either.
4. **No work item currently tracks Phase 2 or Phase 3 of the prior audit's plan.** `project/
   work_items/active/` and `project/work_items/proposed/` contain no items referencing docs,
   reference normalization, or tutorials. Per this skill's guardrail to distinguish planned from
   implemented: this is a **gap**, not a **planned** item — there is no evidence of intent to
   execute Phase 2/3 beyond the prior audit's own recommendation.

## Accuracy findings

1. **`/README.md` (repo root) CLI command table is stale.** It lists 4 implemented commands
   (`help`, `info`, `gather`, `inspect`) and 3 planned (`index`, `advise`, `eval`) — 7 total. The
   actual CLI (`lcats/lcats/cli.py`, cross-checked against `docs/reference/cli-status.md`) has 13:
   the same 7, plus `display`, `survey`, `assess`, `stats`, `repair-specials`, and `meta register`,
   all implemented. `docs/reference/cli-status.md` (Phase 1 output) is accurate and does not have
   this problem.
2. **`/README.md` (repo root) describes LLM integration as OpenAI-only** ("OpenAI API integration
   for text analysis and extraction," "OpenAI API key (for LLM features)"). `lcats/llm/` contains
   both `anthropic_backend.py` and `openai_backend.py`, and `docs/secrets-setup.md` documents
   setup for both providers. This description predates `WORKSTREAM-LLM-BACKEND` (closed
   2026-07-02) and was not updated when it landed.
3. **`lcats/README.md` Requirements section is stale**, carried over from the prior audit (finding
   still unresolved): "Python > 3.6(ish)" (informal; `pyproject.toml` says `>=3.6`) and
   `conda install -c anaconda pytest` in the Requirements list, while `STYLE.md` §8 states
   "Framework: unittest ONLY" and the canonical test command is `scripts/test`. `pytest` is not
   actually required to run the project's tests.
4. **Verified accurate, no action needed:** `lcats/README.md`'s links to `docs/index.md` and
   `docs/reference/cli-status.md` resolve correctly; the top-level `/README.md`'s Python API
   example (`Story`, `Corpora`, `ExtractionTemplate` from `lcats.stories`/`lcats.extraction`) still
   matches current source; `pip install -e ".[dev]"` in `/README.md` matches a real `dev` extra in
   `pyproject.toml`; `docs/reference/cli-status.md`'s implemented/placeholder split exactly matches
   the 13 subparsers in `cli.py`.
5. **Docstring coverage is high and not a significant gap.** AST walk over `lcats/lcats/` (excluding
   tests) found 410 public functions/classes, 29 without a docstring (~93% coverage) — consistent
   with `STYLE.md` §14's docstring requirement being generally followed. Not flagged as a
   reference gap; the gap is the absence of a *curated* API reference page, not missing docstrings.
6. **`project/executions/README.md` still describes a script that doesn't exist**
   (`scripts/prompts/record-execution`), unchanged since it was written. Executions are being
   recorded manually and consistently (12 execution records exist, most recent 2026-07-05), so the
   convention is working in practice — this is a doc/tooling mismatch, not a process failure.
7. **`project/context/humans.md` and `project/context/agents.md` read as stale.** Both are
   dated/framed as of "2026-04-21" ("LRH artifacts are newly bootstrapped," health "yellow," goals
   framed as not-yet-started RAG/CBR work). Since then a full LLM-backend workstream and the
   `assess` command have shipped. These are explicitly marked "non-authoritative, derived" so this
   is lower severity, but they are stale enough to actively mislead an agent or contributor reading
   them first, per the read-order in `agents.md` itself.

## Stale or ambiguous links

None found. Every non-HTTP `[text](path)` link across all Markdown files in the repository (78 at
the time of the discovery pass) was checked against the filesystem (fragment-only links skipped,
`file.md#section` links checked against `file.md` only, paths resolved relative to the containing
file's directory). Zero broken targets. The check was re-run after this file was added to the
tree, against all 79 files, with the same result.

This is a change from what an audit of this repository might have found before: the Phase 1 docs
work introduced correct relative links (e.g., `lcats/docs/index.md` → `../project/README.md`),
and no regressions have been introduced since.

## Project-control-plane vs human-docs boundary

- The boundary is now partially documented: `lcats/README.md`'s "Documentation" section explicitly
  separates "Docs hub" from "LRH control-plane docs" with a link to `project/README.md`. This
  resolves part of finding #1 from the prior audit ("boundary clarity issue").
- However, `docs/index.md`'s Explanation section links to `project/README.md` as if it were a
  single explanation page; it does not mention that `project/` contains 19 subdirectories and ~54
  files. A reader following that link finds a short pointer document (`project/README.md`, 22
  lines) rather than the "Explanation" depth the docs map implies.
- Traceability between control-plane artifacts and code remains informal: `project/design/
  unified-llm-backend-design.md` describes the `LLMBackend` design, and the workstream is closed
  (`project/workstreams/resolved/WORKSTREAM-LLM-BACKEND.md`), but nothing in `docs/reference/`
  points a documentation reader from "I want to know how LLM backends work" to that design doc or
  to the experiment results in `experiments/02_llm_backend_comparison/README.md`. This repeats
  finding #2 ("Traceability issue") from the prior audit — it has not been addressed for this new
  subsystem.
- `project/audits/` previously stored all audit artifacts as flat files. This audit adopts a
  `project/audits/docs/` subdirectory for docs-specific audits (per this skill's required output
  path) and relocates `2026-05-26-docs-audit.md` into it alongside this file, so future docs
  audits have a single, unambiguous home. Non-docs audits (`2026-06-16-special-character-cleanup-
  workstream-audit.md`, `2026-06-18-phase-4-repair-review-application-integration-audit.md`) stay
  in the flat `project/audits/` layout — this convention applies only to `audit_type: docs`.

## Recommended target documentation structure

Do not implement in this operation — for `/lrh-doc-organize` to scope:

```
lcats/docs/
├── index.md                          (update: fix stale "not scaffolded" claims; add secrets-setup.md; link how-to content)
├── README.md
├── tutorials/
│   └── quickstart.md                 (new — extract/rewrite from /README.md and lcats/README.md Quick Start sections)
├── how-to/
│   ├── run-assess.md                 (new — extract Section 9 from lcats/lcats/analysis/corpus/README.md)
│   ├── set-up-api-keys.md            (move from docs/secrets-setup.md, or link it in properly)
│   └── run-tests-lint-format.md      (new — extract from scripts/README.md)
├── reference/
│   ├── README.md
│   ├── cli-status.md                 (keep — accurate)
│   ├── cli-commands.md               (new — per-command flags/options, generated or hand-verified against --help)
│   └── llm-backend.md                (new — Protocol + provider reference, derived from unified-llm-backend-design.md)
└── explanation/
    ├── control-plane.md              (new — what project/ is, pointing into its 19 subdirectories)
    ├── corpus-analysis-architecture.md  (new — Sections 1–8 of the corpus README, relocated/linked)
    └── llm-backend-design.md         (new — link/derive from project/design/unified-llm-backend-design.md)
```

Repo-root `/README.md` should either become a short pointer (mirroring how `lcats/README.md`
points into `docs/`) or be actively resynced with `lcats/docs/reference/cli-status.md` so its CLI
table and provider description stop drifting. Given it's the GitHub-visible landing page, resync
plus a link into the docs hub is likely lower-risk than a full rewrite.

## Recommended phased PRs

### Phase 2a (navigation fixes, no content authored — lowest risk)
- Link `docs/secrets-setup.md` from `docs/index.md` and `docs/reference/README.md`.
- Update `docs/index.md`'s How-to section to point at the existing `lcats assess` how-to content
  (Section 9 of the corpus README) instead of claiming "not scaffolded."
- Add a `lcats/docs/` link and a corrected CLI command count to `/README.md` (repo root).

### Phase 2b (accuracy fixes)
- Fix `/README.md`'s CLI command table (add the 6 missing commands) and LLM-provider description
  (mention Anthropic alongside OpenAI).
- Fix `lcats/README.md`'s Requirements section (Python version wording, drop/replace the `pytest`
  via-conda line to match `STYLE.md`'s `unittest`-only framework).
- Update `project/executions/README.md` to stop referencing the nonexistent
  `scripts/prompts/record-execution` helper, or note it's intentionally deferred.

### Phase 3 (reference normalization)
- Extract Section 9 of the corpus README into `docs/how-to/run-assess.md`; leave a short pointer
  in its place.
- Add `docs/reference/cli-commands.md` with per-command flags, verified against `lcats <command>
  --help`.
- Add `docs/reference/llm-backend.md` derived from `project/design/unified-llm-backend-design.md`.

### Phase 4 (tutorial gap closure)
- Add `docs/tutorials/quickstart.md`: environment setup through `scripts/develop` to a first
  `lcats survey` or `lcats assess --dry-run` run, reusing content already proven correct in
  `lcats/README.md` and `docs/secrets-setup.md`.

## Proposed first PR scope

Scope Phase 2a only — navigation fixes with no new content authored, matching this audit's
lowest-risk, highest-confidence findings:

1. Add a "Documentation" pointer section to `/README.md` (repo root) linking to `lcats/docs/
   index.md`, mirroring the section already present in `lcats/README.md`.
2. Add `docs/secrets-setup.md` to `docs/index.md`'s Reference or How-to section (it's a setup
   how-to; place it under a "How-to guides" heading) and to `docs/reference/README.md`.
3. Update `docs/index.md`'s "How-to guides" section to stop saying "not scaffolded" and instead
   point to `lcats/lcats/analysis/corpus/README.md#9-story-assessment-lcats-assess` as an interim
   how-to location, pending Phase 3 extraction.
4. ~~Decide and record whether `project/audits/` stays flat or adopts the `audits/docs/`
   subdirectory.~~ **Resolved as part of this audit's own write:** `project/audits/docs/` is
   adopted for `audit_type: docs` artifacts; `2026-05-26-docs-audit.md` was moved there alongside
   this file, and cross-references in `2026-06-16-special-character-cleanup-workstream-audit.md`
   and `PROMPT-AD_HOC-REQUEST_ORGANIZE_DOCS-2026-05-27-scaffold.md` were updated to the new path.

No other file moves, no deletions, no rewrites of existing accurate content (`docs/reference/
cli-status.md`, `lcats/README.md`'s documentation-links section stay as-is).

## Risks and cautions

- **Missing convention source file.** The `lrh-doc-audit` skill's `references/audit-requirements.md`
  — part of the skill installed at `~/.claude/skills/lrh-doc-audit/`, not a path in this repository
  — names `docs/reference/docs-audit-artifact-convention.md` as the authoritative in-repo v1 schema
  source. No such file exists anywhere in this repository. This audit followed the schema as
  summarized directly in the skill's own `audit-requirements.md` instead. If a repo-local copy of
  the convention file is expected to exist here, its absence is itself a documentation gap worth
  raising separately — not fixed here, per this skill's "do not create content" guardrail.
- **Audit output path adopts a new subdirectory convention, scoped to `audit_type: docs`.**
  `project/audits/docs/` now holds this audit and the relocated `2026-05-26-docs-audit.md`. Non-
  docs audits (2026-06-16, 2026-06-18) intentionally remain in the flat `project/audits/*.md`
  layout — do not move them as part of a future docs-organize PR.
- **`/README.md` (repo root) is the GitHub-visible landing page** — any edit to its CLI table or
  provider description should be double-checked against `docs/reference/cli-status.md` at PR time
  (not just at audit time), since CLI surface area has changed twice in the last two months
  (`assess` added, `meta register` added).
- **`project/context/humans.md` / `agents.md` staleness is a control-plane concern, not a docs-hub
  concern** — flagged here for completeness (Accuracy findings #7) but out of scope for
  `/lrh-doc-organize`, which operates on `docs_root`, not `control_root`.
- Section 9 of the corpus README is very recent (three commits in the current session before this
  audit). Extracting it into `docs/how-to/` in Phase 3 should be a copy-and-link, not a rewrite —
  the content itself was evidently reviewed carefully (verdict tables, spot-check guidance) and a
  future PR should preserve it rather than reauthor it.

## Validation commands for follow-up PRs

```bash
# Re-run this audit's link check after any docs PR
cd lcats && python3 -c "
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
print(f'{len(broken)} broken links') ; [print(b) for b in broken]
"

# Verify the CLI status matrix still matches the implemented CLI surface
cd lcats && grep -n 'add_parser(' lcats/cli.py

# Verify no stale Python-version / pytest wording reintroduced
cd lcats && grep -n "3.6(ish)\|conda install -c anaconda pytest" README.md

# Verify lrh validate accepts this audit artifact
lrh validate
```
