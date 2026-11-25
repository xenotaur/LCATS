"""Measure structural/spacing features on TRAINING examples only."""
import json,csv,re
from collections import Counter
from pathlib import Path
from evaluate import reference_line,estimate
D=Path(__file__).resolve().parent
records=json.loads((D/'training.json').read_text())
rows=[]
for r in records:
    ref=reference_line(r)
    if ref is None: continue
    lines=r['original_opening'].replace('\r\n','\n').replace('\r','\n').split('\n')
    before=ref-1
    while before>=0 and not lines[before].strip(): before-=1
    prev=lines[before].strip() if before>=0 else ''
    gap=ref-before-1
    # closest preceding line containing a title/byline/illustrator/production note
    neighborhood=lines[max(0,ref-12):ref]
    label=('byline' if re.match(r'(?i)^by\s+\w',prev) else
      'credit' if re.match(r'(?i)^(illustrat(?:ed|ion)|first published|published|transcrib)',prev) else
      'title_or_heading' if prev and len(prev)<70 and prev.upper()==prev else
      'prose_or_other')
    pred=estimate(r,guarded=True)
    rows.append(dict(id=r['gutenberg_id'],reference=ref+1,prediction=pred+1,offset=pred-ref,
      gap=gap,previous_type=label,prev=prev[:110],start=lines[ref][:110],
      preceding_title=any(re.match(r'(?i)^by\s+\w',x.strip()) for x in neighborhood),
      start_short= len(lines[ref].strip())<40,
      start_allcaps=bool(lines[ref].strip()) and lines[ref].strip().upper()==lines[ref].strip(),
      previous_italic=prev.startswith('_') or prev.endswith('_')))
with (D/'training_boundary_features.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
summary={'n':len(rows),'gap_distribution':dict(sorted(Counter(min(x['gap'],6) for x in rows).items())),
 'gap_given_previous_type':{},'predicted_late_by_type':{},'examples_late':[]}
for t in sorted(set(x['previous_type'] for x in rows)):
 subset=[x for x in rows if x['previous_type']==t];summary['gap_given_previous_type'][t]={
 'n':len(subset),'gap_at_least_2':sum(x['gap']>=2 for x in subset),
 'gap_at_least_3':sum(x['gap']>=3 for x in subset)}
 summary['predicted_late_by_type'][t]=sum(x['offset']>0 for x in subset)
summary['examples_late']=[{k:x[k] for k in ('id','offset','gap','previous_type','prev','start')} for x in rows if x['offset']>0][:40]
(D/'training_feature_summary.json').write_text(json.dumps(summary,indent=2))
print(json.dumps({k:v for k,v in summary.items() if k!='examples_late'},indent=2))
print('late cases:', summary['examples_late'])
