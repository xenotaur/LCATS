# Reviewed promotional-preface evidence

Human grant: two-hour target /three-hour hard stop from 2026-10-22 06:43:57 UTC.
Starting commit `3c040b2d`; continuation of PR #524, no integration/main promotion.

## Outcome

Two explicitly attributed promotional introductions (63638, 73988) now have exact,
individually reviewed span-role packets. The first note identifies the editor's
reaction to Noel Loomis's story and addresses readers; the second identifies the
publisher/editor's search for humorous fiction and praises this story. Original
labels and exact text are preserved in hypothetical publisher_blurb metadata.
These are attributed judgments about the cached source, not authenticated original
publisher authorship. The verifier proves identity/coordinate consistency, not semantics.

The delimited-note locator finds exactly two matching candidates among 1,640 in the
1,659-input population, within its 8,192-character opening window and 2,048-character
complete-paragraph bound. This is a coverage count for that syntax, not a count of
all blurbs. Discovery never grants a role. Only the two explicit review packets
supply those judgments; no general classifier or automatic recording path is added.

Both stories still fail readiness and complete historical accounting. Every previous
ledger field is unchanged. Cumulative historical counts remain 14 resolved /1,628
unresolved; candidate intent remains 1,585 unreviewed /13 approve /7 exclude /35 defer,
with zero conflicts. No new decisions, approvals or resolutions. All 55 inherited
records and all 25 diagnostic deferrals remain unchanged. The mixed publisher preface
in 42664 is deliberately excluded from the first promotional family.

The available 27 HTML cache files do not cover the 25 diagnostic cases. Epigraphs,
fictional introductions, narrative editor references and unlabelled teasers remain
counterexamples or unresolved. No original-magazine scans or other sources were
acquired. Further identical note-family runs will not resolve that evidence gap.

## Artifacts and reproduction

- `reviewed-prefaces.json`: the two explicit source-role judgments, not dispositions.
- `ledger.json.gz`, `summary.json`: whole-population replay in 31.085 seconds with
  separate partial-proof/proposed-selection fields. Each hypothetical selection binds
  exact omissions, retained spans, editorial text, readiness and residual history.
- `independent-source-evidence.json`: the investigator's source/context observations,
  counterexamples, HTML inventory and 25-cohort anchor checks. Its `positive_cases`
  field includes the inspected mixed case 42664 with an explicit excluded role; the
  actual reviewed catalogue contains only 63638 and 73988. The wider exploratory
  search is not a proof of absence or an exhaustive literary review.
- `disposition-manifest.json` references and hashes all 55 immutable records in their
  original archives. `cumulative-reviews.json` preserves the existing 41 reviews.
- `withholding.json`: real disposable gathering retains full candidates and withholds
  all 27 cases. Positive actual publication with separate editorial metadata is tested
  on authored fixtures with independently supplied complete-story approval only.
- `wheel.json`, `installed.json`, compressed logs and `validation.json`: validation.
  Initial failures are retained: a wrong test capture-helper name, and a temporary
  probe preparation error treating the cases wrapper as a list. Both were repaired;
  neither caused a product change or suppressed a test.

From `lcats/`, project environment and `PYTHONPATH="$PWD/src"`:

```bash
python ../experiments/10_gettenberg_qualification/scripts/qualify_editorial_evidence.py \
  ../experiments/10_gettenberg_qualification/results/gettenberg-readiness-20261020/census-final.json.gz \
  ../experiments/10_gettenberg_qualification/results/gettenberg-readiness-20261020/full-corpus-final.json.gz \
  QUEUE CUMULATIVE_DISPOSITIONS TEXT_CACHE ../corpora/mass_quantities \
  ../experiments/10_gettenberg_qualification/results/gettenberg-editorial-20261022/cumulative-reviews.json \
  ../experiments/10_gettenberg_qualification/results/gettenberg-editorial-20261022/reviewed-prefaces.json \
  NEW_OUTPUT_DIRECTORY
python -m unittest tests.gatherers_tests.editorial_evidence_test tests.gettenberg_tests.editorial_evidence_runner_test
```

Assemble CUMULATIVE_DISPOSITIONS from the exact `repository_path` entries in the
manifest, verifying hashes first. Use the existing content-addressed candidate queue
and historical decoded/re-encoded UTF-8 gzip source cache; they are not original HTTP
bytes. Missing/stale inputs fail without acquisition. The runner uses the existing
bounded readers, a 600-second POSIX alarm, 6GiB free minimum, socket denial and exclusive
output outside input directories. See the parent README for explicit format/lint.
The source verifier requires a unique unchanged candidate interval in normalized
source; repeated/ambiguous mappings are refused rather than guessed.

## Validation and next decision

3,118 canonical tests /105.330s; 10 focused tests; package and explicit runner
format/lint pass. Fresh isolated wheel has 174 Python modules and 2 JSON resources
byte-identical to source and install, no gutenbergpy; installed smoke, pip check and
all 10 focused tests pass. All 1,659 source/corpus identities and all 55 disposition
references were directly reverified. LRH: zero errors, 351 existing warnings.
Cold independent review found no actionable findings, passed all 10 focused tests,
rejected 48 malformed/stale packets and reproduced all 1,659 ledger rows. Coordinator
reverified reviewed code hashes, the identical replay ledger, all source/corpus
identities and all 55 prior dispositions. See independent-review.json and
coordinator-reverification.json; no repair recheck was needed.

The [evidence milestone](../../../../lcats/project/development/gettenberg-opening-evidence-milestone.md)
presents targeted source acquisition, explicit collection policies and a separate
software-versus-curation delivery decision as options. No acceptance gate is changed.
No canonical corpus mutation, default extraction change, integration, main promotion,
package publication, persistent-consent change or terminal closeout.
