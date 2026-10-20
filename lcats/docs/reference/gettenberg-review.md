# Saved-candidate review reference

`lcats gather-review` is an offline artifact workflow. It reads no catalog, acquires
no sources and publishes no stories. All successful subcommands return JSON and exit
0, including inventory results with conflicts. Input/I/O errors exit 2. This differs
from `lcats gather`, whose exit 3 means a completed batch needs attention.

| Command | Result |
|---|---|
| `list [CANDIDATES] [--dispositions DIRECTORY]` | Candidate generations, finding counts, disposition states, unmatched identities and scan bytes |
| `show CANDIDATE [--start N] [--end N]` | Exact Unicode text window, metadata, full record identity, overlapping findings and omitted-text counts |
| `record CANDIDATE --outcome approve\|exclude\|defer --reviewer TEXT --rationale TEXT [--start N --end N] [--directory DIRECTORY]` | Immutable disposition path and `published:false` |
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
| `record_disposition(candidate, *, outcome, reviewer, rationale, start=None, end=None, directory=DEFAULT_DISPOSITIONS)` | Return immutable path; approval requires an explicit nonempty span |
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
recorded outcome, or `conflict` when outcomes/spans differ. Identical content intent
from different reviewers is not a conflict; their individual records remain listed.
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
