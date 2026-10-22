# Numeric-marker terminal-notice investigation — 2026-10-22

Status: **experiment only; no product, active-gate, corpus or scope-adoption change**.
User approved this follow-up with an 11am Pacific hard stop. Start 17:28:31 UTC,
stop 18:00 UTC. The experiment extends the prior title-matched candidate with explicit
source/catalog identity and title corroboration; no gather algorithms are changed.

## Population result

| Measurement | Result |
|---|---:|
| All pinned inputs checked |1,659|
| Combined-candidate bodies freshly extracted / unchanged refusals |1,646 /13|
| Numeric rule changes cleanup slice |367|
| Numeric rule changes normalized body |366|
| Additional legacy body equalities restored |366|
| Remaining differences: original /title candidate /combined candidate |902 /433 /67|
| Legacy body equalities restored by both candidates together |835|
| New differences among previously equal bodies (either baseline) |0|
| Eligibility changes versus title candidate /differences versus legacy |0 /0|

Both diagnosed fallback-suppression cases regain their exact archived legacy body
hashes. 35401 (*Friend Island*) stays at 26,080 characters through the title candidate;
the numeric rule does not touch it. 50103 (*The Dwindling Years*) returns from 900 to 31,972
characters with a 10-chunk first candidate and fallback restored. The numeric rule also
removes a notice from 61499 (*Monopoly*), but its 54,282-character body was already equal
and remains unchanged. This explains 367 slice changes but 366 body changes.

The 67 remaining body differences are explicitly retained: 10 numeric notices with
nonmatching catalog titles, 56 cases outside the single-line grammar, and the one
leading-LF difference previously measured for 32655. `residual-groups.json` enumerates
every ID and binds the previous grouping. No punctuation normalization, subtitle
trimming, spelling inference or fuzzy title matching is introduced. These are
mechanical groups, not qualified families or publication approvals. All 13 conservative
cleanup refusals remain explicit too. Legacy equality is not literary correctness.

## Proposed narrow contract

The numeric experiment runs **after** the prior title-matched cleanup candidate.
It shortens content only when all of the following hold:

1. Cleanup already accepted a unique corroborated start/end envelope, with no extra
   markers or diagnostics beyond `envelope_removed`.
2. The caller's positive integer source ID equals the catalog ebook ID and the exact
   canonical decimal identifier of both envelope markers. Missing, wrong, string,
   boolean or zero-padded IDs do not qualify.
3. The final nonblank physical line is a complete terminal notice in the existing
   two-form grammar; wrapped, quoted or embedded narrative notices do not qualify.
4. The notice title equals a projected catalog title under the cleaner's existing
   case/horizontal-space comparison, and the author field is nonempty.
5. Removing that line leaves nonempty content. Original characters/newlines and
   half-open offsets remain available; earlier internal notices are not removed.

Author nonemptiness follows the earlier rule; catalog-author equality is not claimed.
Missing corroboration preserves the previous result. The helper is experiment-specific,
uses pinned private cleaner helpers, and inherits the old policy label; it is not a
production API or release. The source adapter already has source and catalog context.
A later implementation must expose that context explicitly and version/bind derivation
provenance appropriately; the pure text cleaner must not silently access a catalog or
network. API placement and final-candidate qualification remain implementation decisions.

## Reproduction and bounds

From `lcats/`, in the historical LCATS project environment:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python \
  ../experiments/10_gettenberg_qualification/scripts/audit_numeric_notices.py \
  CATALOG_CACHE TEXT_CACHE /tmp/NEW_REPORT.json
PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=src:../experiments/10_gettenberg_qualification/scripts \
  scripts/test numeric_notice_candidate_test
scripts/format --check --diff -- \
  ../experiments/10_gettenberg_qualification/scripts/numeric_notice_candidate.py \
  ../experiments/10_gettenberg_qualification/scripts/numeric_notice_candidate_test.py \
  ../experiments/10_gettenberg_qualification/scripts/audit_numeric_notices.py
scripts/lint \
  ../experiments/10_gettenberg_qualification/scripts/numeric_notice_candidate.py \
  ../experiments/10_gettenberg_qualification/scripts/numeric_notice_candidate_test.py \
  ../experiments/10_gettenberg_qualification/scripts/audit_numeric_notices.py
```

Local inputs: existing catalog `/tmp/gettenberg-dispositions-20261020/cache` and
text cache `/Users/centaur/Tempspace/Projects/LCATS/cache/texts`. The original corpus
paths are the fixed machine-local paths in the previous comparison. Do not point this
runner at a changing corpus. Every cached gzip, decoded text and corpus file is hash-
checked; projected titles/authors/aliases and catalog ebook identity are rechecked.

To fit the shortened grant, this experiment **reuses**, rather than reexecutes, the
previous three-way comparison. Its compressed bytes and old helpers are bound to Git
`1488c69ab11fad8fcd78361653bbd261a2788680`; relevant executing product modules are
path/hash checked against the previous report. Product ref remains 6a873b61. The same
historical parser 335855c0 is loaded and hash checked. All 1,646 accepted inputs receive
fresh combined-candidate extraction/normalization. The 1,279 bodies whose cleanup slice
is unchanged also reproduce their previous normalized hash. The 367 changed slices
have fresh measurements, including the one whose body remains equal. The previous
3,292 old/new hashes are historical reused evidence, not freshly reexecuted claims.

No setup/download/cache/corpus write or publication. Socket creation denied during
processing. POSIX alarm 600 seconds, Git 30 seconds, gzip input 32 MiB compressed/expanded.
Completed in 196.868 seconds. Output parent must exist and output must be new, outside
repository/cache roots; failures raise without a completed report. Progress is emitted
every 200 rows. Temporary historical module removed. The shared historical helper needs
the already-installed gutenbergpy measurement dependency; do not restore it to product
requirements. Original HTTP representation/resource/decoding equivalence cannot be
established from these historical decoded/re-encoded UTF-8 cache bytes. Metadata-source
projection differences and actual public gathering require separate qualification.

## Evidence and validation

- `corpus-comparison.json.gz`: fresh per-input candidate measurements, baseline
  references, source/catalog bindings, exact removed text/spans and two detailed traces.
- `independent-probes.json.gz`: independently executed severe-case probes and boundary
  checks; comparison hashes match the full report.
- `residual-groups.json`: coordinator grouping of the 67 explicit residuals.
- `review.json`: independent review, final script hashes and precise verification limits.
- `checks/`: commands, exit codes, focused tests and help/protection smokes. Verbatim
  text logs are losslessly compressed to avoid altering captured whitespace.
- `validation.json` and `manifest.json`: final validation and exact archive byte bindings.

Independent review found no unresolved issues: all population counts and all 367
removed suffixes were checked against source bytes and rule constraints; two real
extractions independently reproduce the severe-case hashes/traces. The reviewer ran
15 additional boundary probes. The ten-title residual list is coordinator evidence,
not separately audited by the reviewer. No second complete extraction replay occurred.

Eight focused tests run through canonical `scripts/test numeric_notice_candidate_test`.
Canonical package format/lint and explicit checks of all three experiment files pass.
Help and existing-output/missing-cache/protected-output refusals pass. No full package
suite, installed-wheel/public-gather acceptance or source download is claimed. Full
comparison completed successfully on its first run. Independent review is recorded in
its own artifact; historical output equality is not a corpus approval.

## Recommendation

Stop expanding this notice family. The combined narrow candidates repair both
established truncations and explain 835 of 902 original cleanup-body differences by
restored legacy equality, without a broader gather rewrite. Present the evidence for
human review of PR #528's scope split and revised qualification criteria, then construct
and qualify a narrower delivery candidate if approved. Keep the 67 residuals and 13
refusals in its causal ledger; classify material effects with evidence, not blanket
acceptance or a requirement to complete the old editorial backlog. Do not silently
turn the 10 title mismatches into a fuzzy-matching follow-up.

[Scope audit](../../../../lcats/project/development/gettenberg-scope-causality-audit.md).
[Prior terminal-notice experiment](../gettenberg-terminal-notice-audit-20261022/README.md).
[Runlog](../../../../lcats/project/development/gettenberg-development-log.md).
