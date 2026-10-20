# Independent source-disposition review

Cold assignment source_disposition_review, dispatched about22:04 UTC, completed
before22:18 UTC. Report only; no recursive agents or skills. Scope: tranche from
3d01fb82, experiment runner/tests, evidence and eight actual source decisions;
not whole PR524 or integration approval. Current files and originals inspected.

## Finding and repair

P2: initial runner computed changed IDs with row.get("body_equal") is False.
Removing the field on unreviewed ID50921 silently reduced counts to1641 changed /
1634 uncovered despite the recorded total1642. Coordinator directly reproduced
this against real inputs (coverage-gap-red.log.gz). Repair validates status,
comparison types and source/corpus bindings for every population row, then checks
reported summary/totals when present. Added regression variants for missing field,
None/int/string values, unexpected status and changed identity.

Coordinator green reproduction rejects the exact malformed input and real intact
reconciliation retains1642 changed /7 covered /1635 uncovered. Narrow independent
repair recheck completed before22:18 UTC: missing field, None/0/1/string values
and disguised cleanup refusal all rejected; actual counts and deferred63889 remain
correct; seven focused tests pass. No remaining actionable issue in recheck.
Reviewed runner SHA256:
feb6be8ecc5a8c60b11409efa2132dc6db8ee8e286c679726ac970e1a3597dc8.
Two assignments total, initial under14 minutes plus recheck under2 minutes;
within20+10 /30 worker-minute ceilings. No extra cold review or hosted retrigger.

## Independently checked evidence

- All six exclusions have genuine named/numbered narrative divisions; verified
  adjacent source prose and retained-body truncation/advertisement claims.
- Complete narratives read for23762 and63889. Approval preserves9876 characters
  and differs from retained body only by three newlines and THE END. Candidate
  Gutenberg end notice is correctly disclosed. Interior caption supports deferral.
- Actual reconciliation/publication replays match archived substantive results:
  seven covered,1635 uncovered; one temporary publication, seven withheld.
- All1659 source/canonical hashes match baseline; product ledger matches.
- Initial six tests and final seven focused tests pass. Black/Ruff checks passed;
  combined Black sandbox IPC failure recovered with individual-file checks.
- Reviewer inspected canonical successful log but did not independently rerun
  scripts/test. Coordinator owns the full canonical validation claim.

Minor precision note accepted:63889 differs by522 frontmatter characters plus
two40-character asterism lines, not just frontmatter. Coordinator verified all
three exact insertion operations and archived63889-differences.json.

Commands: project Python/PYTHONPATH unittest disposition_tranche_evidence_test;
reconcile_review_tranche.py; qualify_readiness_cases.py; individual Black checks;
Ruff --no-cache; inline Python source/boundary/hash and malformed-row checks.
Independent temporary reports: /tmp/gettenberg-source-disposition-independent-review.json
and /tmp/gettenberg-source-disposition-independent-publication.json.
