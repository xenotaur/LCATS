# Targeted terminal-editorial cleanup

Apply `lcats/gatherers/mass_quantities/parser.py` in the code archive to the same path within the LCATS package. Apply `tests/mass_quantities/terminal_editorial_test.py` to your tests directory.

The change adds `_trim_terminal_editorial_tail()` after existing end-of-story cleanup in `clean_gutenberg_story()`. It conservatively detects explicitly labeled terminal transcriber notes, correction tables, and ASCII boxed notes. It does not automatically cut at `THE END`, `FIN.`, or signatures.

Validation:
- Existing parser behavioral tests: 28 passed.
- New terminal editorial behavioral tests: 11 passed.
- In a post-extraction audit of 1,637 `story.json` bodies, identified all 18 previously flagged editorial tails plus one further clearly labeled transcriber note (Gutenberg 69929); no other story bodies were changed by applying the new helper to the already extracted texts.

Important limits:
- The 1,637-body check ran the proposed helper over stored, normalized story bodies, NOT over the original unprocessed Gutenberg source texts. Complete re-extraction against the raw inputs has not been done. It is an encouraging regression check, not full end-to-end validation.
- Source documents with a terminal note longer than the final 160 physical lines may require manual review. Material without an explicit editorial heading is intentionally retained.
- Only parser.py is modified. Existing story JSON files do not change until you rerun extraction.
