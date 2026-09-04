# promote.py's direct genre_sidecar imports: assessment and recommendation

Date: 2026-09-04
Work item: WI-PROMOTE-0102
Scope: recommendation only — this document proposes replacement wording
for two existing criterion texts, but does not edit them; no behavior
change is applied in this WI's own PR.

## Purpose

`WS-PROMOTE-MODE-REDESIGN`'s exit criterion 3 reads: *"a shared
sidecar-validator registry exists, registering every currently-produced
sidecar kind (genre.json, scenes.json, linguistics.json,
linguistics.tokens.json), with no direct promote.py import of any
producer subpackage."* `WI-PROMOTE-0097`'s own acceptance criteria state
it more strongly: *"promote.py imports only this registry, never
genre_sidecar.py or linguistics/sidecar.py directly."*

`promote.py` on `main` still does `from lcats.analysis.corpus import
genre_sidecar` directly, used at two call sites:

1. `_validate_sidecars()` (`promote.py:142`) — `replace`'s own
   pre-existing structural JSON-shape check, called from
   `survey_collection()` for every source story bucket.
2. `_promote_sidecar_records()` (`promote.py:722`) — the shared
   `insert`/`upsert` engine's guard refusing to overwrite an existing
   legacy-flat `genre.json` at the destination.

This document assesses, for each usage independently, whether it can be
routed through `sidecar_validators` without changing its behavior, and
recommends replacement wording for the two criterion texts above.

## What was verified

### Origin and PR #405 impact, per usage

Both usages predate `WI-PROMOTE-0097` entirely. `_validate_sidecars`'s
genre.json handling was introduced by `WI-GENRE-0076` (PR #357); the
`is_legacy_flat_sidecar()` shape-detection function it calls, and the
overwrite guard in what is now `_promote_sidecar_records`, trace to
`WI-GENRE-0075` (PR #350) — confirmed via `git log -S
is_legacy_flat_sidecar` against `origin/main`, well before the registry
existed.

Diffing `WI-PROMOTE-0097`'s merge commit (`9665a2d4`, PR #405) against
its actual mainline parent (not the merge commit's own combined diff,
which hides this) shows an accurate, per-usage account:

- **`_validate_sidecars`** (usage 1, `replace`'s structural check): the
  diff contains zero changes to this function. Genuinely untouched.
- **`_promote_sidecar_records`**'s overwrite guard (usage 2): PR #405
  *did* touch this code — it nested the existing
  `genre_sidecar.is_legacy_flat_sidecar(existing)` call under a new `if
  sidecar_filename == discovery.GENRE_SIDECAR_FILENAME:` conditional
  while generalizing the old genre-only `promote_sidecar_tranche()`
  into the shared, multi-sidecar-kind `_promote_sidecar_records()`
  engine. The guard's own check logic and the
  `is_legacy_flat_sidecar()` call itself were preserved unchanged —
  only their structural nesting moved to accommodate the new
  per-sidecar-kind dispatch. Elsewhere in that same diff, PR #405 did
  remove a *different* direct `genre_sidecar.validate_sidecar(record)`
  call from the old tranche-validation path, replacing it with
  registry-driven dispatch — consistent with the registry's actual
  purpose, just not a full removal of every `genre_sidecar` reference.

Neither Copilot nor Codex flagged either usage site on PR #405's own
review (confirmed by reading `gh pr view 405`'s review/comment history
directly) — the split between these two usages and the registry was a
design choice at `WI-PROMOTE-0097` time, not a defect later caught by
review.

### `_validate_sidecars` is exclusively `replace`'s engine

`_validate_sidecars()` is called only from `survey_collection()`
(`promote.py:278`), which is called only from `promote_collections()`
(`promote.py:516`), which is called only by `promote_cli.py`'s
`_run_replace_mode()` (`promote_cli.py:189`). `insert`/`upsert` use an
entirely separate code path — `promote_sidecar_insert`/
`promote_sidecar_upsert`, both thin wrappers around
`_promote_sidecar_records()` (`promote_cli.py:169`). Neither
`_validate_sidecars` nor anything it calls is reachable from
`insert`/`upsert`.

### `sidecar_validators.py`'s own docstring already documents this split as intentional

The module's docstring states: *"`promote.py` imports only this module
for validation, never `genre_sidecar.py` or
`analysis/linguistics/sidecar.py` directly, so a promotion of an
unrelated sidecar kind (or a `replace`-mode invocation, **which never
validates at all**) never pays the cost of importing
`linguistics/sidecar.py`'s heavier dependency chain."* (emphasis added).
This is written by whoever built the registry (`WI-PROMOTE-0097`) as an
explanation of the registry's own scope — it explicitly carves out
`replace` mode as never going through the registry, confirming the split
between `_validate_sidecars` and the registry was a design choice at
`WI-PROMOTE-0097` time, not an oversight later flagged by review (see
"Origin and PR #405 impact, per usage" above).

### `_promote_sidecar_records`'s guard checks the *destination*, not the incoming payload

The registry's `ValidatorFn` contract (`sidecar_validators.py:52`) is
`Callable[[Any], _ValidationResultLike]` — it validates one incoming
payload and returns whether *that payload* is well-formed. The
`is_legacy_flat_sidecar()` call in `_promote_sidecar_records`
(`promote.py:916`) does something categorically different: it reads the
file **already present at the destination** and decides whether it is
safe to overwrite. There is no registry concept for "check the existing
destination file before writing" — the registry only ever sees the
payload being promoted. Routing this through the registry as it exists
today is not possible without adding a new kind of hook to its
interface (an "overwrite guard," separate from validation) — real
interface work, not a small mechanical swap, and out of this
investigation's scope per its own Non-Goals.

### `_validate_sidecars` contains a mix of registry-routable and non-routable logic

Reading `_validate_sidecars` line by line against `_SIDECAR_REQUIRED_KEYS`
(`promote.py:53`) and the registry's `_validate_genre`/`_validate_scenes`
(`sidecar_validators.py:55`, `:71`):

- **The v1-shaped `genre.json` branch** (`promote.py:186-189`, entered
  when `is_legacy_flat_sidecar(data)` is `False`) calls
  `genre_sidecar.validate_sidecar(data)` directly. The registry's own
  `_validate_genre` (`sidecar_validators.py:55`) is a pure delegation to
  that exact same function — `sidecar_validators.get_validator(
  discovery.GENRE_SIDECAR_FILENAME)(data)` would return an identical
  result. This one call site *could* be swapped for a registry lookup
  with zero behavior change.
- **The `scenes.json` branch** (reached via the generic
  `required_key`/`expected_type` check at `promote.py:202-220`, since
  `SCENES_SIDECAR_FILENAME` is the second `_SIDECAR_REQUIRED_KEYS`
  entry) checks: is `data` a dict, does it have a `"segments"` key, is
  that value a list. `sidecar_validators._validate_scenes`
  (`sidecar_validators.py:71`) — whose own docstring says it is
  *"reimplemented here rather than imported from promote.py, since
  promote.py imports this module and importing back would be
  circular"* — checks the identical three conditions. This is
  genuine, acknowledged duplication between the two files, though the
  two implementations produce differently-worded finding messages (one
  emits a flat string via `MalformedSidecarFinding.error`, the other a
  structured `ValidationFinding` sequence) — a swap here is a real
  refactor of `_validate_sidecars`'s control flow (special-casing
  `scenes.json` similarly to how `genre.json` is already special-cased),
  not a one-line substitution, and would change the exact wording of any
  currently-emitted error string.
- **The legacy-flat `genre.json` branch** (reached when
  `is_legacy_flat_sidecar(data)` is `True`, falling through to the same
  generic branch, checking for a top-level `detected_genre` string) has
  **no registry equivalent at all**. The registry's `_validate_genre` is
  scoped to v1-shaped content only (`genre_sidecar.validate_sidecar`
  would reject a legacy-flat document, since it lacks the v1
  `assessments[]` structure) — registering a validator for a deprecated,
  no-longer-produced shape doesn't fit the registry's own stated scope
  (*"registering every currently-produced sidecar kind"*).
- **The `is_legacy_flat_sidecar()` shape-detection call itself**
  (`promote.py:187`, and again in usage 2 at `promote.py:916`) has no
  registry equivalent under any branch — it decides *which* validation
  path applies (or whether the file is even eligible for
  registry-style validation), not whether a payload is valid. This call
  is structurally irreducible without inventing new registry surface,
  and it is the one `genre_sidecar` reference common to *both* usage
  sites.

## Recommendation

**Do not apply a code change in this WI's own PR.** Two of the four call
sites above (the v1-`genre.json` validation swap, and — with more
restructuring — the `scenes.json` swap) are technically routable through
the registry, but neither achieves full compliance with the exit
criterion's literal wording on its own: `is_legacy_flat_sidecar()` and
the legacy-flat-`genre.json` key check remain irreducible in both usages
regardless. Applying only the two routable swaps would still leave
`promote.py` importing `genre_sidecar` directly, so the actual gap the
exit criterion cares about (a direct import existing at all) would not
close — it would just narrow which lines cause it. Per this WI's own
Scope (*"use judgment and favor deferring when in doubt"*), the value of
a partial, not-fully-compliant swap does not clearly outweigh the review
and behavior-verification cost (the `scenes.json` swap in particular
changes emitted error-message wording), so this is left for a future WI
to pick up only if the low-value cleanup is independently wanted — not
required to resolve this investigation's actual question.

**Recommend narrowing the criterion wording — but on two distinct
grounds, not one, per review feedback (Codex, PR #427).** An earlier
draft of this section characterized *all* of `replace`'s pre-flight
logic as "recognizing an already-obsolete file shape" — that is wrong
for two of the four call sites and contradicts "What was verified"
above. The two grounds are:

1. **`is_legacy_flat_sidecar()`'s shape-detection call is genuinely
   irreducible.** It decides *which* code path applies (or whether a
   file is even eligible for registry-style validation) — not whether a
   payload is valid — and the registry has no hook for this kind of
   check under any branch. This is a real structural mismatch, not a
   judgment call: the exemption for this specific call, in both usages,
   holds regardless of anything else in this section.
2. **`replace`'s validation of genuinely current-format content (the
   v1-`genre.json` `validate_sidecar()` call, and the `scenes.json`
   required-key check) is real content validation, not shape
   detection** — and, as shown above, is technically routable through
   the registry. It is exempted here not because it's somehow not
   "real" validation, but because `sidecar_validators.py`'s own
   docstring documents `replace` mode as never going through the
   registry *at all*, as a deliberate `WI-PROMOTE-0097`-time design
   choice (avoiding `linguistics/sidecar.py`'s heavier dependency chain
   for a mode that, by that same docstring's own words, "never
   validates at all" through the registry) — and because, per the
   Recommendation above, migrating only these two call sites would not
   achieve full compliance anyway, since ground 1's irreducible call
   remains either way.

The exit criterion as originally written conflates these two grounds
into one blanket "no direct import" requirement; the replacement wording
below keeps the same overall scope (both usages remain exempt from
registry routing) but states the two grounds separately, so a future
reader doesn't mistake "exempt" for "not real validation."

### Proposed replacement wording

**`WS-PROMOTE-MODE-REDESIGN`'s exit criterion 3**, currently:

> a shared sidecar-validator registry exists, registering every
> currently-produced sidecar kind (genre.json, scenes.json,
> linguistics.json, linguistics.tokens.json), with no direct promote.py
> import of any producer subpackage

Proposed:

> a shared sidecar-validator registry exists, registering every
> currently-produced sidecar kind (genre.json, scenes.json,
> linguistics.json, linguistics.tokens.json), and is the sole validation
> path for insert/upsert's payload dispatch. replace mode is out of
> scope for registry routing entirely — both its legacy-flat-genre.json
> shape-detection/overwrite-guard logic (used by both replace and the
> insert/upsert engine, structurally unroutable) and its validation of
> current-format sidecars (technically routable, but exempted by
> WI-PROMOTE-0097's own documented design choice that replace never
> validates through the registry) — per WI-PROMOTE-0102

**`WI-PROMOTE-0097`'s acceptance criterion**, currently:

> A new, shared sidecar-validator registry module exists in
> analysis/corpus/, mapping registered sidecar filenames to validator
> callables, registering all 4 currently-produced sidecar kinds
> (genre.json, scenes.json, linguistics.json, linguistics.tokens.json);
> promote.py imports only this registry, never genre_sidecar.py or
> linguistics/sidecar.py directly

Proposed:

> A new, shared sidecar-validator registry module exists in
> analysis/corpus/, mapping registered sidecar filenames to validator
> callables, registering all 4 currently-produced sidecar kinds
> (genre.json, scenes.json, linguistics.json, linguistics.tokens.json);
> promote.py's insert/upsert payload-validation dispatch imports only
> this registry, never genre_sidecar.py or linguistics/sidecar.py
> directly. replace mode's own pre-existing validation logic — both its
> legacy-flat-genre.json shape-detection/overwrite-guard (structurally
> unroutable through the registry) and its validation of current-format
> sidecars (technically routable, but out of scope by design — replace
> never uses the registry, per this module's own docstring) — predates
> this work item and is explicitly out of scope; see WI-PROMOTE-0102.

These are proposed text only; per this investigation's Non-Goals, neither
file is edited here. Applying this wording change is a small, mechanical
edit that whoever closes this WI (or a human reviewing this note) can
make directly.

## Follow-up (optional, not required)

If a future contributor wants to reduce `promote.py`'s direct
`genre_sidecar` surface area for its own sake (not to satisfy the exit
criterion, which the wording change above already resolves):

- The v1-`genre.json` branch in `_validate_sidecars` can be swapped for
  `sidecar_validators.get_validator(discovery.GENRE_SIDECAR_FILENAME)`
  with zero behavior change (confirmed: `_validate_genre` is a pure
  delegation to `genre_sidecar.validate_sidecar`).
- The `scenes.json` branch can be swapped similarly, but changes the
  exact wording of emitted `MalformedSidecarFinding.error` strings (no
  test currently pins these strings, so this is a real but low-risk
  behavior change, not a pure no-op).
- `is_legacy_flat_sidecar()` cannot be routed through the registry
  without adding new registry surface (a shape-detection or
  overwrite-guard hook) — not recommended; the concern is
  `genre.json`-specific and won't recur for any other sidecar kind.
