# Boundary residual grouping and terminal-note qualification

Grant:2026-10-22 00:43:14–01:13:14 UTC maximum. Starting commit819e62fa;
PR #524 remains open against the acquisition branch. WI-GETTENBERG-0010 remains nonterminal.

All 1,477 boundary-text cases were revalidated and grouped. Prefix groups:
749 other,265 underscore-leading,180 production-credit-leading,179 byline-leading,
19 sidenote-leading,18 transcriber-leading,11 illustration-leading,56 empty.
Suffix groups:1,013 empty,219 containing transcriber text,115 end-marker-leading,
130 other. These exclusive lexical labels describe each end, not editorial roles.
Both group totals equal1,477; prefix/suffix groups overlap at the book level.

The new opt-in finite terminal-note grammar qualifies 133 transformations across 77
normalized notice variants.25 have complete historical explanations after composing
with existing qualified notice omissions;108 retain other historical differences.
The133 include132 unreviewed inputs and1 prior approval; all prior intent is
preserved. No new dispositions, approvals, publications or historical resolutions.
The cumulative totals remain14 resolved /1,628 unresolved historical changes.

The219 transcriber-containing suffixes were the strongest clearly labeled family
for a finite grammar in this sprint.133 is measured qualification yield, not a
claim that no other rule could cover more inputs. Prefix prose and historical
truncations are deliberately not classified as disposable blurbs. Qualifying
headings/credits or additional publication formats requires separate evidence.

`groups.json.gz` preserves full boundary texts and per-input proofs. Each proof
uses original candidate Unicode offsets; projection offsets are diagnostic only.
Source candidate bodies are not duplicated here. `summary.json` binds the input
ledger by SHA256; that ledger is archived unchanged in
`../gettenberg-residual-20261022/ledger.json.gz`. Inputs use the existing immutable
candidate queue and decoded/re-encoded legacy text cache, not original HTTP bytes.

Reproduce from `lcats/` with project Python and `PYTHONPATH="$PWD/src"`:

```bash
python ../experiments/10_gettenberg_qualification/scripts/group_boundary_cases.py ../experiments/10_gettenberg_qualification/results/gettenberg-residual-20261022/ledger.json.gz /tmp/gettenberg-dispositions-20261020/repaired-work/candidates ../corpora/mass_quantities /Users/centaur/Tempspace/Projects/LCATS/cache/texts NEW_OUTPUT
python -m unittest tests.gatherers_tests.trailing_notice_test tests.gettenberg_tests.boundary_groups_evidence_test
```

The queue/cache are external immutable inputs; paths reflect this run and must be
provided on another host. Use the earlier readiness/disposition experiment to
reconstruct the pinned candidate generation before replaying if temporary files
are unavailable. Missing or mismatched inputs fail, never fetch replacements.
See the parent experiment README for resource bounds and failure behavior.

Validation: 3,100 canonical tests in 109.767s; targeted 9 tests; package and changed
runner format/lint pass. Fresh isolated wheel/install matches all 173 Python and 2
JSON source files, no gutenbergpy; installed smoke and pip check pass. Three new
rule tests also pass against the installed wheel. All 1,659 corpus/source identities
remain unchanged. Independent cold review reproduced all 1,477 rows and checked all
133 proofs; coordinator separately verified original cuts/text/hashes for all 133.
No Gutenberg requests; PyPI used only for isolated wheel dependencies.

Next: integrate this qualified transformation into the explicit ordered-decision
path, inspect all 25 history-complete cases for retained editorial material and
readiness, then run disposable publication/cumulative reconciliation before any
new approval. Historical equivalence alone remains insufficient. Retain exceptions.

The manifest binds all archived files except itself; logs are losslessly gzip
compressed. Temporary prototype scripts were not promoted into the control plane.
