# Scope and causality audit — 2026-10-22

This is a decision-support experiment, not a product change, accepted corpus, or new
qualification gate. Pinned product head: `6a873b611e3958bb9ddad8e84f2ad190831a9da7`.
Human-authorized audit: two-hour target /three-hour maximum from 07:49:48 UTC.

## Result

The early comparison isolates cleanup effects with a fixed extractor. The later
historical-review backlog combines cleanup effects and our extractor/review changes.
The replacement needs an integration mitigation for demonstrated narrative truncation;
that does not establish that the entire gather overhaul is necessary.

- `causal-replay-pre-review.json.gz`: preserved coordinator replay before imported-module
  location guards; its rows match the corrected replay.
- `causal-replay.json.gz`: eight cases × two cleaners × two extractors; coordinator
  replay matches the investigator's rows after renaming one overbroad field to
  `exact_anchor_interval_preserved`. All16 earlier normalized hashes reproduce.
- `audit-facts.json`: independently checked Git inventory, parser AST contrast,
  population counts, source identities and metadata-selection checks.
- `validation.json`: commands, result summaries and boundaries of this audit's checks.
- `review.json`: independent audit review and any corrections/recheck.
- `manifest.json`: archive file hashes; excludes itself.

No story publication is exercised by this diagnostic. Current readiness is assessed
as a pure function. The eight source anchor intervals were reviewed in a historical
coordinator investigation, not independently reinterpreted here. Exact interval
retention is not semantic approval; typography changes can produce a false result.

Early population arithmetic is 744 old/new equal + 902 changed + 13 refused = 1,659.
Of the 744 equal cases, 742 also match retained corpus output and two do not. The
historical summary's 742 `same_body` count must not be read as old/new equality.

## Reproduction

From `lcats/`, in the historical LCATS measurement environment (Python 3.11.9), with
`PYTHONPATH=src`. The environment needs the already-installed historical gutenbergpy
cleaner whose SHA is checked against the archive; do not add it back to product
requirements or install it automatically. The final delivery package remains a
separate dependency-independence qualification.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python \
  ../experiments/10_gettenberg_qualification/scripts/audit_cleanup_causality.py \
  CATALOG_CACHE TEXT_CACHE /tmp/NEW_REPORT.json
scripts/format --check --diff -- \
  ../experiments/10_gettenberg_qualification/scripts/audit_cleanup_causality.py
scripts/lint ../experiments/10_gettenberg_qualification/scripts/audit_cleanup_causality.py
```

Local inputs used here:

- CATALOG_CACHE: `/tmp/gettenberg-dispositions-20261020/cache` (existing pinned catalog).
- TEXT_CACHE: `/Users/centaur/Tempspace/Projects/LCATS/cache/texts` (historical decoded
  UTF-8 gzip entries, not original wire bytes).
- Archived anchors: `../gettenberg-narrative-20261018/narrative-cases.json`.
- Archived cleanup contrast: `../gettenberg-qualification-20261018/corpus-after.json.gz`.
- Historical parser: Git 335855c04cd7ba936815d2635969d94fdd278c71. It is already migrated;
  47 common functions versus the original baseline differ only in `gather_story`.
  This does not reconstruct the entire old installed environment.

The runner takes only the two existing cache roots and a fresh output path. It verifies
source/archive/parser/legacy-cleaner identities, and pins relevant current modules to
6a873b61. It writes no story or cache entries, denies sockets during catalog processing,
and removes its temporary historical module. Limits: eight cases, 32MiB compressed and
expanded gzip inputs, 180-second POSIX alarm, 30-second Git timeout. Output must be outside
repository and cache roots, exclusive creation; failures raise without a completed
report. Missing inputs fail instead of downloading them. Approximate diagnostic output
is tens of KiB; this is not a new bulk-corpus measurement.

Smoke checks: successful eight-case replay with all archived hashes; repeat with the
same output path must fail without changing the output hash; nonexistent cache must
fail without output; `--help` must exit 0. No complete package-suite rerun is claimed
for unchanged product sources. Canonical format/lint and LRH validation are recorded
separately; the changed experiment runner receives explicit format/lint coverage.

## Interpretation and limits

35401 and 50103 reproduce severe cleanup-triggered truncations with a fixed parser.
42640 demonstrates an extraction-induced change in the historical chapter predicate
under either cleaner. All eight current bodies receive `needs_review` under either
cleaner. 70645 retains a substantial cleaner difference, preventing blanket equivalence
claims. None of these results chooses the minimum integration patch or approves an
individual story.

The 37 extra English-query IDs are outside this corpus; all fail current only-English
eligibility. Two are in the fixed collection list. This is not a full metadata projection
or resource-selection audit. Original HTTP encoding equivalence cannot be established
from this decoded cache. A future candidate needs explicit stage-level contrasts and
actual gather/installed-package qualification.

The investigators' first temporary probe used a nonexistent `has_chapters` name;
corrected to `chaptered` before producing evidence. A coordinator edit initially used
a repository-root-relative path from the package directory and failed before writing;
corrected without product changes. The durable runner is commented/formatted, exposes
cache paths, replaces optimization-sensitive assertions with explicit checks, bounds
gzip expansion and records additional module/runner hashes. Coordinator independently
replayed its output; the original probe's per-cell evidence remains identical.

Plan: [scope audit](../../../../lcats/project/development/gettenberg-scope-causality-audit.md).
Meeting: [brief](../../../../lcats/project/development/gettenberg-scope-meeting-brief.md).

## Independent review

One P2 diagnostic-provenance issue was corrected: hashing repository files did not
prove Python imported them. The runner now checks all eight relevant imported module
locations and executing bytes against pinned Git files. The independent reviewer
reproduced all eight rows /16 archived hashes, then tested a real PYTHONPATH shadow
package with byte-identical story_body.py. It was rejected before output. No findings
remain open. Current and pre-review rows are identical; recorded outputs were produced
from the correct worktree. This correction does not change product code.

Large JSON replay reports and the LRH log are gzip-compressed verbatim. Decompression
was checked byte-for-byte before removing the uncompressed copies; no measured values
were changed. `manifest.json` records compressed and uncompressed identities.
