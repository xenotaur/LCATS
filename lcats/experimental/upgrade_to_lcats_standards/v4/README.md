# LCATS conservative terminal cleanup — four additional cases

Install into the existing LCATS repository, preserving these paths:

- `lcats/gatherers/mass_quantities/parser.py` — replacement parser based on the preceding v4 terminal-cleanup patch.
- `tests/mass_quantities/terminal_four_cases_test.py` — seven new behavioral regression tests.

## Scope

- Gutenberg 72379: if numbered terminal footnotes follow a standalone ending marker, remove them from the narrative and preserve their text through the existing `footnotes.json` publication path. No footnotes sidecar is written for reused, rejected, or unsuccessful stories.
- Gutenberg 25404: remove publisher advertising following a standalone ending marker and a specifically recognized advertising heading.
- Gutenberg 44319: remove a terminal `PRESS OF ...` imprint without removing the preceding author dateline.
- Gutenberg 17083: recognize a short terminal imprint with a city prefix such as `London:--Printed by ...`.

Source-level terminal cleanup remains in place. An additional narrow cleanup pass on the *already-cleaned* text catches terminal structures that were obscured by Gutenberg line wrapping. It removes only recognized supplemental sections and printer imprints; unknown trailing prose and fictional signatures remain untouched.

**Out of scope:** Gutenberg 47492 (*Old Fort Garland*) is deliberately not changed.

## Verification

- 118 isolated parser-related tests passed, including seven new tests.
- Applied the revised cleanup rules to stored story bodies in `stories(7).zip`: exactly four stories were shortened, each only at the end; no unrelated stories changed.
- This is a stored-body check, not a full original-Gutenberg re-extraction. Please rerun the extractor and compare the resulting archive.
