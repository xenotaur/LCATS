---
id: PROP-LCATS-PROMOTE-MODE-REDESIGN
type: design_proposal
title: lcats promote Mode Redesign — Mandatory Modes and Sidecar-Kind Safety Guards
status: proposed
created_on: 2026-08-23
updated_on: 2026-08-23
implementation_status: not_started
implemented_by: []
supersedes: []
superseded_by: null
related_design:
  - project/design/proposals/proposed/genre-evidence-sidecars/00_proposal.md
  - lcats/src/lcats/analysis/corpus/promote.py
  - lcats/src/lcats/analysis/corpus/promote_cli.py
  - lcats/src/lcats/analysis/corpus/discovery.py
  - lcats/src/lcats/analysis/corpus/genre_sidecar.py
  - lcats/src/lcats/analysis/linguistics/sidecar.py
---

# Proposal: lcats promote Mode Redesign

## Summary

This proposal removes `lcats promote`'s silently-destructive default,
replaces it with three mandatory, explicitly-named modes (`insert`,
`upsert`, `replace`), and introduces a shared sidecar-validator registry
so every promoted sidecar kind is schema-checked by default across all
modes.

## Background / Motivation

`lcats promote`'s bare invocation (no mode, no flag) performs a wholesale
`rmtree`+`copytree` of an entire collection from `data/` to `corpora/`
(`promote.py:295-299`). `WI-GENRE-0075` added an additive, non-destructive
tranche-promotion path (`--tranche-manifest`) alongside it, but left the
wholesale path's own default unchanged. A live Copilot review finding on
PR #362 (`WI-GENRE-0077`) surfaced the resulting hazard directly: sidecars
promoted via the tranche path can be silently destroyed by a later,
unrelated wholesale `lcats promote <collection>` run, since the wholesale
path resyncs from `data/`, which never received those sidecars.

`PROP-GENRE-EVIDENCE-SIDECARS` Decision 7 already identified that
"current promotion wholesale-replaces destination collections, which is
too blunt," and chose to *add* tranche promotion alongside wholesale —
but never asked to harden wholesale's own default. This proposal closes
that gap and generalizes the tranche mechanism to serve more than one
sidecar-producing subsystem: `genre_sidecar.py` (in `analysis/corpus/`)
and `linguistics/sidecar.py` (in `analysis/linguistics/`, a separate
subpackage) already independently converged on the same validator
interface shape, and an imminent whole-corpus `linguistics.json` rollout
makes the wholesale-vs-tranche collision concrete and near-term, not
speculative.

## Prior Art Check

### Duplication search
- In-repo: No existing implementation of a mode-split/registry/guard
  redesign found. `WI-GENRE-0075` (resolved) built the tranche mechanism
  this proposal generalizes; `WI-GENRE-0077` is the PR whose review
  surfaced the need. Neither duplicates this proposal.
- Sibling repos: None identified.
- External libraries: None — project-specific corpus-management tooling.
  Naming/behavior precedent surveyed below, not adopted as a dependency.
- Recommendation: Proceed.

### Demand search
- Work items: No open work item requests this redesign.
- Proposals: `PROP-GENRE-EVIDENCE-SIDECARS` Decision 7 is the governing
  design this proposal extends/completes, not a duplicate request.
- Backlog: No matching entry. One adjacent, unrelated entry exists
  (`backlog.md:651`, mojibake-flagging disagreement between `lcats
  survey`/`lcats promote`) — a separate, already-decided-not-to-fix
  issue.
- Recommendation: No closeout action. Reference `PROP-GENRE-EVIDENCE-
  SIDECARS` Decision 7 as originating context.

## Design Decisions

### Decision 1: Mode selection is mandatory, not a silent default

Options considered: leave the wholesale default in place with a runbook
warning; make wholesale's replacement additive/merge-by-default; require
explicit `--force` to reach wholesale; require an explicit, named mode
for every invocation.

**Chosen: require an explicit, named mode for every invocation** — no
default exists. A runbook-only warning was rejected (buried in a
potentially large diff, easy to miss); an implicitly-additive default was
rejected (surprising to anyone who doesn't know it changed). Matches
fail-safe-defaults design (Saltzer & Schroeder, 1975) and clig.dev's
guidance that destructive operations require explicit opt-in.

### Decision 2: Three modes — `insert`, `upsert`, `replace`

Options considered for the per-file additive modes: a single `merge` mode
covering both create and overwrite; separate create-only and
overwrite-allowed modes. Options considered for naming: `mirror`, `sync`,
`wholesale`, `clobber`, `whomp`, `add`, `stage`, `merge`, `put`, `create`.

**Chosen:**
- `insert` — per-file, create-only; refuses if the target already
  exists. Named for SQL's bare-`INSERT`-fails-on-conflict precedent
  (reinforced by POSIX `open(O_CREAT|O_EXCL)`), deliberately paired with
  `upsert`.
- `upsert` — per-file, create-or-overwrite, never deletes anything else,
  whole-file overwrite only (no in-sidecar content merge — see Decision
  3). Named for the vector-DB/AI-community convention (Pinecone,
  Weaviate, Qdrant, Chroma, Milvus all use this term for the identical
  semantic), matching this project's own audience.
- `replace` — today's existing wholesale mechanism, unchanged, just no
  longer reachable implicitly. Chosen over `mirror`/`sync` because both
  split ambiguously between a one-way-destructive sysadmin reading
  (`rsync --delete`, `wget --mirror`) and a bidirectional consumer-cloud
  reading (Google Drive's "Mirror files" mode is two-way); over
  `wholesale` because it doesn't verb naturally as an imperative CLI
  command; over `clobber`/`whomp` for register/precedent reasons noted in
  Open Questions.

CLI shape: `lcats promote <insert|upsert|replace> [collection] [options]`,
mode as a mandatory positional subcommand (`argparse`
`add_subparsers(dest="mode", required=True)`), not a required flag.
Verified empirically that this composes with zero changes to the
top-level `lcats/src/lcats/cli.py`'s existing `parents=[...]` wiring
pattern (distinct from `analysis/corpus/cli.py`, a same-named but
different file cited elsewhere in this document — correction, review
finding PR #369). That pattern is used identically for 9 subcommands
total, 8 besides `promote` itself (`survey`, `assess`, `stats`,
`repair-specials`, `annotate`, `clean`, `linguistics`, `visualize`), not
six as an earlier draft stated — the entire cost of this redesign is
contained to `promote_cli.py`'s own internal structure.

### Decision 3: No in-sidecar content merge in `promote.py`

Options considered: build schema-aware merge logic into `upsert` (e.g.
appending to an existing sidecar's `assessments[]`); keep `upsert`
strictly whole-file, delegate content-level combination to the producing
tool.

**Chosen: keep `upsert` whole-file only.** Matches `promote.py`'s
existing, deliberate ignorance of sidecar internals (`_validate_sidecars`
already does shape-only checks, not semantic ones — see
`_SIDECAR_REQUIRED_KEYS`, `promote.py:44-46`). Avoids `promote.py` needing
N different merge strategies for N sidecar kinds as more are added.
Content-level combination (e.g. `annotate.py`'s existing
`merge_genre_sidecar()`) stays the producing tool's responsibility,
documented for researchers via a tutorial/runbook/sample code rather than
built into the promotion gate.

### Decision 4: Validator required by default, uniformly across `insert` and `upsert`

Options considered: require validation for `upsert` only (since it can
overwrite existing data) and not `insert` (since it only creates new
files); require validation uniformly for both.

**Chosen: uniform requirement, no exception.** `insert`'s no-overwrite
guarantee protects against destroying existing data; it does nothing to
protect against creating new, unreviewable content in a previously-empty
location. The harm the validator guards against — an unvalidated blob
entering the tracked, team-reviewed corpus — is identical regardless of
whether the write overwrites or creates. An asymmetric rule would also
reintroduce a version of the silent-default surprise Decision 1 exists to
eliminate.

Escape hatch: `--allow-unvalidated`, chosen over generic `--force`/
`--unsafe`/`--noschema` to match the existing `--allow-smart` house
convention (flag defined at `cli.py:169-171`, with a second copy at
`specials_cli.py:60`; consumed by `specials.py`'s `is_allowed()`) for
"loosen an otherwise-strict check," and to name the specific thing being
bypassed rather than acting as a catch-all a future, independent safety
check might also reach for.

### Decision 5: Sidecar-validator registry as a new, dedicated module

Options considered: extend `discovery.py` (the existing shared home for
filename constants); hardcode per-kind validator imports directly in
`promote.py`; a new, dedicated sibling module.

**Chosen: a new, dedicated module** in `analysis/corpus/` (exact filename
TBD at implementation time, e.g. `sidecar_validators.py`), mapping
registered sidecar filenames to validator callables
(`Callable[[Any], ValidationResult]`). `discovery.py`'s own imports are
`os, pathlib, sys, typing` only — it does no validation-related importing
today — but it is imported far more widely than a small, contained set:
14+ files across `analysis/corpus/` and beyond depend on it directly,
including `annotate_cli.py`, `assess_cli.py`, `cli.py`, `output.py`,
`processing.py`, `promote.py`, `corpus_survey.py`, `corpus_surveyor.py`,
`linguistics/runner.py`, `science_fiction/preparation.py`,
`datasets/torchdata.py`, `gatherers/downloaders.py`, `stories.py`, and
`visualize/sources.py` (correction, review finding PR #369 — an earlier
draft undercounted this at six). Extending `discovery.py` to import a
producer's own validator (e.g. `linguistics.sidecar`) would give every
one of these importers a new, transitively-inherited dependency, even
though most have nothing to do with sidecar validation — a wider blast
radius than originally stated, reinforcing rather than weakening the
case for a separate module. One nuance worth being explicit about:
`linguistics/runner.py` already imports `discovery.py` today, so
`analysis/corpus/` and `analysis/linguistics/` already have a real,
bidirectional coupling at the subpackage level — `discovery.py` is not
entirely uninvolved with the linguistics subpackage. It remains a leaf
specifically *with respect to sidecar-validation logic*, which is the
property this decision actually depends on; that narrower framing is
what the "leaf module" language above should be read as. Hardcoding
directly in `promote.py` would reintroduce the exact coupling a prior
review finding (PR #248) already fixed once for filename constants.

**Registry scope must cover every currently-produced sidecar kind, not
only the two used as illustrative examples above** (review finding, PR
#369) — `genre.json` and `linguistics.json` are not the only kinds
already in production. `promote.py`'s own `_SIDECAR_REQUIRED_KEYS`
(`promote.py:44-47`) already recognizes a third, `scenes.json`; and
`linguistics/sidecar.py` produces and validates a fourth,
`linguistics.tokens.json` (`TOKEN_DETAIL_FILENAME`,
`linguistics/sidecar.py:22`, validated by its own
`validate_token_detail()`, `linguistics/sidecar.py:236`). Registering
only two of the four would leave `scenes.json` and
`linguistics.tokens.json` unprotected by both Decision 4 (they'd force
`insert`/`upsert` into `--allow-unvalidated`) and Decision 6 (`replace`
could still silently delete a destination-only copy of either) —
directly contradicting this proposal's own all-kinds safety guarantee.
All four registry entries must ship together for Decisions 4 and 6 to
hold as stated; `genre_sidecar.validate_sidecar()` and `linguistics/
sidecar.py`'s `validate_sidecar()`/`validate_token_detail()` already
share compatible interface shapes, so registering all four requires no
interface redesign — `_SIDECAR_REQUIRED_KEYS`'s existing shape-only
check for `scenes.json` can be wrapped as a `Callable[[Any],
ValidationResult]`-shaped adapter rather than needing a new validator
written from scratch.

### Decision 6: `replace` gets a targeted, registry-based orphaned-sidecar guard

Options considered: no additional guard beyond Decision 1's mode
requirement; an interactive confirmation prompt; a generic "any file
present only in destination" diff-and-refuse; a targeted guard scoped to
registered sidecar kinds only.

**Chosen: a targeted guard.** Renaming the mode alone (Decision 1) closes
the *accidental* wholesale invocation, but not the *deliberate* one
against a collection that's since been upserted-into — the actual
scenario PR #362's review finding described, made concrete by an
imminent whole-corpus `linguistics.json` rollout. An interactive prompt
was rejected — this codebase has zero existing interactive confirmations
anywhere (`grep` for `input(`/`are you sure` across
`src/lcats/analysis/corpus/*.py` and the top-level `src/lcats/cli.py`
returns nothing), and one
would break `docs/reference/prepare-corpora-release.md`'s scripted
release process. A generic destination-only-file diff was rejected for
false-positive risk (legitimately corpora-only content unrelated to
sidecar promotion). The targeted guard checks, before `_copy_collection`
runs, whether the destination has any *registered* sidecar kind (via the
Decision 5 registry) for a story where the source lacks it, and refuses
by default if so.

Escape hatch: `--allow-orphaned-sidecar-deletion` — beat `--force`
(reintroduces the exact overload risk Decision 4's `--allow-unvalidated`
was chosen to avoid) and `--acknowledge-data-loss` (unwanted judgmental
tone). Names the precise mechanical situation: a sidecar becomes
"orphaned" once its would-be source in `data/` is gone. Not used by
`insert`/`upsert`, which are structurally incapable of deleting anything
regardless of flags.

### Decision 7: `--sidecar` flag, shared by `insert`/`upsert`

Options considered for the flag name: `--tranche`, `--kind`, `--type`,
`--sidecar-filename`, `--sidecar`.

**Chosen: `--sidecar`**, matching the existing `*_FILENAME` constant
convention already used three times across two subpackages
(`GENRE_SIDECAR_FILENAME`, `SCENES_SIDECAR_FILENAME`,
`SIDECAR_FILENAME`) more directly than `--kind`/`--type`, which would
introduce vocabulary the codebase doesn't currently use for this concept.
`--tranche` was rejected as a name for *this* concept specifically —
"tranche" more naturally names a batch/subset of records, not a category
of file, and reusing it for both meanings reintroduces exactly the kind
of ambiguity this whole proposal is rooting out elsewhere (it remains the
correct name for the mode *family*, e.g. in prose descriptions).

Value normalization: no extension given → assume `.json` (covers every
currently-registered kind); extension given → exact match against the
registry key, no inference (covers a future non-JSON kind precisely). The
registry must refuse to register two kinds sharing a basename across
different extensions, so the bare-name shortcut stays unambiguous by
construction.

### Decision 8: `insert`/`upsert` gain live-directory-scan sourcing, not `replace`

Options considered: add a `--tranche=<kind>` scoping flag to `replace`
itself, limiting its blast radius to one sidecar kind across a whole
collection; extend `insert`/`upsert` to optionally source records by
scanning `data/<collection>/*/<sidecar-filename>` directly, instead of
requiring a pre-built manifest file (`promote_sidecar_tranche()`'s
current sole input mode).

**Chosen: extend `insert`/`upsert`.** A scoping flag on `replace` would
build a second mechanism for the same underlying need ("touch only one
sidecar kind"), reintroducing the "which command do I use" ambiguity this
whole redesign exists to eliminate. The rule stays exceptionless: one
sidecar kind → always `insert`/`upsert`, regardless of whether records
come from a curated manifest or a live directory scan. This closes a real
gap the linguistics-sidecar rollout surfaced directly: bulk-syncing one
kind across an entire collection fits neither `replace` (too broad) nor
today's manifest-only tranche mode (too narrow, requires hand-curating a
manifest first).

## Non-Goals

- Does not change `replace`'s underlying mechanism (`_copy_collection`'s
  `rmtree`+`copytree`) — only when it's reachable and what pre-flight
  guard runs before it.
- Does not build schema-aware content merging into `promote.py` for any
  sidecar kind (Decision 3) — that stays each producing tool's own
  responsibility.
- Does not extend the validator interface to non-JSON sidecar kinds
  (e.g. a hypothetical binary `.png` sidecar) — today's registry entries
  assume already-parsed JSON. Filed as a follow-on decision, not solved
  here.
- Does not implement the `insert`/`upsert` live-directory-scan capability
  in full detail (Decision 8) beyond stating the design direction — exact
  scan/manifest interop is implementation-time detail.
- Does not touch `lcats annotate`'s own sidecar-writing behavior.

## Implementation Plan

Large scope, multi-stage: see the companion workstream
`WS-PROMOTE-MODE-REDESIGN` for staged work-item breakdown. Anticipated
stages, in dependency order:

1. Sidecar-validator registry module (Decision 5) + mandatory mode split
   (Decisions 1-2) + uniform validation requirement (Decision 4) +
   `--sidecar` flag (Decision 7).
2. `replace`'s targeted orphaned-sidecar guard (Decision 6).
3. `insert`/`upsert` live-directory-scan sourcing (Decision 8) —
   prioritized given the imminent linguistics-sidecar rollout this
   directly de-risks.

Individual work items are not minted by this proposal; they follow once
the companion workstream is adopted.

## Open Questions

- Exact module filename and location for the Decision 5 registry within
  `analysis/corpus/` (a specific name was not fixed at design time).
- Whether `--allow-unvalidated` skips validation only when no validator
  is registered for the named kind, or also when a registered validator's
  check would otherwise fail — needs pinning down at implementation time.
- `clobber` and `whomp` were both seriously considered as alternate names
  for `replace` and found non-disqualifying but weaker than `replace`
  (informal register for `clobber`; zero prior technical precedent, both
  a pro and a con, for `whomp`) — recorded here in case the chosen name
  needs revisiting later.

## Cross-References

- Governing prior design: `project/design/proposals/proposed/genre-
  evidence-sidecars/00_proposal.md`, Decision 7
- Triggering finding: PR #362 (`WI-GENRE-0077`), Copilot review comment
- Prior implementation this generalizes: `WI-GENRE-0075` (resolved),
  `promote_sidecar_tranche()`
- Existing house convention followed: `--allow-smart`
  (`lcats/src/lcats/analysis/corpus/cli.py:169-171`, second copy at
  `specials_cli.py:60`)
- Existing coupling-avoidance precedent followed: `discovery.py:12-16`
  (review finding, PR #248)
