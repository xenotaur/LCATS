---
id: WI-PROMOTE-0097
title: Add mandatory insert/upsert/replace modes and sidecar-validator registry to lcats promote
type: deliverable
status: resolved
priority: medium
owner: unassigned
contributors: []
assigned_agents: []
related_focus: []
related_roadmap: []
related_workstreams:
  - WS-PROMOTE-MODE-REDESIGN
related_design:
  - project/design/proposals/adopted/lcats-promote-mode-redesign/00_proposal.md
  - lcats/src/lcats/analysis/corpus/promote.py
  - lcats/src/lcats/analysis/corpus/promote_cli.py
  - lcats/src/lcats/analysis/corpus/discovery.py
  - lcats/src/lcats/analysis/corpus/genre_sidecar.py
  - lcats/src/lcats/analysis/linguistics/sidecar.py
depends_on: []
blocked_by: []
blocked: false
blocked_reason: null
resolution: "Implemented and merged in PR #405 (merge commit 9665a2d44544941b476e47015bf7f178a3ed7289). lcats promote now requires an explicit insert/upsert/replace mode - no bare invocation, no silent default. Generalized promote_sidecar_tranche() into promote_sidecar_insert()/promote_sidecar_upsert(), sharing one engine, driven by a manifest-identity envelope ({lcats_id, payload}) so routing works uniformly across all 4 registered sidecar kinds. Added sidecar_validators.py, a shared registry (genre.json, scenes.json, linguistics.json, linguistics.tokens.json) with lazy-imported linguistics validators to avoid pulling in their heavier dependency chain. --allow-unvalidated covers only the no-registered-validator case. replace's own wholesale mechanism is unchanged. Review (Copilot + Codex) found and fixed 7 issues before merge, including 3 P1s: an unsafe --sidecar-filename path-escape/story.json-overwrite risk under --allow-unvalidated, a payload/envelope lcats_id identity-mismatch gap, and a real regression that would have broken WI-GENRE-0077's only existing manifest (resolved via a documented bare-record compatibility path). See project/executions/WI-PROMOTE-0097/ and project/executions/AD_HOC/*WI_PROMOTE_0097* for the full record chain."
expected_actions:
  - edit_file
  - run_tests
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - implement_replace_orphaned_sidecar_guard
  - implement_live_directory_scan_sourcing
  - change_promote_wholesale_replacement_default_behavior
  - extend_validator_interface_to_non_json_kinds
  - allow_unvalidated_bypass_of_a_registered_validators_rejection
acceptance:
  - "lcats promote requires an explicit insert/upsert/replace mode as a mandatory positional subcommand; a bare invocation with no mode (e.g. lcats promote <collection> with no mode named) refuses rather than defaulting to any behavior"
  - "insert mode: per-file, create-only - writes a named sidecar file into an existing story bucket only if it does not already exist there; refuses (does not overwrite) if it does"
  - "upsert mode: per-file, create-or-overwrite - writes a named sidecar file whether or not it already exists, never touches or deletes any other file in the destination bucket or collection, whole-file overwrite only (no in-sidecar content merge)"
  - "replace mode: today's existing wholesale rmtree+copytree mechanism (promote_collections/_copy_collection), unchanged, reachable only via the explicit replace mode name - no scope change to its own behavior in this item"
  - "A new, shared sidecar-validator registry module exists in analysis/corpus/, mapping registered sidecar filenames to validator callables, registering all 4 currently-produced sidecar kinds (genre.json, scenes.json, linguistics.json, linguistics.tokens.json); promote.py's insert/upsert payload-validation dispatch imports only this registry, never genre_sidecar.py or linguistics/sidecar.py directly. replace mode's own pre-existing validation logic -- both its legacy-flat-genre.json shape-detection/overwrite-guard (structurally unroutable through the registry) and its validation of current-format sidecars (technically routable, but out of scope by design -- replace never uses the registry, per this module's own docstring) -- predates this work item and is explicitly out of scope; see WI-PROMOTE-0102 (amended per WI-PROMOTE-0102's investigation, not part of this WI's original resolution)"
  - "insert and upsert both refuse by default when the named --sidecar kind has no registered validator; --allow-unvalidated overrides this specific case (no registered validator) only - it does not bypass a registered validator's own rejection of malformed content, which insert/upsert always refuse unconditionally, with no override available in this item (resolves the adopted proposal's own Open Question on this point)"
  - "insert/upsert manifest entries are self-identifying independent of their payload's own internal shape: each manifest line supplies a destination lcats_id in an envelope alongside the sidecar payload, rather than promote_sidecar_tranche()'s current behavior of reading lcats_id off the payload itself - this is required because scenes.json payloads (annotate.py's _annotate_scenes() output: segments/segment_count/model/input_tokens/output_tokens) carry no story-identity field at all, unlike genre-sidecar-v1 payloads - a manifest line with no envelope wrapper is still accepted as a bare legacy record when it carries its own non-empty top-level lcats_id (compatibility path, review finding PR #405), but an identity-bearing payload's own lcats_id must agree with the routing lcats_id or the write is rejected"
  - "--sidecar flag is shared identically by insert and upsert, selecting which registered kind an invocation targets; a value with no extension assumes .json before the registry lookup, a value with an extension is matched exactly with no inference; the registry refuses to register two kinds sharing a basename under different extensions"
  - "lcats/docs/reference/corpus-promotion.md, lcats/docs/reference/cli-commands.md, and lcats/docs/reference/prepare-corpora-release.md are updated to reflect the new mandatory-mode command syntax, replacing every documented bare/flag-based invocation"
  - "scripts/test passes with no new failures"
  - "lrh validate reports 0 errors"
required_evidence:
  - test_output
  - lrh_validate
  - manual_review
artifacts_expected:
  - lcats/src/lcats/analysis/corpus/promote.py
  - lcats/src/lcats/analysis/corpus/promote_cli.py
  - lcats/src/lcats/cli.py
  - lcats/tests/analysis_tests/promote_test.py
  - lcats/docs/reference/corpus-promotion.md
  - lcats/docs/reference/cli-commands.md
  - lcats/docs/reference/prepare-corpora-release.md
---

# Work Item: WI-PROMOTE-0097

## Summary

Remove `lcats promote`'s silently-destructive default by requiring an
explicit `insert`/`upsert`/`replace` mode on every invocation, and build
a shared sidecar-validator registry so every promoted sidecar kind is
schema-checked by default across both additive modes. This is Stage 1 of
`WS-PROMOTE-MODE-REDESIGN`'s implementation plan
(`PROP-LCATS-PROMOTE-MODE-REDESIGN`, Decisions 1, 2, 4, 5, and 7).

## Problem / Context

`lcats promote`'s bare invocation currently performs a wholesale
`rmtree`+`copytree` of an entire collection from `data/` to `corpora/`
with no confirmation and no way to opt out
(`lcats/src/lcats/analysis/corpus/promote.py:295-299`). A separate,
additive tranche-promotion path exists (`--tranche-manifest`), but the
wholesale path's own default was never hardened — a gap a live Copilot
review finding on PR #362 (`WI-GENRE-0077`) surfaced directly: sidecars
promoted via the tranche path can be silently destroyed by a later,
unrelated wholesale promote. `PROP-LCATS-PROMOTE-MODE-REDESIGN` (adopted)
designs the full fix; this item implements its first, foundational
stage — the mode split and validator registry that Decision 6's
`replace`-specific guard (Stage 2) and Decision 8's live-directory-scan
sourcing (Stage 3) both depend on.

### Duplication search
- In-repo: No existing implementation of the mode split or registry.
  `WI-GENRE-0075` (resolved) built the tranche-promotion mechanism this
  item generalizes into `insert`/`upsert`.
- Sibling repos: None identified.
- External libraries: None — project-specific corpus-management tooling.
- Recommendation: Proceed.

### Demand search
- Work items: No other open work item requests this.
- Proposals: `PROP-LCATS-PROMOTE-MODE-REDESIGN` (adopted) is the
  governing design this item implements — not a duplicate request.
- Backlog: No matching entry.
- Recommendation: Proceed.

## Scope

- Restructure `lcats promote`'s CLI (`promote_cli.py`) into mandatory
  `insert`/`upsert`/`replace` modes via `argparse`
  `add_subparsers(dest="mode", required=True)`; no default mode.
- Generalize `promote_sidecar_tranche()` into `insert` (create-only) and
  `upsert` (create-or-overwrite) implementations.
- Leave `replace`'s underlying mechanism (`_copy_collection`) unchanged —
  only its reachability changes.
- Build the sidecar-validator registry module (exact filename decided at
  implementation time, e.g. `sidecar_validators.py`), registering all 4
  currently-produced kinds.
- Require a registered validator by default for `insert`/`upsert`, with
  `--allow-unvalidated` as the sole override.
- Add the `--sidecar` flag, shared by `insert`/`upsert`, with the
  extension-inference rule from the proposal's Decision 7.
- Update the three affected docs files to the new command syntax.

## Required Changes

1. **`lcats/src/lcats/analysis/corpus/promote_cli.py`**: restructure
   `build_parser()` to require an explicit mode subcommand (`insert`,
   `upsert`, `replace`), each with its own argument set — `insert`/
   `upsert` take `--sidecar <name>[.ext]` and `--tranche-manifest <path>`,
   plus `--allow-unvalidated`; `replace` keeps today's `collections`/
   `--source`/`--dest`/`--dry-run` arguments unchanged. Update `run()`'s
   dispatch accordingly.
2. **`lcats/src/lcats/analysis/corpus/promote.py`**: add
   `promote_sidecar_insert()`/`promote_sidecar_upsert()` (or a single
   function parameterized by an insert/upsert distinction — implementer's
   choice, justified against the existing `promote_sidecar_tranche()`
   shape), each validating via the new registry (Required Change 3)
   before writing, generalizing `discovery.GENRE_SIDECAR_FILENAME` to
   whichever filename `--sidecar` resolves to instead of the current
   hardcoded genre-only destination. **Manifest envelope (review finding,
   PR #401):** `promote_sidecar_tranche()` today derives its destination
   `lcats_id` by reading it off the manifest record's own top-level
   `lcats_id` field — that only works because `genre-sidecar-v1` payloads
   happen to carry their own identity. `scenes.json` payloads
   (`annotate.py`'s `_annotate_scenes()` output — `segments`/
   `segment_count`/`model`/`input_tokens`/`output_tokens`) carry no
   story-identity field at all, so this item's manifest format must
   change to an envelope shape: each manifest line is `{"lcats_id":
   "<destination story id>", "payload": {<sidecar content, validated by
   the registry and written as-is>}}`. Destination routing reads
   `lcats_id` from the envelope only, never from the payload's own
   (possibly absent) fields — this keeps routing payload-shape-agnostic
   for all 4 registered kinds without needing live-directory-scan
   sourcing (explicitly out of scope, see Non-Goals). Existing genre-
   sidecar-v1 manifests (e.g. `WI-GENRE-0004`'s
   `validation_results.jsonl`, already consumed by `WI-GENRE-0077`) will
   need to move to this envelope shape too, or a compatibility path
   must be documented — flag this to reviewers if the migration cost
   turns out non-trivial. `promote_collections()`/`_copy_collection()`
   are unchanged in this item.
3. **New registry module** in `analysis/corpus/`: a `dict[str,
   Callable[[Any], ValidationResult]]` (or equivalent), registering
   `genre.json` → `genre_sidecar.validate_sidecar`, `linguistics.json`/
   `linguistics.tokens.json` → `linguistics.sidecar.validate_sidecar`/
   `validate_token_detail`, and `scenes.json` → an adapter wrapping
   `promote.py`'s existing `_SIDECAR_REQUIRED_KEYS`-based shape check
   (per `PROP-LCATS-PROMOTE-MODE-REDESIGN` Decision 5's own note that
   this needs no new validator written from scratch). Reject
   registrations with a shared basename across different extensions
   (guards the `--sidecar` bare-name shortcut).
4. **`lcats/tests/analysis_tests/promote_test.py`**: add tests covering
   the mode-required refusal, `insert`'s create-only refusal-on-conflict,
   `upsert`'s create-or-overwrite behavior (reusing/adapting existing
   tranche-mode test coverage), the registry's validator dispatch for
   all 4 kinds, `--allow-unvalidated`'s override behavior, the
   `--sidecar` bare-name/extension normalization rule and its
   basename-collision guard, and confirmation `replace`'s own existing
   test coverage is unaffected.
5. **`lcats/docs/reference/corpus-promotion.md`**, **`lcats/docs/
   reference/cli-commands.md`**, **`lcats/docs/reference/prepare-
   corpora-release.md`**: update every documented invocation to the new
   mandatory-mode syntax.

## Non-Goals

- Does not implement `replace`'s orphaned-sidecar guard or
  `--allow-orphaned-sidecar-deletion` (`PROP-LCATS-PROMOTE-MODE-REDESIGN`
  Decision 6) — that is Stage 2, a separate work item, depending on this
  item's registry.
- Does not implement live-directory-scan sourcing for `insert`/`upsert`
  (Decision 8) — that is Stage 3, a separate work item.
- Does not extend the validator interface to non-JSON sidecar kinds —
  explicitly deferred by the proposal itself.
- Does not change `replace`'s own wholesale copy/replace mechanism.

## Acceptance Criteria

(see frontmatter `acceptance:` above)

## Validation

- `scripts/version tools`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`

## Risk Notes

- The registry's basename-collision guard (Required Change 3) is cheap
  to get right now and expensive to retrofit once real invocations exist
  using the bare-name shortcut — implement it as part of registration,
  not as an afterthought.
- Generalizing `promote_sidecar_tranche()`'s hardcoded
  `discovery.GENRE_SIDECAR_FILENAME` destination to an arbitrary
  `--sidecar`-resolved filename is the one piece of this item most
  likely to have a subtle scoping bug (e.g. accidentally still assuming
  genre-shaped validation somewhere) — the new tests (Required Change 4)
  covering all 4 kinds, not just genre, are load-bearing for catching
  this.
- ~~The manifest envelope format change (Required Change 2, review
  finding PR #401) may require migrating existing genre-sidecar-v1
  manifests ... needs to be designed.~~ — **resolved by this item's own
  implementation** (review finding, PR #405, `chatgpt-codex-connector`,
  P1): a manifest line with no `"payload"` field is accepted when it
  carries its own non-empty top-level `lcats_id` — the whole record is
  then treated as the payload, using that same `lcats_id` for routing.
  Existing genre-sidecar-v1 manifests (`WI-GENRE-0004`'s
  `validation_results.jsonl`, produced by
  `experiments/05_metadata_genre_prefilter/run_prefilter.py`, consumed by
  the still-open PR #362/`WI-GENRE-0077`) need no migration.
- Two further P1 findings on PR #405 (`chatgpt-codex-connector`), both
  fixed: (1) an identity-bearing payload's own `lcats_id` must agree with
  the envelope/routing `lcats_id`, or the write is rejected — otherwise a
  valid payload for one story could be routed into a different story's
  bucket; (2) an unregistered `--sidecar` value used with
  `--allow-unvalidated` must be a single safe path component (no `..`/
  `/`, not `story.json`) before being joined onto the destination bucket
  — otherwise it could escape the bucket or overwrite the canonical
  story file.
- One P2 finding on PR #405 (`copilot-pull-request-reviewer`), fixed: a
  write-path exception (e.g. a payload that fails `json.dumps`, or an
  `OSError` from the atomic write) is now recorded as a per-line
  rejection like any other validation failure, instead of aborting the
  entire manifest run.

## Dependencies / Order

No `depends_on`. This item is Stage 1 of `WS-PROMOTE-MODE-REDESIGN`;
Stage 2 (`replace`'s orphaned-sidecar guard) and Stage 3 (live-directory-
scan sourcing) both depend on this item's registry once minted as their
own work items.

## Related Workstream and Designs

- Workstream: `project/workstreams/active/WS-PROMOTE-MODE-REDESIGN.md`
- Design: `project/design/proposals/adopted/lcats-promote-mode-redesign/00_proposal.md`
