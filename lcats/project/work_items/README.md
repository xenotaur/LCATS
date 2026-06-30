# Work Items Directory

This directory tracks actionable execution units aligned to the current roadmap.

## Layout
- `active/` contains currently in-progress items (`status: active`).
- `proposed/` contains planned/future items (`status: proposed`).
- `resolved/` contains completed items (`status: resolved`).

YAML frontmatter is authoritative for metadata, and directory buckets are kept aligned with the `status` field.

## Active Items
- `active/WI-SPANOPS-0002.md`
- `active/WI-REVIEW-0003.md`
- `active/WI-APPLY-0005.md`
- `active/WI-META-0006.md`
- `active/WI-LLM-0007.md` — Create `lcats/llm/` package (Protocol + backends)

## Proposed Items
- `proposed/WI-PERSIST-0004.md`
- `proposed/WI-LLM-0008.md` — Migrate `JSONPromptExtractor` to `LLMBackend`
- `proposed/WI-LLM-0009.md` — Migrate `assess.py` / `assess_cli.py` to `LLMBackend`
- `proposed/WI-LLM-0010.md` — Side-by-side model comparison dry run

## Resolved Items
- `resolved/WI-REPAIR-0001.md`
