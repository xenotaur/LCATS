# Saved-candidate review workflow qualification — 2026-10-20

Product d3bdff07860d477bea421aff296565c944c89398 completes the previously unfinished
review-tooling tranche. This is a workflow qualification, not corpus acceptance or
permission to integrate PR524. See the [user guide](../../../../lcats/docs/how-to/gettenberg-review.md),
[reference](../../../../lcats/docs/reference/gettenberg-review.md),
[workflow contract](../../../../lcats/project/development/gettenberg-review-workflow.md)
and [runlog](../../../../lcats/project/development/gettenberg-development-log.md).

## Results and evidence boundaries

- Final reconstruction of all 1,659 immutable inputs matches the earlier census:
  1,640 needs_review, 13 cleanup_refused, five ready, one ineligible. Queue scan
  reads 59,323,700 JSON bytes and retains all 1,640 exact candidate generations.
- Eight earlier explicit approvals are represented without changing their decisions;
  one earlier source-grounded exclusion and one deferral are recorded separately.
  Inventory: 1,630 unreviewed, eight approve, one exclude, one defer. These are
  reviewer-intent records, not ten new literary reviews or accepted historical
  body-difference dispositions. No new blanket acceptance or heuristic deletion.
- Twenty first/last preview windows across those ten reviewed inputs preserve exact
  text and omissions. Window fidelity is not a new full-narrative assessment.
- Exported approvals equal the prior explicit inputs through readiness.load_decisions.
  A separate 28-case publication runner consumes the actual exported file: 13
  temporary publications (eight explicit, five automatic), 14 withheld candidates,
  one ineligible source. These temporary outputs are removed by the runner.
- Post-run hashes verify all 1,659 canonical story files and compressed sources
  unchanged. Queue generation and review commands publish no stories. No Gutenberg
  requests occur. Historical decoded UTF-8 caches do not establish wire-byte
  transport/encoding correctness or authorize live original-byte approval.
- 3,027 canonical tests pass in 89.079s; 41 focused checks and 12 documentation
  checks pass. The latter execute all nine new guide commands through real CLI
  dispatch and actual authored-source publication. Package and 16 experiment
  runners pass format/lint. LRH reports zero errors / 351 pre-existing warnings.
- [Independent review](review.md) finds no actionable defect. It independently
  checks focused tests, queue counts, exported decisions and report fingerprints.
- The isolated wheel build and fresh venv installation succeeded offline using
  cached wheel bytes. All 171 Python modules and two JSON data files match source,
  wheel and installed package exactly. No extra modules, gutenbergpy or VCS
  requirement. Installed list/show/approve/exclude/defer/export, conflict visibility,
  explicit publication, CLI help and pip check pass outside the checkout.

## Reproduction and failures retained

Run the commands in the [experiment README](../../README.md#saved-candidate-review-workflow-qualification)
from lcats/ with the project interpreter and PYTHONPATH pointing to this checkout.
Use the pinned catalog archive SHA256
358f177c30818027ad93b3478da2248d7996999475d83e59288ee74423050b28,
original historical text cache and canonical collection. Explicit input files are:

- ../gettenberg-readiness-20261020/census-final.json.gz
- ../gettenberg-readiness-20261020/review-decisions-derivation-bound.json
- ../gettenberg-review-workflow-20261020-incomplete/reviewed-annotations.json

The final workflow report records their exact hashes, product and runner ledgers,
compact disposition records, inventory and per-source identities. Full candidate
bodies stay in the local work directory and are not duplicated here. Use fresh work
and output paths. Final replay elapsed 20.694s; it supersedes workflow.json for the
output-reuse repair, without rewriting that earlier report. Both classifications
match. Source ledgers bind the final candidate rather than inferring validity from
identical output counts. Manifest includes compressed and original hashes.

Initial canonical.log has two failing obsolete documentation expectations after
moving the approval example into the new guide. Tests now execute the replacement
commands; canonical-final.log supersedes it. The JSON-type reuse regression fails
before the fix (json-types-red.log) and passes afterward (json-types-green.log).
Canonical JSON identity now distinguishes booleans, integers and floats in existing
outputs. No malformed existing file is overwritten. Sandbox-only format/lint
failures are retained separately; approved execution passes those same checks.

The online isolated build failed on PyPI DNS, not package code. Complete cached pip
wheel ZIP bytes were recovered into a temporary wheelhouse; filenames preserve the
complete compressed WHEEL tag set (including py2.py3). The first offline install
missed universal-wheel compatibility because recovery initially retained only the
first tag; install-offline-fixed.log records the corrected recovery and successful
fresh resolution. No declared dependency or global environment changed. Reproduce
with a populated wheelhouse, PIP_NO_INDEX=1 and PIP_FIND_LINKS pointing to it, then
python -m build --wheel and pip install the resulting wheel into a fresh venv.
The wheel and installed freeze record exact artifacts; do not infer current online
resolution from this offline check. Temporary recovery/check orchestration is not
product code. The durable installed smoke is qualify_installed.py.

## Remaining work

1,630 workflow candidates remain unreviewed, in addition to unresolved corpus
acceptance obligations. The 1,640 review candidates and 1,642 changed historical
bodies are different sets. This run does not resolve the latter. Exclude/defer are
audit intent only and do not mutate collection membership. Broader source-grounded
dispositions, final WI0010 acceptance, integration, human main promotion and native
closeout remain separate gates. Original and incomplete-run evidence remain intact.
