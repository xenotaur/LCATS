"""Training-only side-by-side narrative boundary evaluation.

Reproduce with `python study_frontmatter.py` from the package directory.
Uses the ground-truth opening; does not download data or modify annotations.
The original split's test data is NOT consulted for this feature selection.
"""
from __future__ import annotations
import csv
import json
from pathlib import Path
import gutenberg_extractor as p
from evaluate import reference_line

ROOT=Path(__file__).parent

def predict(record, *, apply_precision):
    opening=record['original_opening'].replace('\r\n','\n').replace('\r','\n')
    lines=opening.split('\n')
    title=record['title']; authors=record['authors']
    lo, hi, _ = p.identify_story_boundaries(opening,title,authors,[])
    warnings=[]
    lo=p._refine_front_boundary(lines,lo,hi,title,warnings)
    lo=p._refine_repeated_display_heading(lines,lo,hi,title,authors,[],warnings)
    lo=p._conservative_narrative_guard(lines,lo,hi,title,warnings)
    lo=p._bracketed_marker_narrative_guard(lines,lo,hi,title,authors,[],warnings)
    lo=p._dated_scene_opening_guard(lines,lo,hi,title,authors,[],warnings)
    lo=p.preserve_structural_opening(lines,lo,hi,title,authors,
        title_match=p._title_span,author_match=p._author_line,warnings=warnings)
    if apply_precision:
        lo=p.refine_promotional_blurb_boundary(lines,lo,hi,title,authors,warnings)
    return lo, warnings

def main():
    records=json.loads((ROOT/'training.json').read_text(encoding='utf8'))
    rows=[]
    for row in records:
        ref=reference_line(row)
        before, _ = predict(row,apply_precision=False)
        after, reasons = predict(row,apply_precision=True)
        rows.append({'gutenberg_id':row['gutenberg_id'],
          'title':row['title'][0] if row['title'] else '',
          'reference_line':None if ref is None else ref+1,
          'before_line':before+1,'after_line':after+1,
          'before_offset':None if ref is None else before-ref,
          'after_offset':None if ref is None else after-ref,
          'lines_removed':after-before,
          'reason':'short_italic_teaser_separator_removed' if after>before else ''})
    metrics={}
    for name in ('before','after'):
        offsets=[r[name+'_offset'] for r in rows if r[name+'_offset'] is not None]
        metrics[name]={
          'assessable':len(offsets),'unassessable':len(rows)-len(offsets),
          'exact':sum(x==0 for x in offsets),
          'narrative_loss_cases':sum(x>0 for x in offsets),
          'narrative_lines_lost':sum(max(x,0) for x in offsets),
          'extra_frontmatter_cases':sum(x<0 for x in offsets),
          'extra_frontmatter_lines':sum(max(-x,0) for x in offsets)}
    changes=[r for r in rows if r['lines_removed']>0]
    extra_loss=[r for r in changes if r['after_offset'] is not None and r['after_offset']>max(r['before_offset'],0)]
    result={'training_entries':len(records),'metrics':metrics,
            'changed_entries':len(changes),
            'excess_lines_removed':sum(r['lines_removed'] for r in changes),
            'new_or_increased_narrative_loss':len(extra_loss),
            'changed_gutenberg_ids':[r['gutenberg_id'] for r in changes],
            'qualification':'Training-only evaluation; already inspected prior held-back cases; no fresh independent test.'}
    with (ROOT/'frontmatter_training_results.csv').open('w',encoding='utf8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    (ROOT/'frontmatter_training_summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
