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
- `proposed/WI-ASSESS-0051.md` — Genre-census sample and cost-estimate tooling (Gap 2) - full-corpus run retired, see WI-GENRE-0004
- `proposed/WI-EVENT-0033.md` — Add schema-hardened structured output to scene/story analysis extractors
- `proposed/WI-RELEASE-0037.md` — Resolve gutenbergpy VCS-pin PyPI-publish blocker
- `proposed/WI-RELEASE-0039.md` — Pre-launch verification of the gutenbergpy dependency resolution before real PyPI publish
- `proposed/WI-LLM-0055.md` — Capture full entity lists and diff them across benchmark candidates
- `proposed/WI-LLM-0066.md` — Wire run_census.py to a local OpenAI-compatible backend and evaluate gpt-oss:20b at genre-census scale
- `proposed/WI-GENRE-0001.md` — Create metadata genre prefilter scaffold
- `proposed/WI-GENRE-0004.md` — Full-corpus metadata scan, genre-balanced 100-200 story selection, and bounded Opus validation
- `proposed/WI-VISUALIZE-0073.md` — Reusable lcats visualize CLI substrate and genres command

## Abandoned Items
- `abandoned/WI-META-0006.md` — superseded by native LRH functionality (`lrh meta register`); reversed by WI-META-0023
- `abandoned/WI-ANNOTATE-0053.md` — superseded by `WI-STATS-0049`, which landed the identical `lcats stats` selector fix independently

## Resolved Items
- `resolved/WI-LLM-0065.md` — Make gpt-oss:20b entity extraction production-grounded behind a candidate-scoped adapter; consider-only pending precision/recall evaluation, with no default routing change
- `resolved/WI-LLM-0064.md` — Establish a best-of-breed config for ollama_gpt_oss_20b and fix harness diagnostic gaps
- `resolved/WI-LLM-0063.md` — Thoroughly vet ollama_gpt_oss_20b across all 3 pipeline stages; genre detection 3/3, entity extraction 3/3 (real output-count variance found), segmentation 0/3 (new alignment-rejection failure mode distinct from silent-ignore)
- `resolved/WI-LLM-0062.md` — Investigate WI-LLM-0056's two distinct tool_choice failure mechanisms; silent-ignore mitigation partially recovers gemma4:12b (1/2) but not deepseek-r1:14b (0/3); gemini_flash's filter rejection was a token-budget confound, not schema complexity (3/3 success at max_tokens=32000)
- `resolved/WI-LLM-0056.md` — Tranche 1: expand the benchmark harness to cross-provider coverage; all 6 cells landed with real evidence (3 succeeded, 3 documented failures revealing two distinct tool_choice failure mechanisms)
- `resolved/WI-LLM-0058.md` — Fix ASSESSMENT_TOOL secondary_genre schema-adjacent field corruption (39% combined rate across two real runs); sanitized via a new non-fatal AssessmentResult.secondary_genre_sanitized flag, checkpoint-version bumps across all 3 assess_story() callers, GO recommendation for WI-ASSESS-0051's --full run
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
- `resolved/WI-EVENT-0032.md` — Harden Event-Role-World tool-schema reliability and processor error/model handling
- `resolved/WI-EVENT-0028.md` — Investigate need and design for cross-segment causal relation extraction
- `resolved/WI-EVENT-0029.md` — Implement story-level cross-segment relation pass for Event-Role-World extractor
- `resolved/WI-STORY-0042.md` — Make LCATS story discovery and identity dual-layout-compatible
- `resolved/WI-ANNOTATE-0052.md` — Validate sidecar content in lcats promote's release gate
- `resolved/WI-ANNOTATE-0054.md` — Run lcats annotate over a per-genre subset and collect statistics
- `resolved/WI-PACKAGING-0031.md` — Bring lcats/pyproject.toml metadata up to PEP 621/639 and CI-parity
- `resolved/WI-PACKAGING-0032.md` — Move lcats package from lcats/lcats/ to lcats/src/lcats/ (src-layout)
- `resolved/WI-PACKAGING-0034.md` — Fix and document environment.yml and pre-commit tool-version drift
- `resolved/WI-PACKAGING-0035.md` — Add setuptools-scm dynamic versioning and remove lcats/setup.py
- `resolved/WI-PACKAGING-0036.md` — Replace hardcoded parent-depth path counting with a pyproject.toml anchor
- `resolved/WI-RELEASE-0038.md` — Add lcats.version module, --version CLI flag, and scripts/version release helper
- `resolved/WI-ANNOTATE-0050.md` — Fix max_tokens truncation in assess_story and make_segment_extractor
- `resolved/WI-ANNOTATE-0051.md` — Build lcats annotate command with checkpoint-safe sidecar writes
- `resolved/WI-ASSESS-0031.md` — Extend VALID_GENRES from 4 to 8 target genres
