# Work Items Directory

This directory tracks actionable execution units aligned to the current roadmap.

## Layout
- `active/` contains currently in-progress items (`status: active`).
- `proposed/` contains planned/future items (`status: proposed`).
- `resolved/` contains completed items (`status: resolved`).
- `abandoned/` contains items that will not be pursued (`status: abandoned`).

YAML frontmatter is authoritative for metadata, and directory buckets are kept aligned with the `status` field.

## Active Items
- (none)

## Proposed Items
- `proposed/WI-PERSIST-0004.md`
- `proposed/WI-META-0023.md` — Remove LRH meta-registry duplication from LCATS codebase and docs

## Abandoned Items
- `abandoned/WI-META-0006.md` — superseded by native LRH functionality (`lrh meta register`); reversed by WI-META-0023

## Resolved Items
- `resolved/WI-REPAIR-0001.md`
- `resolved/WI-SPANOPS-0002.md` — span-op model; superseded by the shipped rule/override/allowlist pipeline (2026-07-18 decision log)
- `resolved/WI-REVIEW-0003.md` — human review/override model; superseded, see above
- `resolved/WI-APPLY-0005.md` — safe span-op application; superseded, see above
- `resolved/WI-LLM-0007.md` — Create `lcats/llm/` package (Protocol + backends)
- `resolved/WI-LLM-0008.md` — Migrate `JSONPromptExtractor` to `LLMBackend`
- `resolved/WI-LLM-0009.md` — Migrate `assess.py` / `assess_cli.py` to `LLMBackend`
- `resolved/WI-LLM-0010.md` — Side-by-side model comparison dry run
- `resolved/WI-INFRA-0011.md` — Add secrets utility and contributor guide for `.secrets/` pattern
- `resolved/WI-ASSESS-0012.md` — Extend `lcats assess` with optional `--genre` and always-on genre detection
- `resolved/WI-DOCS-0013.md` — Fix accuracy issues in repo-root README.md and lcats/README.md
- `resolved/WI-DOCS-0014.md` — Normalize CLI, LLM-backend, and assess reference docs
- `resolved/WI-DOCS-0015.md` — Add a quickstart tutorial
