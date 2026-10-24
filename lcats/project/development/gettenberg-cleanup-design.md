# Conservative cleanup contract — WI-GETTENBERG-0006

Run gettenberg-20261016-cleanup; integration base3d55a487. This contract is recorded
before implementation. Acceptance requires independent review and qualification;
this design alone is not evidence that implementation passed.

## Boundary and API decisions

`cleanup.strip_boilerplate(text, max_characters=32*1024*1024)` accepts decoded
Python str only. A structured input error rejects bytes/other types and oversized
input before scanning; callers may explicitly change the positive character bound.
Byte decoding belongs to resources.decode_text. No I/O, network, normalization,
HTML parsing, corpus writing, global cache or gutenbergpy import is permitted.

Immutable CleanupResult retains the exact original str and half-open character
content_start/content_end offsets, detected marker records, diagnostics and a
separate versioned cleanup policy. Its text property slices the original, and
changed reports whether boundaries moved. Markers include kind, one-based line,
full-line character span (including line ending), exact identifier and style.
Results/diagnostics are dataclasses suitable for dataclasses.asdict/JSON export.
No duplicate stored full body; nothing silently normalizes or drops characters.

Recognize complete standalone triple-asterisk START/END OF THE or THIS PROJECT
GUTENBERG EBOOK lines with a nonempty title or numeric identifier. Compare labels
case-insensitively after horizontal whitespace normalization; preserve original
spelling/offsets. LF, CRLF and CR are physical line endings; Unicode line-like
characters are ordinary content. Permit horizontal indentation and initial BOM
without stripping body text. Require exactly one start and one end, matching
identifiers and article styles, correct order and non-whitespace retained content.
Malformed marker-like lines, repeated/nested/concatenated pairs, missing markers,
mismatched identifiers/styles or empty bodies preserve the entire original.

Context guards: a nonblank removed prefix must start with a recognized Gutenberg
eBook banner; a nonblank removed suffix must contain the standalone full Gutenberg
license heading. Marker-only wrappers with whitespace outside are accepted. This
refuses ordinary narrative surrounding a quoted marker pair. Syntax/context cannot
prove document intent: spoofed complete envelopes remain a documented limitation.
Never treat plain 'The End', production credits, copyright text, or arbitrary
'End of Project Gutenberg' substrings as independent boundaries.

The historical standalone `End of Project Gutenberg's <title>, by <author>` notice
may move the end boundary earlier only when it is the immediately preceding
nonblank line before a qualified starred end marker and its title agrees. Record
that extra boundary explicitly; otherwise retain it. Credits/transcriber notes
inside the chosen body remain gather-time responsibility.

Scanning is linear over physical lines and retains bounded candidate metadata.
Stop conservatively on excess candidates; do not pick the first/last convenient
pair. Unsupported older ETEXT/small-print/multilingual/wrapped markers are not
silently guessed. A no-op result is observable, not a claim that input was clean.

## Evidence, provenance and retained material

Primary evidence inspected2026-10-16:

- [Current Gutenberg publication60600](https://www.gutenberg.org/cache/epub/60600/pg60600-images.html), updated2025: complete THE/EBOOK start and end, banner and full-license heading.
- [Historical publication32458](https://gutenberg.org/files/32458/32458-h/32458-h.htm), released2010: THIS/EBOOK start/end, title-matching plain end notice, and full-license heading.
- Existing LCATS analysis boundary fixtures corroborate the modern delimiter form;
  headers_test currently tests delegation, not safe boundary behavior.

These observations establish marker syntax, not comprehensive historical coverage.
Tests will use independently authored LCATS narratives and envelopes, with these
URLs explaining observed variants. No upstream stripping algorithm/marker list,
Gutenberg story prose, license text or complete book is copied into the repository.
Short conventional marker syntax is factual evidence; authored fixtures carry
LCATS's repository license. Research used web source inspection, no raw catalog,
mirror acquisition, corpus cache or bulk ebook download.

## Scope and validation

Legacy headers.py and gatherer callers remain unchanged for WI0008 migration.
Test actual result slices, original-object preservation, precise CR/LF/Unicode
positions, modern/historical forms, near markers inside narrative, paired quotes,
repeats, malformed boundaries, absence/one-sided input, short/empty content,
resource bounds, no-I/O/import behavior and JSON serialization. Execute fenced
how-to examples, then canonical format/lint/scripts/test and LRH/readiness checks.
Freeze exact source hashes before cold review; first hosted rounds and final-head
CI remain mandatory for integration. Native statuses stay nonterminal until main.
