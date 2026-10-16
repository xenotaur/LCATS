# Conservative Gutenberg boilerplate cleanup

Import with `from lcats.gettenberg import cleanup`.
`cleanup.strip_boilerplate(text, *, max_characters=32*1024*1024)` is a pure
operation over decoded **plain text**. It neither loads a catalog nor accesses
files/network, and does not import `gutenbergpy`. Decode bytes with
`resources.decode_text`; HTML markup requires a separate extraction step.
The legacy `headers.strip_headers` wrapper and gatherers have not migrated yet.

## Result and source preservation

`CleanupResult` is an immutable dataclass:

| Field/property | Meaning |
|---|---|
| `original` | The exact input string, retained without modification. |
| `content_start`, `content_end` | Half-open offsets into `original`, in Python Unicode characters, not bytes or grapheme clusters. |
| `text` | Property computing `original[content_start:content_end]`. |
| `changed` | Whether any prefix or suffix was removed. |
| `markers` | Immutable tuple of detected `CleanupMarker` records in source order; bounded as described below. |
| `diagnostics` | Immutable tuple of `CleanupDiagnostic(code, message, line=None)`. |
| `policy_version` | `gutenberg-boundaries-v1`, independent of decoding/transport versions. |

All preservation outcomes select `[0:len(original)]`. `changed=False` does not
certify that the input is clean: inspect diagnostics. Output is an exact slice;
no blank lines, indentation, Unicode composition, punctuation or line endings
inside it are normalized. Retain the original artifact/decoding provenance
separately if you need to trace text back to acquired bytes.

`CleanupMarker(kind, start, end, line, identifier=None, style=None)` describes a
whole physical line, including its ending. Offsets are half-open and `line` is
one-based. Kinds are `start`, `end`, `end_notice`, and `unrecognized`. Identifier
retains the title/number spelling with surrounding spaces/tabs removed; style
is `the` or `this`. Unrecognized candidates have neither identifier nor style.
You can inspect the original marker with `original[marker.start:marker.end]`.

`dataclasses.asdict(result)` produces JSON-compatible original/offset/evidence
records. Computed properties `text` and `changed` are not dataclass fields and
are not included. Exporting duplicates the original in the serialized output;
store only offsets and provenance references when that better fits your workflow.

## Acceptance rules

A supported envelope has one complete standalone starred start and one complete
standalone starred end. The conventional form is:

```text
*** START OF THE PROJECT GUTENBERG EBOOK A LANTERN ***
Body text, unchanged.
*** END OF THE PROJECT GUTENBERG EBOOK A LANTERN ***
```

Both `THE` and historical `THIS` are supported, but the pair must agree. A nonempty
title or numeric identifier is required. Identifiers compare by casefolding and
collapsing spaces/tabs; other punctuation and Unicode normalization must agree.
Keywords are ASCII case-insensitive. Horizontal indentation and spacing are
accepted, as is an initial BOM; none of this changes the body. Only LF, CRLF and
CR form physical lines. Unicode line-like characters are ordinary text.

Candidate detection is deliberately broader than accepted syntax: a physical
line beginning (after whitespace) with one or more stars followed by `START` or
`END` is a candidate, even if its Gutenberg name is incomplete or absent. Unsupported
Unicode spacing, single-star delimiters and wrapped fragments therefore cause a
safe refusal instead of hiding a competing envelope. A narrative containing such
a standalone starred heading can also cause a refusal; no content is lost.
The exact historical `*** START: FULL LICENSE ***` line is license-section
metadata, not a book boundary. It is exempt from candidate detection; this does
not waive the matching book pair or the full-license heading requirement.

All of these conditions must hold before any removal:

1. There is exactly one recognized start and one recognized end, in order, with
   matching style and identifier. No malformed marker-like candidates are present.
2. Any nonblank prefix starts with a Gutenberg eBook banner, such as
   `The Project Gutenberg eBook of …` or `Project Gutenberg's …`.
3. Any nonblank suffix contains a standalone full Gutenberg license heading:
   `THE FULL PROJECT GUTENBERG LICENSE`, with optional `™` or `-tm` after Gutenberg.
4. The retained content has at least one non-whitespace character.

Whitespace-only outer regions need no banner/license. Repeated, nested or
concatenated envelopes are ambiguous; the function never chooses the first or
last convenient pair. Ordinary narrative around a quoted marker pair fails the
context guards. A deliberately reproduced complete Gutenberg envelope can still
look genuine: these are syntax/context checks, not proof of origin or intent.

The historical `End of Project Gutenberg's <title>, by <author>` notice can be
removed only when it is the immediately preceding nonblank line before the
qualified starred end, its title matches that marker, and its author is nonempty.
That line becomes an explicit `end_notice` boundary; the remaining body must still
be nonempty. A standalone, differently titled, quoted or nonadjacent notice is
retained. Production credits and transcriber notes inside the body remain intact.

The default input bound is **33,554,432 characters**, adjustable with a positive
integer `max_characters`. Scanning is linear in input size with bounded candidate
records. More than 16 marker-like lines stops the scan and preserves all text;
`markers` then contains only the first 16 candidates and `candidate_limit` names
the next line. Input and per-line temporary strings still require memory; result
properties and serialization can allocate additional copies.

## Diagnostics and errors

| Code | Result |
|---|---|
| `envelope_removed` | Qualified prefix/suffix removed. |
| `end_notice_removed` | Corroborated historical end notice also removed. |
| `no_markers` | No qualified candidates; original retained. |
| `unrecognized_marker` | Unsupported/malformed marker-like line; original retained. |
| `candidate_limit` | Candidate evidence exceeded the bound; original retained. |
| `multiple_markers` | Repeated/nested/concatenated markers; original retained. |
| `incomplete_pair` | Missing start or end; original retained. |
| `reversed_pair` | End precedes start; original retained. |
| `mismatched_pair` | Identifiers or styles disagree; original retained. |
| `unverified_header` | Prefix lacks the expected banner; original retained. |
| `unverified_footer` | Suffix lacks the expected full-license heading; original retained. |
| `empty_content` | Removal would leave whitespace only or nothing; original retained. |

`CleanupInputError` subclasses `GettenbergError` and `ValueError`, with stable
`.code`: `invalid_text` for non-str input, `invalid_limit` for nonpositive/noninteger
limits (including bool), or `input_too_large` for exceeded bounds. It returns no
partial/truncated result and does not modify the caller's input.

## Coverage and provenance

Rules are independently authored from observed conventions in Gutenberg's
[current publication60600](https://www.gutenberg.org/cache/epub/60600/pg60600-images.html)
and [historical publication32458](https://gutenberg.org/files/32458/32458-h/32458-h.htm).
Fixtures contain LCATS-authored stories and envelopes, with source URLs documenting
observed syntax; no upstream cleanup implementation or marker list is copied.

This policy deliberately does not guess older ETEXT/small-print, wrapped,
multilingual or other unqualified conventions. Plain `THE END`, arbitrary
copyright language, or an `End of Project Gutenberg` substring is not a boundary.
A safe refusal is preferable to silently losing narrative; broaden the policy
only with new evidence and regression fixtures. See the
[cleanup workflow](../how-to/gettenberg-cleanup.md) for use and inspection.
