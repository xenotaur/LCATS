# LCATS terminal cleanup (conservative expansion)

Apply these files in the existing LCATS repository, keeping the relative paths:

- `lcats/gatherers/mass_quantities/parser.py` (replace existing parser)
- `tests/mass_quantities/terminal_supplement_test.py` (new)
- `tests/mass_quantities/terminal_editorial_test.py` (compatible latest tests)
- `tests/mass_quantities/terminal_publication_markers_test.py` (unchanged latest tests)

The parser retains prior Gutenberg boundary, terminal editorial, and `year.json`
logic. The only new behaviors are:

1. Remove a short, explicitly identified printer/publisher imprint at the very
   end of a story.
2. Remove publisher advertisements or the Hugo winners list *only* after a
   standalone terminal ending marker and a matching editorial heading.
3. Separate numbered, terminal explanatory footnotes *only* when a final
   standalone ending marker precedes them. Save the notes as `footnotes.json`
   next to `story.json`, **only after successful new publication**. A missing
   note creates no file, and reuse or failed publication creates no new file.
4. Remove terminal end markers that become exposed after cleaning.
5. Allow a final dash-prefixed pen-name byline only if an identical explicit
   `By ...` credit appears in the original opening. Unmatched/fictional
   signatures remain untouched.

## Sidecar structure

`footnotes.json` contains `gutenberg_id`, `title`, and `footnotes` (verbatim
content with physical lines in each note joined for readability). This sidecar
is supplementary and is not included in the narrative `story.json` body.

## Validation

- 111 focused parser, terminal editorial/publication, and publication-year
  integration tests passed in the isolated LCATS test harness.
- Applied terminal cleanup to stored bodies in `stories(6).zip`: 12 stories
  shortened strictly at the end. Four terminal footnote sections are retained
  as supplemental data. No other stored stories were shortened.
- Two additional terminal pen-name credits (Gutenberg 29503 and 31841) match
  explicit opening bylines; those require re-extraction of the original source
  for final verification rather than an already-cleaned-story dry run.
- A full original-Gutenberg re-extraction was not performed. The tests used
  isolated substitutes for unavailable full-application modules.

The source parser remains conservative: unidentified prose after an ending
marker is left in place, fictional signatures are not removed, and unanchored
footnotes are not deleted.
