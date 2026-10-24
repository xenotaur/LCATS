# Gettenberg post-adoption backlog

Status: **open follow-up; A–D accepted for bounded replacement delivery on 2026-10-24**.
Acceptance is conditional on retaining these matters in a durable backlog; this
register fulfills that condition. It does not claim integration, main delivery,
editorial approval or that any follow-up has been implemented.

Triage owner: **xenotaur**, consistent with WI-GETTENBERG-0010. Implementation owners
and grants remain unassigned. Coordinate gather changes with Kenny when his work is
available; no assignment or access to his code is assumed. The entries below are
backlog records, not executable instructions or authorized implementation work items.

## Evidence and maintenance

- [Human decision sheet](gettenberg-delivery-decision.md#human-acceptance--2026-10-24)
  records the approval and delivery scope.
- [Acceptance record](gettenberg-adoption-acceptance.json) identifies the approved
  groups and pins the historical proposed ledger by SHA256. Each proposed row links
  exact decoded input, metadata and old/new body hashes. Historical false acceptance
  flags describe the earlier measurement time and are deliberately not overwritten.
- [Causal evidence](../../../experiments/10_gettenberg_qualification/results/gettenberg-causal-yield-20261023/README.md)
  includes `causal-ledger.json.gz`: join each ID below to its row for markers, traces,
  excerpts, body changes and input identities.
- [Corrected batch yield](../../../experiments/10_gettenberg_qualification/results/gettenberg-refusal-continuation-20261023/README.md)
  establishes 1,646 publications/reuses, 13 refusals and zero unattempted in the frozen
  cohort. [Independent review and installed-package evidence](../../../experiments/10_gettenberg_qualification/results/gettenberg-delivery-review-20261024/README.md)
  support the candidate at reviewed product `823f33c23836aff220fab80046ab84b80584c063`.

This is the single active detailed register for these follow-ups; the
[project backlog](../design/backlog.md) is its discovery index. Stable references
GPA-A through GPA-D below are local backlog keys, not minted LRH work-item IDs.
Before implementation, scope and promote an entry into an LRH work item with explicit
acceptance and budget. Replace its active instructions here with a link/status to
that item, retaining the historical IDs/evidence. Close an entry only with linked
validation or an explicit documented decision to retain the limitation. Delivery
acceptance alone never closes a backlog entry. Do not merge preserved PR #524 or
redefine story extraction as a side effect of adopting this library.

## GPA-A — Unsupported boundary formats: 13 explicit refusals

**Status:** open; accepted delivery exclusions. **Priority:** P2 (visible per-item
failure), using the project backlog's priority convention.

The current boundary recognizer cannot safely qualify these inputs under its rules.
This is not a finding that the books are corrupt or unusable. Preserve sources,
emit no story for a refused input, log `story_cleanup_refused`, continue later inputs
and return incomplete CLI status 2. Repeating the run reuses successful output but
does not fix these exclusions. There are six wrapped markers, three competing
interior *END* candidates, three unsupported initial banners and one identifier mismatch.

| Gutenberg ID | Catalog title | Observed refusal mechanism |
|---|---|---|
| 3699 | Miss Sarah Jack of Spanish Town, Jamaica | Book boundary marker wraps across physical lines |
| 3724 | The House of Heine Brothers, in Munich | Book boundary marker wraps across physical lines |
| 20257 | A Political Romance | Opening and closing marker identifiers disagree |
| 35759 | Security Risk | Interior *END* text competes with the boundary marker |
| 35770 | The Hero | Interior *END* text competes with the boundary marker |
| 35879 | The Rotifers | Interior *END* text competes with the boundary marker |
| 38287 | We're Civilized! | First nonblank line is not a supported banner |
| 38302 | The Lonely Ones | First nonblank line is not a supported banner |
| 53402 | Brotherly House | First nonblank line is not a supported banner |
| 70349 | When the squadron dropped anchor | Book boundary marker wraps across physical lines |
| 70923 | An experiment in gyro-hats | Book boundary marker wraps across physical lines |
| 71085 | The fire of Asshurbanipal | Book boundary marker wraps across physical lines |
| 72379 | A voice from the inner world | Book boundary marker wraps across physical lines |

**First step:** select one format family, inspect its pinned source rows and propose
one narrow recognition rule; do not bypass cleanup or broadly catch exceptions.
Treat identifier mismatch separately from line-wrapping support. Test authored
near-misses and narrative marker lookalikes as well as the real-source anchors.

**Completion evidence:** explicit supported/refused outcomes for every affected ID;
unchanged original identities; demonstrated narrative preservation and publication
ownership; full frozen-cohort cleanup/body replay and actual batch/reuse/refusal
counts. No acceptance from a higher output count alone. Other operational errors
must remain distinct and fatal where currently specified.

## GPA-B — Retained terminal notices: 55 bodies

**Status:** open; accepted known delivery limitation. **Priority:** P3 until a narrow
body-contract/removal decision is scoped.

Each body retains the complete historical body plus source-backed terminal notice
text, without measured eligibility changes. The extra text is non-story material
and can affect later analysis; acceptance is not editorial cleanliness or permission
to remove uncertain endings. The exact accepted input/body set is:

2345, 2347, 3183, 8525, 9204, 9210, 9213, 9214, 9215, 9218, 12830, 17083, 22218, 22479, 22810, 22841, 22844, 23003, 23146, 23165, 23168, 23198, 23254, 23326, 23329, 23548, 23549, 23550, 23551, 23553, 23555, 23556, 23557, 23701, 23703, 24375, 25057, 30259, 30267, 36867, 44319, 47492, 51006, 51622, 51650, 51668, 51698, 53035, 56250, 59289, 61498, 61766, 61870, 62443, 63720.

**First step:** group the pinned notice forms and decide whether a narrowly
corroborated removal or continued retention is preferable. Coordinate any downstream
extraction change with GPA-C; never restore the old footer boundary wholesale.

**Completion evidence:** source-grounded proposed cuts, before/after body identities,
negative/adversarial cases and full-cohort replay. In particular, preserve GPA-C's
23552 final paragraph when changing what follows it. A decision to retain some forms
must name those inputs and document the continued limitation rather than reporting
all notices removed.

## GPA-C — Twelve specific body effects and gather reconciliation

**Status:** open follow-up; the twelve existing candidate outcomes are accepted for
bounded delivery. **Priority:** P3 for body/paratext policy decisions; the independently
reproduced final-paragraph deletion in the unchanged parser merits P1 follow-up under
the existing backlog's silent-loss convention. That is not a new review finding that
the qualified candidate loses 23552's ending: the candidate preserves it.

| IDs | Accepted observation | Follow-up / regression requirement |
|---|---|---|
| 32655 | One leading newline; full old body retained. | Decide whether whitespace normalization is useful; do not treat cosmetic equality as a narrative requirement. |
| 70645 (*Sam Bass*) | A 16,465-character prefix containing magazine blurb and story opening is restored; full old body retained. | Preserve recovered narrative. Decide treatment of the blurb separately; do not discard the entire prefix or invent a legacy header cause (the recorded legacy cleanup trace is empty). |
| 22967, 27921, 29181, 29206, 30010, 30035 | Transcriber notes plus terminal notices; full old bodies retained. | Define which source notes belong in a body or separate provenance before changing extraction. |
| 23161 | Author signature plus terminal notice; full old body retained. | Decide signature treatment explicitly; preserve source attribution. |
| 23252 | Illustration caption plus terminal notice; full old body retained. | Decide caption treatment explicitly; distinguish caption text from narrative. |
| 23552 (*The Phantom of Bogue Holauba*) | Final 387-character narrative paragraph restored, plus notice. The unchanged parser can delete that paragraph when terminal, independently of either cleaner. | Keep the restored ending. Isolate/fix the parser heuristic in separate gather work, with a regression that survives later notice removal and cases where a title genuinely marks non-narrative material. |
| 42640 (*The Last Christmas Tree*) | Removes 166 characters of publication-note/title text; retains narrative; adds 230 characters of colophon/notice. | Decide frontmatter/colophon placement; preserve narrative and source provenance. Use exact line hunks, not a misleading large contiguous diff. |

These are accepted outcomes, **not twelve instructions to restore historical output**.
Some changes recover real story content. The six note cases, signature and caption
are eight paratext cases; adding the newline, two restorations and frontmatter/tail
variation accounts for twelve.

**First step:** preserve the 23552 isolated reproducer and compare it with Kenny's
work when available; agree a small separate gather work item before implementation.
For the remaining cases, choose a body/paratext contract and retain regression
anchors even where no behavior change is desired. Preserve the broader work at
`b1254805` / PR #524 for reconciliation, without automatically adopting its design.

**Completion evidence:** independently reproduced mechanism, source-grounded expected
body, tests protecting restored openings/endings, explicit paratext decisions and
measured downstream eligibility/ownership/yield. Report separate outcomes for each
listed ID; do not collapse delivery acceptance into editorial approval.

## GPA-D — Qualification coverage and historical provenance boundary

**Status:** open coverage/provenance follow-up; current evidence accepted as sufficient
for bounded delivery. **Priority:** P3 (scope, acquisition cost and evidence design
must be decided before running an expanded experiment).

- Actual gather comparison/yield covers the frozen **1,659-input** intersection,
  not all **5,492 configured IDs**. The other 3,833 are outside this measurement;
  they are not proven failures, refusals or successes.
- Separate metadata evidence covers **78,937 records** with public-field/raw-RDF
  round trips. The 37 additional English-query records reflect multivalued-language
  handling; this does not establish their story publication yield.
- Historical cached inputs are decoded/re-encoded UTF-8. They do not recover original
  response bytes, encoding decisions or request history. Authored original-byte
  acquisition and installed-package tests provide separate evidence, not a retroactive
  proof of historical wire fidelity.
- Resource timings are dated measurements in the recorded environment, not a general
  speedup guarantee or performance qualification of every supported dependency version.

**First step:** inventory existing verified receipts and the unmeasured configured
selection without downloading. Propose an explicit bounded coverage/acquisition plan
if broader yield claims are needed: network authority, pacing/cache reuse, bytes/time
budget, disposable outputs and stage-specific expected results. Capture original
bytes and receipts prospectively; do not relabel decoded historical text as original
transport or promise to reconstruct missing evidence.

**Completion evidence:** exact selection/input/source identities, published/reused/
refused/skipped/fatal/unattempted counts and separate metadata/transport/cleanup/
extraction effects. Update the qualification boundary only for actual observations.
The irrecoverable historical provenance limit can remain a permanent documented
boundary; close that subtopic by explicit acknowledgement, not invented equivalence.
No bulk network acquisition, canonical corpus promotion or package publication is
authorized by this backlog or by A–D acceptance.
