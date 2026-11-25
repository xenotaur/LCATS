# Verification of old and new LCATS Gutenberg extractions against source archives

## Scope and limitations

- Source ZIPs: stories1.zip, stories2.zip, stories3.zip, stories4.zip, stories5.zip, stories6.zip, stories7.zip, stories89.zip. **1,660 distinct archived IDs**.
- The old and new corpora were matched by Project Gutenberg ID in the JSON metadata, not filenames. **1,640** stories occur in both and have an archived original.
- Seven new-only Gutenberg IDs have no corresponding file in the source ZIPs (see CSV); they **cannot be source-verified** using supplied archives.
- Automated comparison uses case-insensitive alphanumeric tokens and a seven-token rolling exact-match shingle. It disregards punctuation, typography, underscores, line-breaks, and paragraph joining when locating original text.
- **Source-word coverage is a completeness measure, not an editorial correctness score.** Transcriber notes and magazine teasers occur in the source; retaining these can produce misleadingly higher coverage. Similarly, a story can be incomplete even though every retained word matches the source. Significant differences are inspected against original presentation.
- Some extractions use Gettenberg editions that may differ slightly from the archived sources. The normalization and exact matching approach is conservative, not a proof of textual identity or exact boundaries.

## Results across 1,640 directly comparable stories

| Automated classification | Stories | Meaning |
|---|---:|---|
| roughly_equal_source_coverage | 1214 | Within about 0.5 percentage points in covered source span; may still differ in editorial boundaries. |
| small_source_coverage_difference | 351 | Different by less than five percentage points; review where changes occur. |
| new_covers_more_source | 64 | New covers >= 5 percentage points more of the union source span. |
| old_covers_more_source | 11 | Old covers >= 5 percentage points more of the union source span. |

An increase in source coverage should not be interpreted as an unconditional win; the actual literary opening/ending is the decision criterion.

## Confirmed or strongly supported improvements in new corpus

| Gutenberg ID | Story | Additional original words aligned in new | Finding |
|---:|---|---:|---|
| 20257 | A Political Romance | 9385 | New recovers narrative beginning at "In my last"; old begins in later correspondence and is severely truncated. New wins on completeness. |
| 58744 | Money is the Root of All Good | 8392 | New restores 8,392 source words preceding the old opening; new wins strongly. |
| 67580 | Under the Skin | 8258 | New restores 8,258 source words preceding old opening; new wins strongly. |
| 72147 | Respectfully mine | 7498 | New restores original opening; old starts much later; new wins strongly. |
| 64841 | Dark Reality | 7313 | New covers 7,313 more source words; inspect structure for any internal cut in old. |
| 24375 | Wizard | 6973 | New restores most of the literary text omitted in old. |
| 3711 | The Relics of General Chasse: A Tale of Antwerp | 6139 | New restores a large earlier portion omitted in old. |
| 63123 | The Eyes of Thar | 5895 | New restores a long omitted earlier portion. |

## Confirmed new-extractor losses and other defects

| Gutenberg ID | Original-based finding |
|---:|---|
| 65347 | New BAD: original italicized opening is a narrative scene with named speakers El, Bee, Peak; new jumps to Ted Truesdale after a scene divider (537 words omitted). Old preserves that scene. |
| 24566 | New BAD: skips first dated scene (JULY 18, 1949 A.D.) and begins at JUNE 13, 427th Year GALACTIC ERA, about 480 words later. Old retains first scene. |
| 50940 | New BAD: skips narrative opening and starts at later action about a tunnel, ~406 words after old. Old has a magazine tagline before opening; remove tagline but preserve narrative. |
| 31964 | New BAD: skips early first-person narrative about circus life. Old has promotional standfirst; strip standfirst but retain story. |
| 60393 | New BAD: skips italicized expository story opening about the "morons" and 2010 government hunters, 381 words. Old includes opening narrative. |
| 65241 | New BAD: skips 201 narrative words describing Rick Mason receiving his partner’s distress call. Old retains this. |
| 42640 | New correctly removes opening publication-history note, but incorrectly RETAINS terminal edition/printing statement (NINE HUNDRED AND FIFTY COPIES...). Neither body is fully clean; old has an opening editorial note. |
| 51006 | New removes opening editorial paratext and terminal colophon; new is better; old retains these. |
| 26967 | Old contains a copyright line and transcriber note; new correctly removes them. Old extra source words are not story words. |
| 51570 | New starts with narrative “Baby Doll,” while old retains preceding promotional magazine teaser. New better. |
| 47492 | New restores journal narrative omitted by old, but includes an author’s note and footnotes that may or may not belong under corpus policy; targeted editorial review needed. |

These cases demonstrate that the new extractor can mistakenly treat **genuine opening scenes as editorial material**, particularly italicized passages or sections separated by asterisks. They deserve regression tests preserving the entire opening, not only the first one or two sentences.

## Prior three opening-dialogue reports

- **26956**: Both preserve the first dialogue line in these archives; old retains a few additional source words elsewhere.
- **49767**: Both preserve initial dialogue and have essentially identical source-word coverage.
- **51570**: New starts with narrative “Baby Doll,” while old retains preceding promotional magazine teaser. New better.

## Correctness conclusion

1. The new extraction has large, clear completeness improvements across many stories; it is a stronger overall starting point.
2. The new corpus has **confirmed deletions of true narrative**. At minimum the six cases listed above should be corrected before treating the new corpus as an authoritative replacement.
3. The old corpus also contains editorial residue and sometimes loses the beginning or most of the story.
4. Neither archive can be certified 100% correct with this automated comparison; the row-level CSV lists all stories, passage coverage and opening/ending snippets. Boundary correctness requires checking source structure for cases where editorial or narrative material is ambiguous.
5. Because existing outputs are reused by the Gettenberg gatherer, corrections to parser rules will require controlled regeneration of the affected JSON files.

## Deliverables

- `gutenberg_source_verification.csv`: all 1,667 IDs, corpus membership, source match rates, aligned source-word coverage, first/last alignment positions and snippets, and interpretation flags.
- `gutenberg_source_priority_review.csv`: the 64 materially-new-more, 11 materially-old-more, seven no-source cases, plus selected important examples.
- `verify_against_gutenberg.py`: reproducible verifier; uses `SHARD_INDEX` and `SHARD_COUNT` environment variables for parallel batches.
- `build_source_verification_report.py`: report generator.