# Review a withheld Gutenberg candidate

Use this workflow when gathering reports `needs_review`. It works entirely on saved
candidate files: it requires no catalog setup or network access and never publishes
a story. Keep review artifacts outside your data and corpora directories.

## Find and inspect an exact candidate

Run from `lcats/` in your project environment, or from your normal runtime directory
with an installed LCATS package. The default queue is relative to that directory.

```bash
lcats gather-review list
lcats gather-review list /path/to/candidates --dispositions /path/to/dispositions
```

Omit `--dispositions` until the disposition directory exists. JSON output lists each
candidate generation separately, with its full path, title, findings and disposition
state. `unreviewed` means no matching record; `approve`, `exclude` and `defer` describe
recorded intent. `conflict` means reviewers selected different outcomes or spans.
Multiple generations of an ebook and unmatched dispositions remain visible. Nothing
chooses the newest file or resolves a conflict for you.

Copy the exact candidate path from the inventory or gather outcome into `candidate`:

```bash
candidate='/path/to/candidates/ID-HASH.candidate.json'
lcats gather-review show "$candidate"
lcats gather-review show "$candidate" --start 4000 --end 8000
```

The default preview shows at most 4,000 characters; explicitly requested windows
may contain up to 16,384. Use the returned `next_start` and `candidate_characters`
to page through the text, clipping the final end offset to the total length.
`omitted_before` and `omitted_after` tell you how much text is outside a window.
Offsets count Unicode characters in the exact saved candidate, starting at zero;
end offsets are exclusive. They are **not** UTF-8 byte positions or paragraph
numbers. JSON escapes preserve control characters and Unicode safely in terminal
output; decode the JSON rather than counting its printed escape sequences.

Review the whole narrative and its findings. A preview is not a completeness check.
Consult the original cached source when needed to distinguish narrative from notes,
advertisements, illustrations and genuine divisions. A headline or repeated pattern
alone is not sufficient evidence to discard text or accept a whole collection.

## Record the outcome

After identifying a complete narrative span, set `start` and `end` to its reviewed
character offsets. Supply your actual reviewer attribution and source-grounded
rationale; the command records them but does not authenticate a human signature.

```bash
lcats gather-review record "$candidate" --outcome approve \
  --start "$start" --end "$end" \
  --reviewer "$reviewer" --rationale "$rationale" \
  --directory /path/to/dispositions
```

Record `exclude` when the source does not belong in this collection, or `defer` when
you cannot yet decide. These outcomes take no span and cannot authorize publication:

```bash
lcats gather-review record "$candidate" --outcome exclude \
  --reviewer "$reviewer" --rationale "$rationale" \
  --directory /path/to/dispositions

lcats gather-review record "$candidate" --outcome defer \
  --reviewer "$reviewer" --rationale "$rationale" \
  --directory /path/to/dispositions
```

Each command returns the exact immutable disposition path. Repeating identical
input reuses the same record; changing intent creates another record. Exclude/defer
are audit records: they do not edit the collection definition, delete a candidate,
or suppress subsequent gathering. Preserve old records and inspect conflicts.

## Export explicitly selected approvals

Choose the exact approval records to export. Never use a wildcard over an unreviewed
or conflicted directory. If conflicting records exist, resolve the question through
source review and explain why the selected record is authoritative for this run;
export does not adjudicate conflicts or revoke other records.

```bash
lcats gather-review export /path/to/selected.disposition.json \
  --candidates /path/to/candidates --output /path/to/review-decisions.json
```

You can name several approval files in one command. Each must have its matching
saved candidate, and each Gutenberg ID may occur only once. Export refuses
non-approvals, stale or corrupt evidence, duplicate IDs and unequal existing output.
Choose a new output path for a different selection; existing evidence is preserved.

Then run gathering with the same source/cache configuration used for the candidate:

```bash
lcats gather mass_quantities --offline \
  --review-decisions /path/to/review-decisions.json
```

Gather independently checks current source, metadata, extraction/chapter policy,
assessment and selected-text identities. Changed evidence invalidates approval;
inspect the new candidate and review it again. Definite collection exclusions still
apply. Historical decoded-cache reviews cannot authorize live original-byte inputs.
`--yes` only approves setup; it is never editorial approval.

Gather preserves existing story files. Use a separate disposable output root for
requalification; review decisions do not replace already published files. The
inventory also does not certify publication: inspect the new gather outcome/log.

See the [reference](../reference/gettenberg-review.md) for limits and API contracts,
and the [architecture explanation](../explanation/gettenberg-architecture.md) for
why preservation, review intent and publication are separate.
