import csv,collections,zipfile
from pathlib import Path
root=Path('/mnt/data')
with (root/'gutenberg_source_verification.csv').open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
shared=[r for r in rows if r['source_present']=='True' and r['old_present']=='True' and r['new_present']=='True']
count=collections.Counter(r['classification'] for r in shared)
major=['20257','58744','67580','72147','64841','24375','3711','63123','65347','24566','50940','31964','60393','65241','42640','51006','26956','49767','51570','26967','47492']
notes={
'20257':'New recovers narrative beginning at "In my last"; old begins in later correspondence and is severely truncated. New wins on completeness.',
'58744':'New restores 8,392 source words preceding the old opening; new wins strongly.',
'67580':'New restores 8,258 source words preceding old opening; new wins strongly.',
'72147':'New restores original opening; old starts much later; new wins strongly.',
'64841':'New covers 7,313 more source words; inspect structure for any internal cut in old.',
'24375':'New restores most of the literary text omitted in old.',
'3711':'New restores a large earlier portion omitted in old.',
'63123':'New restores a long omitted earlier portion.',
'65347':'New BAD: original italicized opening is a narrative scene with named speakers El, Bee, Peak; new jumps to Ted Truesdale after a scene divider (537 words omitted). Old preserves that scene.',
'24566':'New BAD: skips first dated scene (JULY 18, 1949 A.D.) and begins at JUNE 13, 427th Year GALACTIC ERA, about 480 words later. Old retains first scene.',
'50940':'New BAD: skips narrative opening and starts at later action about a tunnel, ~406 words after old. Old has a magazine tagline before opening; remove tagline but preserve narrative.',
'31964':'New BAD: skips early first-person narrative about circus life. Old has promotional standfirst; strip standfirst but retain story.',
'60393':'New BAD: skips italicized expository story opening about the "morons" and 2010 government hunters, 381 words. Old includes opening narrative.',
'65241':'New BAD: skips 201 narrative words describing Rick Mason receiving his partner’s distress call. Old retains this.',
'42640':'New correctly removes opening publication-history note, but incorrectly RETAINS terminal edition/printing statement (NINE HUNDRED AND FIFTY COPIES...). Neither body is fully clean; old has an opening editorial note.',
'51006':'New removes opening editorial paratext and terminal colophon; new is better; old retains these.',
'26956':'Both preserve the first dialogue line in these archives; old retains a few additional source words elsewhere.',
'49767':'Both preserve initial dialogue and have essentially identical source-word coverage.',
'51570':'New starts with narrative “Baby Doll,” while old retains preceding promotional magazine teaser. New better.',
'26967':'Old contains a copyright line and transcriber note; new correctly removes them. Old extra source words are not story words.',
'47492':'New restores journal narrative omitted by old, but includes an author’s note and footnotes that may or may not belong under corpus policy; targeted editorial review needed.'
}
with (root/'gutenberg_source_priority_review.csv').open('w',encoding='utf-8-sig',newline='') as f:
 fields=['gutenberg_id','title','classification','old_words','new_words','old_only_aligned_source_words','new_only_aligned_source_words','new_start_shift_source_words','new_end_shift_source_words','old_opening','new_opening','assessment','manual_review_note'];w=csv.DictWriter(f,fields,extrasaction='ignore');w.writeheader()
 selected=[r for r in rows if r['classification'] in ('new_covers_more_source','old_covers_more_source','source_unavailable') or r['gutenberg_id'] in major]
 for r in selected:w.writerow({**r,'manual_review_note':notes.get(r['gutenberg_id'],'Needs manual determination: original-word coverage is not sufficient to distinguish narrative from editorial matter.')})
lines=[]
lines.append('# Verification of old and new LCATS Gutenberg extractions against source archives\n')
lines.append('## Scope and limitations\n')
lines.append(f'- Source ZIPs: {", ".join([f"stories{i}.zip" for i in range(1,8)]+["stories89.zip"])}. **1,660 distinct archived IDs**.')
lines.append('- The old and new corpora were matched by Project Gutenberg ID in the JSON metadata, not filenames. **1,640** stories occur in both and have an archived original.')
lines.append('- Seven new-only Gutenberg IDs have no corresponding file in the source ZIPs (see CSV); they **cannot be source-verified** using supplied archives.')
lines.append('- Automated comparison uses case-insensitive alphanumeric tokens and a seven-token rolling exact-match shingle. It disregards punctuation, typography, underscores, line-breaks, and paragraph joining when locating original text.')
lines.append('- **Source-word coverage is a completeness measure, not an editorial correctness score.** Transcriber notes and magazine teasers occur in the source; retaining these can produce misleadingly higher coverage. Similarly, a story can be incomplete even though every retained word matches the source. Significant differences are inspected against original presentation.')
lines.append('- Some extractions use Gettenberg editions that may differ slightly from the archived sources. The normalization and exact matching approach is conservative, not a proof of textual identity or exact boundaries.\n')
lines.append('## Results across 1,640 directly comparable stories\n')
lines.append('| Automated classification | Stories | Meaning |\n|---|---:|---|')
for category,explanation in [
 ('roughly_equal_source_coverage','Within about 0.5 percentage points in covered source span; may still differ in editorial boundaries.'),
 ('small_source_coverage_difference','Different by less than five percentage points; review where changes occur.'),
 ('new_covers_more_source','New covers >= 5 percentage points more of the union source span.'),
 ('old_covers_more_source','Old covers >= 5 percentage points more of the union source span.')]:
 lines.append(f'| {category} | {count[category]} | {explanation} |')
lines.append('\nAn increase in source coverage should not be interpreted as an unconditional win; the actual literary opening/ending is the decision criterion.\n')
lines.append('## Confirmed or strongly supported improvements in new corpus\n')
lines.append('| Gutenberg ID | Story | Additional original words aligned in new | Finding |\n|---:|---|---:|---|')
for i in ['20257','58744','67580','72147','64841','24375','3711','63123']:
 r=next(x for x in rows if x['gutenberg_id']==i)
 lines.append(f'| {i} | {r["title"]} | {r["new_only_aligned_source_words"]} | {notes[i]} |')
lines.append('\n## Confirmed new-extractor losses and other defects\n')
lines.append('| Gutenberg ID | Original-based finding |\n|---:|---|')
for i in ['65347','24566','50940','31964','60393','65241','42640','51006','26967','51570','47492']:
 lines.append(f'| {i} | {notes[i]} |')
lines.append('\nThese cases demonstrate that the new extractor can mistakenly treat **genuine opening scenes as editorial material**, particularly italicized passages or sections separated by asterisks. They deserve regression tests preserving the entire opening, not only the first one or two sentences.\n')
lines.append('## Prior three opening-dialogue reports\n')
for i in ['26956','49767','51570']:lines.append(f'- **{i}**: {notes[i]}')
lines.append('\n## Correctness conclusion\n')
lines.append('1. The new extraction has large, clear completeness improvements across many stories; it is a stronger overall starting point.')
lines.append('2. The new corpus has **confirmed deletions of true narrative**. At minimum the six cases listed above should be corrected before treating the new corpus as an authoritative replacement.')
lines.append('3. The old corpus also contains editorial residue and sometimes loses the beginning or most of the story.')
lines.append('4. Neither archive can be certified 100% correct with this automated comparison; the row-level CSV lists all stories, passage coverage and opening/ending snippets. Boundary correctness requires checking source structure for cases where editorial or narrative material is ambiguous.')
lines.append('5. Because existing outputs are reused by the Gettenberg gatherer, corrections to parser rules will require controlled regeneration of the affected JSON files.\n')
lines.append('## Deliverables\n')
lines.append('- `gutenberg_source_verification.csv`: all 1,667 IDs, corpus membership, source match rates, aligned source-word coverage, first/last alignment positions and snippets, and interpretation flags.')
lines.append('- `gutenberg_source_priority_review.csv`: the 64 materially-new-more, 11 materially-old-more, seven no-source cases, plus selected important examples.')
lines.append('- `verify_against_gutenberg.py`: reproducible verifier; uses `SHARD_INDEX` and `SHARD_COUNT` environment variables for parallel batches.')
lines.append('- `build_source_verification_report.py`: report generator.')
(root/'gutenberg_source_verification_report.md').write_text('\n'.join(lines),encoding='utf-8')
with zipfile.ZipFile(root/'gutenberg_original_verification_package.zip','w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for f in ['gutenberg_source_verification_report.md','gutenberg_source_verification.csv','gutenberg_source_priority_review.csv','verify_against_gutenberg.py','build_source_verification_report.py']: z.write(root/f,arcname=f)
print('built',len(rows),'rows',len(selected),'priority')
