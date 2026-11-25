"""Offline audit; archive candidates are not ground-truth chapter labels."""
from pathlib import Path
from collections import Counter
import csv, json, zipfile
from structural_screen import inspect_structure

ROOT=Path(__file__).resolve().parent.parent
rows=[]
for archive in sorted(ROOT.glob('stories*.zip')):
    with zipfile.ZipFile(archive) as z:
        for filename in z.namelist():
            if not filename.endswith('.txt') or not Path(filename).stem.isdecimal():
                continue
            raw=z.read(filename).decode('utf-8-sig',errors='replace')
            d=inspect_structure(raw)
            rows.append({'gutenberg_id':int(Path(filename).stem),'source_archive':archive.name,
                         'raw_rejected':d.reject,'reason':d.reason or '',
                         'evidence':'; '.join(f'{x.line}: {x.excerpt}' for x in d.findings[:5])})
with open('structural_archive_audit.csv','w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader();w.writerows(rows)
summary={'stories_scanned':len(rows),'rejected_raw':sum(r['raw_rejected'] for r in rows),
         'reason_counts':dict(Counter(r['reason'] for r in rows if r['raw_rejected'])),
         'note':'Candidate structural detections only, not verified chapter classification. Existing saved outputs are not rechecked.'}
Path('structural_archive_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
