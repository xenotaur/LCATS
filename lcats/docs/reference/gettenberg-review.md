# Saved-candidate review reference

`lcats gather-review` is an offline artifact workflow. It reads no catalog, acquires
no sources and publishes no stories. All successful subcommands return JSON and exit
0, including inventory results with conflicts. Input/I/O errors exit 2. This differs
from `lcats gather`, whose exit 3 means a completed batch needs attention.

| Command | Result |
|---|---|
| `list [CANDIDATES] [--dispositions DIRECTORY]` | Candidate generations, finding counts, disposition states, unmatched identities and scan bytes |
| `show CANDIDATE [--start N] [--end N]` | Exact Unicode text window, metadata, full record identity, overlapping findings and omitted-text counts |
| `record CANDIDATE --outcome approve\|exclude\|defer --reviewer TEXT --rationale TEXT [--start N --end N | --omissions FILE] [--directory DIRECTORY]` | Immutable disposition path and `published:false` |
| `export DISPOSITION... --candidates DIRECTORY --output FILE` | Explicitly selected approvals in gather's existing `--review-decisions` JSON format; `published:false` |

Default relative paths are `logs/gather/review/mass_quantities` for candidates and
`logs/gather/dispositions/mass_quantities` for recorded dispositions. `list` does not
load dispositions unless requested. Missing requested directories fail; existing
empty directories yield an empty inventory. Directories are scanned non-recursively.

## Library API

Import `from lcats.gatherers import candidate_review`.

| Function | Contract |
|---|---|
| `load_candidate(path)` | Validate current-format saved report, body/assessment/source-context hashes and content-addressed filename |
| `preview(path, *, start=0, end=None)` | JSON-compatible text window; default end is at most start + 4000 |
| `record_disposition(candidate, *, outcome, reviewer, rationale, start=None, end=None, omissions=None, directory=DEFAULT_DISPOSITIONS)` | Return immutable path; approval requires a nonempty span or evidenced omissions |
| `load_disposition(path)` | Validate disposition schema, attribution, approval fields and content-addressed filename; matching candidate is checked by inventory/export |
| `inventory(candidates, *, dispositions=None)` | Summarize each exact generation; never choose a latest record or resolve a conflict |
| `export_approvals(dispositions, *, candidates, output)` | Validate exact candidates and selected text, sort exported approvals by ID, return output path |

Input and consistency failures raise `ValueError`; filesystem failures can raise
`OSError`. Hashes detect inconsistent artifacts, not maliciously recomputed records
or authenticated authorship. Loading an artifact does not certify source freshness
or literary quality. Gathering independently revalidates current derivation context.

## Disposition schema and state

A disposition filename is `<id>-<record_sha256>.disposition.json`. Its JSON object
contains exactly these fields:

| Field | Meaning |
|---|---|
| `schema_version` | Integer `1` |
| `kind` | `gettenberg_candidate_disposition` |
| `gutenberg_id` | Positive integer ID |
| `candidate_record_sha256` | Identity of the full saved candidate record |
| `outcome` | `approve`, `exclude` or `defer` |
| `reviewer`, `rationale` | Nonblank attribution and source-grounded reason |
| `approval` | A [ReviewDecision](gettenberg-gather.md#publication-readiness-and-reviewed-decisions) object for approval; otherwise `null` |

JSON object keys must be unique; non-finite numbers are rejected. Approved spans are
nonempty, within the candidate, and use exact Unicode character offsets. Attribution
must match between disposition and nested approval. Both filenames and internal
identities are validated. Equal records reuse existing files; unequal outputs are
never overwritten. Atomic creation requires filesystem hard-link support, as in
story publication; directory entries are not promised power-loss durability.

Inventory state is `unreviewed` with no matching dispositions, otherwise the sole
recorded outcome, or `conflict` when outcomes, complete retained selections or separately preserved blurb ranges differ. Identical content intent
from different reviewers or v1/v2 versions is not a conflict; their individual records remain listed.
Records for missing candidate generations appear in `unmatched_disposition_candidates`.
These are reviewer-intent states, not current collection membership or publication.

Export consumes only named approvals; it does not scan other disposition records to
infer consensus. Even if inventory reports a conflict, explicit selection remains
possible and the caller owns that choice. A single export cannot contain two records
for one ID, including identical repeated records or different candidate generations.
Exclusion and deferral never modify collection definitions or existing outputs.

## Resource and filesystem bounds

| Bound | Limit |
|---|---|
| Candidate JSON | 64 MiB per file |
| Disposition JSON | 64 KiB per file |
| Directory inventory | 10,000 matching files per directory |
| Export | 1–10,000 named approval records, at most 8 MiB serialized output |
| Aggregate scan | 1 GiB actual JSON bytes across candidates and dispositions |
| Preview window | Default 4,000; maximum 16,384 Unicode characters |
| Attribution | Reviewer 256 characters; rationale 4,000 characters |

All reads are individually bounded; aggregate accounting is checked after each
bounded read, so the failing read can exceed the aggregate allowance by at most one
file bound. Candidate bodies are validated one at a time; inventory retains summary
rows, not full texts. Preview still reads its full bounded candidate to validate
identity. Its metadata/findings are additional to the text-window limit.

Input files must be regular, non-symlink files. Output parent paths are resolved and
must be outside configured data/corpora roots. Symlink output files and aliases into
protected roots fail. These are local misuse guards, not a sandbox against another
process concurrently replacing directories. Configure actual collection roots before
using custom locations. Preserve original sources and historical records.


## Opt-in boundary rule proposals

Import `from lcats.gatherers import review_rules` and call
`review_rules.evaluate_boundary_notice(candidate_path)`. This reads a validated
saved candidate and returns evidence; it does not record approval or change gather.
`publication_notice(text)` tests only the complete notice grammar.

`delimited-publication-notice-v1` recognizes a complete bracketed transcriber
publication/copyright notice in the first or last paragraph. The publication name
must be in the explicit finite list in the module, followed by one named month or
season and a 1900–1999 year, then the exact research/copyright sentence. Case,
physical whitespace and the supported apostrophe variants affect recognition only.
The complete paragraph is bounded to 1,000 characters. Unknown publications, date
forms, additional prose, incomplete brackets and interior notes do not match.
No surrounding title, byline, blurb or caption is discarded. At most one matching
notice per boundary is considered; the selected text is a contiguous exact substring.

The JSON result records the rule version, ebook and candidate/source/assessment
identities, applicability, selected span/hash, exact removed text/spans/hashes,
selected structural/readiness assessments and blockers. `approval_eligible` means
that this narrow edit leaves no readiness findings or recognized retained editorial
labels; it is not a literary-quality certificate or historical reconciliation.
The original assessment is recomputed and must match the saved evidence.

The qualification experiment additionally requires an unreviewed input and exact
historical-baseline equality after the separately recorded existing normalization
before it may record this rule's decision. It keeps unexplained differences,
existing decisions and conflicts out of the automatic recording set. See the
[batch procedure](../how-to/gettenberg-review.md#qualify-a-batch-offline).


## Ordered retained spans and editorial metadata

`readiness.OrderedReviewDecision.for_report(report, *, omissions, reviewer, rationale)`
constructs an explicit v2 approval. `omissions` is a list of 1–256 objects, each with
exactly `start`, `end`, `kind`, `reason` and `evidence`. Offsets are nonnegative
Unicode character integers in the unchanged candidate, end-exclusive; booleans and
floats are rejected. The supported kinds are `publication_notice` and
`publisher_blurb`. Reason and evidence must each contain 1–4,000 nonblank characters.
This is attributed review evidence, not independently authenticated classification.

The constructor derives each omitted text hash and the ordered retained complement.
It rejects overlaps, reordering, out-of-bounds ranges and an empty selection. Adjacent
omissions are permitted; unclassified characters are retained. Concatenation inserts
nothing: choose source paragraph boundaries that preserve appropriate existing
separators. Existing collection normalization is applied separately afterward.

The serialized v2 decision contains `schema_version: 2`, `gutenberg_id`,
`source_identity_sha256`, `candidate_sha256`, `assessment_sha256`,
`candidate_characters`, `selected_spans`, `omitted_spans`, `selected_sha256`,
`reviewer` and `rationale`. Each omitted object adds `sha256` to its five input fields.
Retained spans must be exactly the complement of the ordered omissions; loaders
reject incomplete partitions. There are at most 257 retained spans. Source/context,
full candidate, every omission and reconstructed output are checked before use.
The 64 KiB disposition and 8 MiB export limits still apply even below the span limit.

`readiness.decision_from_dict(value)` and `load_decisions(path)` accept v1 and v2.
V1 evidence keeps its original schema and bytes; it is never silently restamped or
rewritten. A disposition's outer schema remains v1 with a versioned nested approval.
`candidate_review.load_omissions(path)` reads the CLI specification as bounded,
strict JSON (64 KiB, regular non-symlink file); decision construction validates fields.

A v2 inspected report has `selected_span: null`, `selected_spans` and `editorial`.
Published `metadata.editorial` contains confirmed blurbs only, with exact text,
source-relative start/end, kind, reason/evidence, text hash, candidate/source hashes,
reviewer and explicit offset basis. These offsets refer to the original candidate,
not the concatenated or normalized published body. Publication notices remain in
review provenance; raw inputs and saved candidates remain intact. A blurb changes
placement only after explicit review; no classifier infers its role from position.
V1 and v2 decisions may both resolve reviewed uncertainty, but neither overrides a
collection exclusion. Automatic rule proposals do not supply that judgment.

## Opt-in ordered notice proposals

`review_rules.evaluate_publication_notices(candidate_path)` applies
`ordered-publication-notice-v1` to complete matching paragraphs anywhere in the
candidate, using exactly the boundary rule's finite notice grammar. Each omission
contains the notice and following separator or final whitespace; the preceding
separator remains. At the leading boundary, exterior leading whitespace belongs
to that notice. Nonmatching paragraphs are never omitted. At most 256 notices may
be proposed; an all-omitted candidate or larger set remains unresolved.

The result binds source/candidate/assessment identities and records `omissions`,
`selected_spans`, output hash, exact removed text/hashes and recomputed assessments.
`transformation_qualified` means the exact transformation satisfies this rule;
`selected_readiness_eligible` means no remaining mechanical readiness findings or
recognized retained editorial labels. `publication_approved` is always false.
Missing matches or unusable selections have `selected_spans: null` and blockers.
Apparent blurbs, credits and unrelated differences remain for separate review.
The function writes nothing. The experiment's explicit recording mode additionally
requires no prior intent and complete historical-baseline reconciliation, as above.


## Historical difference evidence

`lcats.gatherers.historical_review.explain_typography(selected, historical)`
returns `source-preserved-typography-v1` evidence without editing either input or
authorizing publication. Inputs are strings of at most4,000,000 Unicode characters.
The caller must bind the selected text to a validated source decision and verify
the historical baseline hash. The experiment also requires that normalization
leaves the selected text unchanged before using this explanation.

The finite comparison projection removes only complete interior paragraphs whose
text is exactly seven spaces followed by five asterisks separated by seven spaces.
It also accounts for exterior ASCII spaces, tabs and LF characters on each side.
Other whitespace, interior indentation, prose, punctuation and ordering remain
material. Exact whole projected equality explains the historical difference; the
actual selected output retains its separators and typography. This intentionally
does not reproduce the old parser's broader substring-based paragraph deletion.

Evidence includes input hashes, exact comparison-only ranges/text/hashes, projection
hashes, `complete`, and a diagnostic `residual_shape`. Shapes such as
`additional_boundary_text` are structural relationships, not blurb classifications.
`publication_approved` is always false. Empty/whitespace-only inputs never qualify.
An exact equality result is separate from a typography explanation.

Historical preservation cannot detect an unwanted blurb already present in the old
corpus. The [qualification experiment](../../../experiments/10_gettenberg_qualification/README.md#source-grounded-historical-reconciliation)
therefore requires an explicit source-bound reviewed cohort before recording new
non-equal historical approvals, in addition to readiness and cumulative exceptions.


## Opt-in terminal-note composition

`review_rules.evaluate_publication_notices(candidate_path, include_terminal=True)`
returns `ordered-and-terminal-publication-notices-v1`. It combines the existing
ordered bracketed notices with `terminal-unbracketed-publication-notice-v1`, using
original candidate Unicode coordinates for every omission. The default
`include_terminal=False` preserves the previous grammar and result packet.

The terminal helper `propose_trailing_publication_notice(body)` recognizes one
complete final unbracketed transcriber note of at most 1,000 characters, following
a blank line and nonempty retained text. Recognition permits finite magazine names,
one month/season and a 1900–1999 year, the exact copyright-research sentence and an
optional exact spelling/typography correction sentence. It permits matching magazine
underscores and case/whitespace variations; it never rewrites retained text. The
helper returns exact original offsets/text/hashes, or `None`; oversized/non-string
inputs raise `ValueError`. Recognition alone has no publication authority.

The combined proposal preserves every other character and the separators preceding
the terminal note. Overlapping independent omissions fail closed rather than being
trimmed to fit. The existing 256-omission bound, strict partition validation,
reassessment and retained-editorial-label checks apply. `terminal_notice` records
the exact additional proof or `null`; `publication_approved` remains false. A
combined proposal can contain only bracketed notices if the terminal grammar does
not match; existing safeguards and cohort requirements still apply.

The archival batch runner selects this mode with `--rule terminal`. Recording
requires an exact source-bound `--cohort-review` packet for **every** new proposal,
including exact-baseline matches and `--historical-acceptance baseline`. Historical
equality can preserve an unwanted old blurb. Missing/stale/duplicate review evidence,
known defer/exclude/conflict intent, remaining findings and unexplained differences
prevent recording. Default extraction and other rule modes are unchanged.
