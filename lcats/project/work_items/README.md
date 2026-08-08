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
- `proposed/WI-PERSIST-0004.md` — Design persistence layer for corpus state and operation history
- `proposed/WI-EVENT-0030.md` — Run stratified cross-segment relation density pilot across genres
- `proposed/WI-ASSESS-0051.md` — Run current-classifier full-corpus genre survey (Gap 2)
- `proposed/WI-EVENT-0032.md` — Harden Event-Role-World tool-schema reliability and processor error/model handling
- `proposed/WI-EVENT-0033.md` — Add schema-hardened structured output to scene/story analysis extractors
- `proposed/WI-RELEASE-0037.md` — Resolve gutenbergpy VCS-pin PyPI-publish blocker
- `proposed/WI-RELEASE-0039.md` — Pre-launch verification of the gutenbergpy dependency resolution before real PyPI publish
- `proposed/WI-STORY-0042.md` — Make LCATS story discovery and identity dual-layout-compatible
- `proposed/WI-LLM-0055.md` — Capture full entity lists and diff them across benchmark candidates
- `proposed/WI-LLM-0056.md` — Tranche 1: expand the benchmark harness to cross-provider coverage (Anthropic, OpenAI, Gemini, one open-weight family)
- `proposed/WI-ANNOTATE-0052.md` — Validate sidecar content in lcats promote's release gate
- `proposed/WI-ANNOTATE-0054.md` — Run lcats annotate over a per-genre subset and collect statistics

## Abandoned Items
- `abandoned/WI-META-0006.md` — superseded by native LRH functionality (`lrh meta register`); reversed by WI-META-0023
- `abandoned/WI-ANNOTATE-0053.md` — superseded by `WI-STATS-0049`, which landed the identical `lcats stats` selector fix independently

## Resolved Items
- `resolved/WI-LLM-0051.md` — Investigate Ollama's forced tool_choice reliability; 0/5 baseline success, but a system-prompt reminder retry helps (2/5, 40%) - implemented as an automatic retry in the harness
- `resolved/WI-LLM-0050.md` — Extend the local-model benchmark harness to genre-detection and segmentation stages; genre detection hybrid-viable (2/2), segmentation not (2/2 tool_choice failures)
- `resolved/WI-LLM-0049.md` — Add qwen3:30b-a3b (MoE) candidate to the local-model benchmark harness; hypothesis not supported (both slower and less reliable than qwen3:8b)
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
- `resolved/WI-META-0023.md` — Remove LRH meta-registry duplication from LCATS codebase and docs
- `resolved/WI-EVENT-0028.md` — Investigate need and design for cross-segment causal relation extraction
- `resolved/WI-EVENT-0029.md` — Implement story-level cross-segment relation pass for Event-Role-World extractor
- `resolved/WI-PACKAGING-0031.md` — Bring lcats/pyproject.toml metadata up to PEP 621/639 and CI-parity
- `resolved/WI-PACKAGING-0032.md` — Move lcats package from lcats/lcats/ to lcats/src/lcats/ (src-layout)
- `resolved/WI-PACKAGING-0034.md` — Fix and document environment.yml and pre-commit tool-version drift
- `resolved/WI-PACKAGING-0035.md` — Add setuptools-scm dynamic versioning and remove lcats/setup.py
- `resolved/WI-PACKAGING-0036.md` — Replace hardcoded parent-depth path counting with a pyproject.toml anchor
- `resolved/WI-RELEASE-0038.md` — Add lcats.version module, --version CLI flag, and scripts/version release helper
- `resolved/WI-ANNOTATE-0050.md` — Fix max_tokens truncation in assess_story and make_segment_extractor
- `resolved/WI-ANNOTATE-0051.md` — Build lcats annotate command with checkpoint-safe sidecar writes
- `resolved/WI-ASSESS-0031.md` — Extend VALID_GENRES from 4 to 8 target genres
