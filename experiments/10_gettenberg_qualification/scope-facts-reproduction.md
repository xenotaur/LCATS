# Reproducing the scope-audit facts

The original [audit-facts.json](results/gettenberg-scope-audit-20261022/audit-facts.json)
is immutable historical evidence. The new
[reproduce_scope_facts.py](scripts/reproduce_scope_facts.py) runner reconstructs its
18 derivable fields and compares every value to that original record. It writes a
separate report, never modifies the original, and does not change product acceptance.

From `lcats/`, with the project Python environment active:

```bash
PYTHONDONTWRITEBYTECODE=1 python ../experiments/10_gettenberg_qualification/scripts/reproduce_scope_facts.py --help
PYTHONDONTWRITEBYTECODE=1 python ../experiments/10_gettenberg_qualification/scripts/reproduce_scope_facts.py /tmp/NEW_SCOPE_FACTS.json
scripts/format --check --diff -- ../experiments/10_gettenberg_qualification/scripts/reproduce_scope_facts.py
scripts/lint ../experiments/10_gettenberg_qualification/scripts/reproduce_scope_facts.py
```

Choose a new output filename. It must have an existing parent outside this repository.
No `PYTHONPATH`, cached catalog, text cache, or `gutenbergpy` installation is needed.
The runner uses Python's standard library and local Git. It requires POSIX `SIGALRM`
and the original commits to exist locally; it never fetches missing commits.

## What is recomputed

- **Git inventory:** `git diff --name-status` between qualification base
  `ed20e9c297bf5e50e1911b84722e53f5db3edee3` and pinned product head
  `6a873b611e3958bb9ddad8e84f2ad190831a9da7`, separately for `lcats/src/lcats`
  and its `gettenberg` package. Normalization and storymap equality compares
  source baseline `5cfd2d71caf6f3eedfdfc0b830b5c5ff1a74ba3b` to the pinned head.
- **AST contrast:** top-level parser functions from the original source baseline
  and pre-repair `335855c04cd7ba936815d2635969d94fdd278c71` are compared using
  `ast.dump(..., include_attributes=False)`. This reconstructs 47 shared functions
  with only `gather_story` changed. It is not whole-runtime equivalence.
- **Population:** statuses and normalized before/after/retained-corpus hashes in
  archived `gettenberg-qualification-20261018/corpus-after.json.gz` are counted
  directly: 1,646 compared, 13 refused, 744 equal, 902 changed, 742 new outputs
  matching retained corpus, and zero recorded metadata rejections. This rechecks
  archived arithmetic, not source extraction or original transport bytes.
- **37 additional English-query IDs:** the archived index report's `new_only` list
  and language records are intersected with the comparison population and pinned
  `SINGLE_STORIES`. The list is obtained from its literal AST; no storymap module
  is imported. Only the pinned pure `only_english` function is executed, with
  `set` as its sole available builtin, against each archived language list.
  Results: no comparison IDs, configured IDs 28219 and 57044, and no IDs passing
  only-English eligibility. This does not repeat the database query or establish
  all metadata/resource behavior.
- **Input identities:** all three input hashes in the original facts are checked,
  including narrative-cases.json (an identity check, not reinterpretation of its
  anchors). The original audit-facts.json itself has a fixed SHA-256 guard.

## Explicit exclusions

The fields `coordinator_replay_matches_investigator_rows`,
`investigator_report_sha256`, and `note` are historical observations about a
separate temporary investigator report. That report is not an archived input to
this runner. Their original values appear under `not_reproduced`, with a reason;
none contributes to `all_reproduced_fields_match`. The separate
[audit replay runner](scripts/audit_cleanup_causality.py) reproduces the archived
cleanup/extractor experiment under its own documented environment requirements.

## Safety, limits and smoke checks

The module is import-safe and has a main guard. It performs no network operations,
product imports, gathering, catalog setup, or corpus writes. Each archive is bounded
at 32 MiB; expanded gzip JSON at 64 MiB; Git subprocesses at 30 seconds each; the
whole CLI run at 120 seconds. Inputs must resolve to regular files inside the
repository. Evidence hashes are checked before using the records.

Existing output paths, including symlinks, and repository output paths are refused.
The complete comparison must succeed before exclusive output creation. Missing or
altered evidence, missing commits, mismatched facts, or changed original-record fields
raise errors without a completed report. Output is tens of KiB at most for these
pinned inputs. No full package-suite pass is implied by these diagnostic checks.

Smoke checks used for this repair: successful reproduction of all 18 fields; help
exit zero; import without loading `gutenbergpy`; repeated-output refusal with unchanged
output hash; repository-output refusal; symlink-output refusal; and missing-evidence
refusal without output. A smoke harness initially expected 19 fields, detected the
count error, and was corrected to 18; no measured archival value was changed.
