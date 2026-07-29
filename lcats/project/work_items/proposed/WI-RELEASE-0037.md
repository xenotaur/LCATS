---
resolution: null
blocked_reason: null
blocked: false
id: WI-RELEASE-0037
title: Resolve gutenbergpy VCS-pin PyPI-publish blocker
type: deliverable
status: proposed
owner: xenotaur
contributors:
  - xenotaur
assigned_agents: []
related_focus: []
related_roadmap: []
related_workstreams: []
related_design: []
depends_on: []
blocked_by: []
expected_actions:
  - edit_file
  - create_file
  - run_tests
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - publish_package
  - modify_ci_pipeline
acceptance:
  - A documented decision (vendor the fix vs. publish/maintain a distinct-named LCATS-controlled PyPI fork vs. wait on upstream) exists with rationale, including why "wait on upstream" is or isn't viable given no ETA
  - lcats/pyproject.toml's gutenbergpy dependency (currently lcats/pyproject.toml:26, a git+https direct reference) no longer contains a git+https or other direct URL reference
  - lcats/environment.yml's matching gutenbergpy pin (currently environment.yml:263, the identical git+https reference) is updated to match whichever replacement was chosen, so the documented conda environment no longer installs the old fork
  - If vendoring - the alias-table/title-index logic from raduangelescu/gutenbergpy PR #26 is present in lcats/src/lcats/gettenberg/ with clear attribution/comment pointing at the upstream PR, accompanied by a new regression test that exercises the real parser/cache-writer path (not the mocked/fake-row paths in cache_test.py and metadata_test.py) and asserts on resulting title associations and alias tables
  - If re-fork-and-publish - a distinct PyPI project name is reserved and, once published via a separate prerequisite work item (this item's own forbidden_actions bars publish_package), lcats/pyproject.toml pins it by version, not URL
  - lcats/src/lcats/gettenberg/ tests, including the new regression test for the vendoring path, pass unchanged in behavior after the change
  - A built wheel's metadata contains no direct URL/VCS reference (verified via twine check and metadata inspection)
  - lrh validate reports 0 errors
required_evidence:
  - manual_review
  - lrh_validate
  - test_output
artifacts_expected:
  - lcats/pyproject.toml
  - lcats/environment.yml
  - lcats/src/lcats/gettenberg/
---

## Summary

Resolve `lcats/pyproject.toml:26`'s `gutenbergpy @ git+https://github.com/xenotaur/gutenbergpy.git@60ca548...`
dependency so LCATS's distributed package metadata contains no direct
URL/VCS reference — a hard PyPI-publish blocker independent of any other
release-readiness work.

## Problem / Context

LCATS depends on two fixes (alias tables, title-index correction) that were
merged upstream into `raduangelescu/gutenbergpy:master` via
[PR #25](https://github.com/raduangelescu/gutenbergpy/pull/25) and
[PR #26](https://github.com/raduangelescu/gutenbergpy/pull/26), both
authored by `xenotaur`. However, the published `gutenbergpy` PyPI package
is still 0.3.5 (released 2023-03-27), predating that merge — there is no
PyPI release containing the needed fixes. As currently pinned, LCATS
cannot be uploaded to PyPI with this dependency: PyPI's upload validation
(`pypi/warehouse`'s `warehouse/forklift/metadata.py`, in
`_validate_metadata`) rejects any `Requires-Dist` entry whose parsed
`Requirement.url` is not `None` — i.e. any direct URL/VCS reference —
with `Can't have direct dependency: <req>`, which is exactly the shape of
`gutenbergpy @ git+https://...`. This blocks any real (non-placeholder)
PyPI release regardless of how the rest of release-readiness work
proceeds.

As of this work item's authoring, LCATS has contacted the upstream
maintainer to ask about their release schedule (the "wait on upstream"
option below) — response pending. One encouraging, but non-committal,
signal: `raduangelescu/gutenbergpy:master`'s own `setup.cfg` already
declares `version = 0.3.6`, one version ahead of what's actually
published on PyPI (0.3.5) — the maintainer has already bumped the
in-repo version, just not cut/published the release.

Two implementation options (vendor, re-fork-and-publish) were assessed in
more depth than originally scoped, and turned out more coupled than
first assumed. `lcats/src/lcats/gettenberg/cache.py:11` imports the
installed `gutenbergpy` package's own `gutenbergcache` module and calls
its `GutenbergCache.create(...)` (`cache.py:128`) and `.get_cache()`
(`cache.py:144`) directly — LCATS never re-implements any RDF-parsing or
cache-writing logic itself. `GutenbergCache.create()` (in gutenbergpy's
own `gutenbergcache.py`) hardcodes `from gutenbergpy.parse.rdfparser
import RdfParser` and `from gutenbergpy.caches.sqlitecache import
SQLiteCache` at module scope and instantiates them directly, with no
constructor parameter or other extension point to substitute a patched
parser or cache-writer. Both PR #25 and PR #26 touch five files entirely
internal to gutenbergpy's own pipeline:
`gutenbergpy/parse/rdfparser.py`, `gutenbergpy/parse/book.py`,
`gutenbergpy/parse/cachefields.py`, `gutenbergpy/caches/sqlitecache.py`,
and `gutenbergpy/caches/gutenbergindex.db.sql`. Because there is no seam
to attach a small patch to, both vendoring and forking-and-publishing
mean owning a modified copy of gutenbergpy's cache-construction
dependency closure going forward — a closure larger than just these
five diffed files, since the orchestrating `GutenbergCache` class and
several further transitive dependencies live outside the diff (see
Required Change 3 for the fuller, still-provisional list). Vendoring
and forking-and-publishing differ in *where* that fork lives and how
it's packaged, not in whether a fork is required. See Required Changes
3 and 4 below, revised accordingly.

### Duplication search
- In-repo: No existing implementation or decision record found (grepped
  `lcats/src/`, `lcats/project/design/proposals/` for `gutenbergpy`;
  `.claude/skills/` does not exist in this repo, so it was skipped
  rather than searched. Only hits in the searched paths were unrelated
  design/execution docs referencing the dependency in passing).
- Sibling repos: None identified — this is LCATS-specific.
- External libraries: None identified as an alternative; the two
  realistic implementation paths (vendoring in-tree vs. publishing a
  maintained fork) both require forking the same gutenbergpy
  cache-construction dependency closure —
  see Problem/Context.
- Recommendation: Proceed.

### Demand search
- Work items: None found.
- Proposals: None found.
- Backlog: No `project/design/backlog.md` in this repo.
- Recommendation: No action.

## Scope

- Decide among: (a) wait for upstream to cut a new PyPI release (contact
  already made, response pending), (b) fork gutenbergpy's cache-
  construction dependency closure into LCATS's own tree and point
  `lcats/src/lcats/gettenberg/cache.py` at that local copy instead of
  the installed package, (c) publish and maintain a distinct-named
  LCATS-controlled PyPI fork of the same closure. That closure is
  larger than just the two PRs' diff — see Required Change 3.
- Update `lcats/pyproject.toml`'s and `lcats/environment.yml`'s
  dependency declarations to remove the direct VCS reference, per
  whichever path is chosen.
- If vendoring (b) or forking-and-publishing (c), add a real
  (non-mocked) regression test covering the forked parser/cache-writer
  logic — both options carry the same code-ownership burden.
- If re-fork-and-publish, scope the fork's actual PyPI publish as a
  separate prerequisite work item rather than performing it here, and
  budget for the fork's own packaging/dependency modernization (see
  Required Change 4).
- Verify existing Gutenberg-fetching functionality is unaffected.

## Required Changes

1. Record the decision and rationale (in this work item's Problem/Context
   or its execution record).
2. Update `lcats/pyproject.toml:26`'s `gutenbergpy` dependency
   accordingly. Also update `lcats/environment.yml:263`, which pins the
   identical `gutenbergpy @ git+https://...` reference for the conda
   development environment — leaving it unchanged would mean
   contributors recreating the documented conda environment continue
   pulling the old fork commit, and tests run in that environment could
   mask a broken vendored or PyPI dependency.
3. If vendoring: the two upstream PRs' diff touches five files
   (`gutenbergpy/parse/rdfparser.py`, `gutenbergpy/parse/book.py`,
   `gutenbergpy/parse/cachefields.py`, `gutenbergpy/caches/sqlitecache.py`,
   `gutenbergpy/caches/gutenbergindex.db.sql`), but the file list
   actually needed to run the cache-construction pipeline standalone is
   larger, since `SQLiteCache.create_cache()` also reads
   `gutenbergpy/caches/gutenbergindex_indices.db.sql` (a second SQL
   resource, not part of the PR diff), and the orchestrating
   `GutenbergCache` class referenced below lives in a sixth file,
   `gutenbergpy/gutenbergcache.py`, not in the diff either. A closer
   read of `gutenbergpy/caches/sqlitecache.py`'s own imports turns up
   further transitive dependencies not yet enumerated here —
   `gutenbergpy/caches/cache.py` (the abstract `Cache` base class
   `SQLiteCache` extends), `gutenbergpy/gutenbergcachesettings.py`, and
   `gutenbergpy/utils.py`. Do not treat any file list in this work item
   as complete: at implementation time, trace gutenbergpy's actual
   import graph from `GutenbergCache.create()` (e.g. via
   `python -m py_compile` / `importlib` tooling, or by reading each
   module's imports transitively) to determine the real vendoring
   closure, rather than trusting a hand-enumerated list — this list has
   already grown twice from independent review, which is itself
   evidence hand-enumeration is unreliable here. Vendor that verified
   closure, with the merged fixes already applied, into a local module
   tree under `lcats/src/lcats/gettenberg/` (e.g. a
   `_vendor_gutenbergpy/` subpackage), attributing the source PRs in a
   header comment. Update `lcats/src/lcats/gettenberg/cache.py:11,128,144`
   to call the vendored copy's `GutenbergCache.create()`/`.get_cache()`
   instead of the installed `gutenbergpy` package's — there is no
   constructor parameter or other extension point on
   `GutenbergCache.create()` to substitute a patched
   `RdfParser`/`SQLiteCache` without doing this, since it imports and
   instantiates both by name internally. This is an in-tree fork of
   gutenbergpy's cache-construction subsystem, not a small patch file;
   treat future upstream changes to this closure as needing manual
   re-porting (see Risk Notes). Add a real parser/cache-writer
   regression test alongside the fork —
   `tests/gettenberg_tests/cache_test.py` mocks `GutenbergCache.create`
   and `metadata_test.py` injects fake query rows via `_FakeCache`, so
   rerunning the existing suite alone cannot demonstrate the forked
   alias-table/title logic is actually correct; an incomplete fork
   could satisfy "tests pass unchanged" while newly built caches remain
   wrong. Per `AGENTS.md`'s mocking/test philosophy ("avoid heavy
   mocking... validate behavior, not that mocks were called"), the new
   test should exercise the real parsing/cache-write path and assert on
   the resulting title associations and alias tables, not a mocked
   stand-in.
4. If forking-and-publishing: reserve a distinct PyPI project name (not
   `gutenbergpy` — confirmed MIT-licensed, so forking and republishing
   under a new name with the copyright/license notice preserved is
   legally clean, but the name itself must not squat the upstream
   maintainer's active namespace). Budget for upstream's own packaging
   being legacy-style — a bare `setup.py` plus metadata in `setup.cfg`,
   no PEP 621 `pyproject.toml` project table — and for dated
   dependencies (`future`, `httpsproxy-urllib2`, `lxml`, `pymongo`,
   `chardet`) inherited by the fork. Set up a second, independent
   release pipeline (Trusted Publishing, versioning, a runbook) for the
   fork, duplicating `WI-RELEASE-0038`'s scope for a second package.
   This work item's `forbidden_actions` includes `publish_package`
   (scoped to `lcats` itself, the actual release blocker this item
   exists to unblock) — so the fork's own publish is out of scope for
   this item regardless of which path is chosen; if re-fork-and-publish
   is selected, scope the fork's publish (including the packaging and
   release-pipeline work above) as an explicit, separate prerequisite
   work item rather than performing it inline here.
5. Run `lcats/src/lcats/gettenberg/`'s test suite, including the new
   regression test from step 3, to confirm no behavior regression.

## Non-Goals

- Does not implement the full LCATS PyPI publish workflow or CI
  changes — separate future work.
- Does not update `README.md:33`'s stale "not yet supported" claim —
  separate item.
- Does not build `scripts/version`/release-smoke tooling — that's
  WI-RELEASE-0038.
- Does not actually publish `lcats` to PyPI.

## Acceptance Criteria

- A documented decision (vendor the fix vs. publish/maintain a
  distinct-named LCATS-controlled PyPI fork vs. wait on upstream) exists
  with rationale, including why "wait on upstream" is or isn't viable
  given no ETA.
- `lcats/pyproject.toml`'s gutenbergpy dependency (currently
  `lcats/pyproject.toml:26`, a git+https direct reference) no longer
  contains a git+https or other direct URL reference.
- `lcats/environment.yml`'s matching gutenbergpy pin (currently
  `environment.yml:263`) is updated to the same replacement, so the
  documented conda environment doesn't silently keep installing the old
  fork.
- If vendoring: gutenbergpy's actual, traced (not hand-guessed) import
  closure for `GutenbergCache.create()` — starting from the two PRs'
  five diffed files but confirmed to also include at least
  `gutenbergcache.py`, `gutenbergindex_indices.db.sql`, `cache.py`,
  `gutenbergcachesettings.py`, and `utils.py` — with the merged fixes
  applied, is present as a local module tree under
  `lcats/src/lcats/gettenberg/` with clear attribution pointing at PR
  #25/#26; `cache.py:11,128,144` call the vendored copy, not the
  installed `gutenbergpy` package, for cache construction; and a new
  regression test exercises the real parser/cache-writer path (not the
  mocked `GutenbergCache.create` or fake-row `_FakeCache` paths already
  in the suite) and asserts on the resulting title associations and
  alias tables.
- If re-fork-and-publish: a distinct PyPI project name is reserved (not
  `gutenbergpy`, to avoid squatting the upstream maintainer's
  namespace); the fork's own packaging (upstream's legacy `setup.py`/
  `setup.cfg`) builds cleanly and its dependency list has been reviewed
  for staleness; a release pipeline for the fork exists; the actual
  publish is scoped as a separate prerequisite work item, consistent
  with this item's own `forbidden_actions: publish_package`; once
  published, `lcats/pyproject.toml` pins it by version, not URL.
- `lcats/src/lcats/gettenberg/` tests, including the new regression
  test where applicable, pass unchanged in behavior after
  the change.
- A built wheel's metadata contains no direct URL/VCS reference
  (verified via `twine check` and metadata inspection).
- `lrh validate` reports 0 errors.

## Validation

- `lrh validate`
- `scripts/test`
- `scripts/build && twine check dist/*`
- `for whl in dist/*.whl; do unzip -p "$whl" '*.dist-info/METADATA'; done | grep -i gutenbergpy` (confirm no `git+`/URL reference remains; loops so multiple wheels in `dist/` are each checked, not just the first)

## Risk Notes

- Vendoring and re-fork-and-publish share the same underlying cost:
  both require forking the same five gutenbergpy-internal files, since
  `GutenbergCache.create()` has no extension point for substituting a
  patched parser/cache-writer (see Problem/Context). They differ only
  in where that fork lives and how it's packaged — vendoring keeps it
  private inside LCATS's own tree; re-fork-and-publish makes it a
  second, independently versioned, installable PyPI project. Neither
  option is a small patch.
- Vendoring permanently diverges LCATS's copy from upstream. The
  vendored files, copied in rather than pulled via a git dependency,
  won't carry upstream's own commit history or tags with them into
  LCATS's tree — so any future upstream fix to this closure has to be
  found and manually compared against upstream (e.g. via `git blame`/
  `git log` on the upstream repo directly) and re-applied by hand, not
  picked up by a version bump the way a real dependency would be.
- A separate LCATS-controlled PyPI fork adds an ongoing maintenance and
  security surface (a second package to keep current) plus a second,
  independent release pipeline (Trusted Publishing, versioning, a
  runbook) — effectively duplicating `WI-RELEASE-0038`'s scope for a
  package that isn't LCATS's actual deliverable. It also inherits
  upstream's legacy packaging (`setup.py`/`setup.cfg`, no PEP 621
  project table) and dated dependencies (`future`,
  `httpsproxy-urllib2`, `lxml`, `pymongo`, `chardet`).
- "Wait on upstream" now has an active maintainer contact in progress
  (as of this work item's latest update) but still no committed ETA —
  `raduangelescu/gutenbergpy:master`'s `setup.cfg` already shows an
  unreleased `version = 0.3.6` bump, a mildly encouraging but
  non-committal signal. Continue to treat this as a
  considered-and-possibly-rejected option pending the maintainer's
  response, not a settled plan to wait indefinitely.

## Open Questions

- Maintainer response on release timing (Option A) is pending as of
  this update; revisit this work item's decision once it arrives.
- PyPI project-name availability for a re-fork-and-publish path (e.g.
  `lcats-gutenbergpy` or similar) has not been confirmed — a check
  attempt was blocked by PyPI's bot-challenge page and needs to be
  redone before that option could actually proceed.
