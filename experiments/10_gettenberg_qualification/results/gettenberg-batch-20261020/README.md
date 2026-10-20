# Batch review qualification —2026-10-20

WI-GETTENBERG-0010 / PR #524 continuation from 0c9d4b3e. The human approved narrow
rules with per-input evidence and unresolved exceptions. This experiment qualifies
one opt-in rule and measures its limits; it does not accept the corpus or authorize
integration/main promotion. See the [decision checkpoint](../../../../lcats/project/development/gettenberg-batch-review-milestone.md).

## Final results

[Summary](summary.json.gz), [full per-input ledger](ledger.json.gz),
[explicit approvals](approvals.json), [immutable disposition](dispositions/).

| Measurement | Result |
|---|---:|
| Immutable corpus inputs checked |1,659|
| Historical changed bodies |1,642|
| Earlier source-review resolutions retained |7|
| New qualified rule disposition |1 (70154)|
| Historical changed bodies still unresolved |1,634|
| Grammar-matched complete publication notices |734|
| Interior notices (all start within first 1,500 candidate characters) |688|
| Boundary-rule matches |46|
| Selected readiness plus retained-label guard passed |12|
| Entire historical difference explained with no prior intent |1|

Final run 17.741 seconds; no Gutenberg/network requests, catalog rebuild or canonical
publication. Cumulative input inventory is 18 intents: 9 approve, 7 exclude, 2 defer;
1,622 candidate inputs unreviewed. The new separate disposition adds one approval;
the independently replayed [combined inventory](combined-inventory.json.gz) is10 approve, 7 exclude, 2 defer,
1,621 unreviewed. This is intent accounting, distinct from historical resolution.
Earlier eight approval smoke cases remain historical-difference gaps; none were
silently subtracted. All 1,659 inputs, including 13 cleanup refusals, remain in the ledger.

70154 (*Murderer's Chain*) selects exact candidate Unicode [227, 20509),20,282 chars.
The removed 227 characters are the complete bracketed publication notice and separator
whitespace. The selected raw SHA256 equals historical extracted body, normalized
baseline and stored corpus body. Normalization provenance is null. This is an
agent-attributed qualified-rule disposition, not an individual human signature or
claim of a complete literary reading. Source freshness remains historical decoded
UTF-8 cache provenance, not newly acquired original-wire bytes.

The other 11 readiness-eligible matches do not fully explain their historical body
differences. Some retain apparent blurbs. Other matches retain caption/sidenote or
readiness findings. Interior notes cannot be removed by a contiguous selection
without losing text on one side. Nothing is accepted solely from a common warning,
sampling, a regex match, old-output equality, or a ready assessment.

## Validation and repairs

3,053 canonical tests pass in 103.680s; 26 focused tests pass. Package format/lint and
explicit checks of all three changed experiment runners pass. LRH validation has
zero errors and351 pre-existing warnings. Fresh isolated build
and dependency installation succeed. All 172 Python modules and 2 JSON resources are
byte-equal across source, wheel and installed package. Installed rule proposal,
review CLI, withholding/publication, CLI/API imports and pip check pass. The wheel's
dirty version reflects uncommitted control-plane edits; source byte equality is the
qualification identity. Build/dependency installation may contact PyPI; corpus replay
and installed smoke disable network and make no Gutenberg requests.

[Actual gather replay](publication.json.gz):70154 publishes temporarily;32484
(unexplained blurb/difference),31948(sidenote),23337(interior note) and63889(prior defer)
remain needs_review. This uses the normal source-bound decision/publication path;
the temporary outputs are removed by the runner. All original compressed/decoded
sources and canonical files hash-equal the baseline ([post-test preservation](preservation-final.json)).

Cold independent review found two P1s and one P2. Coordinator reproduced all three:
trailing whitespace could lose a final narrative paragraph; an incomplete cumulative
inventory could override known prior exclusion; inconsistent equality flags could
hide changed bodies. Repairs check every removed piece, preserve unremoved exterior
whitespace, require every known prior disposition in cumulative inventory, and check
equality against valid normalized hashes. Authored regressions and independent narrow
recheck pass. [Initial review](gettenberg-batch-independent-review.json) and
[repair recheck](gettenberg-batch-independent-recheck.json) retain exact findings/hashes.
The reviewer found no such defects in the actual immutable input population.

History retains initial sidecar-discovery failure and pre-final measurements. The
first successful dry-run summary incorrectly included the unrecorded proposal in
resolved coverage; final default dry-run counting excludes it. Final recording mode
explicitly creates the disposition. Earlier test logs are pre-repair evidence only;
`test-repaired.log.gz` and `focused-all-repaired.log.gz` are authoritative. A short-body
fixture and a trailing-note whitespace fixture initially failed preconditions and
were corrected without weakening the preservation assertions.

## Reproduce

Follow the [batch runner instructions](../../README.md#batch-review-qualification).
Inputs: `../gettenberg-readiness-20261020/{census-final,full-corpus-final}.json.gz`,
the reconstructed candidate/cumulative disposition queue from the preceding run,
original cached text and mass_quantities corpus, and
`../gettenberg-dispositions-20261020/reviews-final.json` plus its `dispositions/`.
The preceding cumulative annotations/decisions can rebuild the queue with
qualify_review_workflow.py and the pinned local catalog. Run once without recording,
then in a new directory with `--record-qualified` after reviewing the rule/evidence.
Use cases.json and approvals.json with qualify_readiness_cases.py for publication.
No original source body is copied into this results directory; only bounded removed
notice text and identities are retained. Manifest hashes include expanded gzip bytes.
