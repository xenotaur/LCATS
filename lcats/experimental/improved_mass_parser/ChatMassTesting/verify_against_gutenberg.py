#!/usr/bin/env python3
"""Cross-compare two LCATS body corpora against locally archived Gutenberg source.

Heuristic, source-grounded alignment: does not claim to certify exact story boundaries.
"""
import csv, json, re, zipfile, collections, unicodedata, statistics, os
from pathlib import Path
ROOT=Path(__file__).resolve().parent
ARCHIVES=[f'stories{i}.zip' for i in range(1,8)]+['stories89.zip']
TOKEN=re.compile(r'[a-z0-9]+')
N=7

def tokens(x):
    x=unicodedata.normalize('NFKD',x).casefold()
    return TOKEN.findall(x)

def loads_corpus(name):
    byid={}
    with zipfile.ZipFile(ROOT/name) as z:
        for item in z.namelist():
            if not item.endswith('/story.json'):continue
            d=json.loads(z.read(item))
            m=d.get('metadata',{})
            found=re.search(r'(?:/epub/|/ebooks/)(\d+)',m.get('url',''))
            if not found: continue
            id=int(found.group(1))
            if id in byid: raise ValueError(f'duplicate ID {id} in {name}')
            byid[id]={'body':d['body'],'title':d.get('name',''),'folder':item.rsplit('/',2)[-2], 'metadata':m}
    return byid

def loads_sources():
    raw={}
    for file in ARCHIVES:
        with zipfile.ZipFile(ROOT/file) as z:
            for item in z.namelist():
                mt=re.search(r'(\d+)\.txt$',item)
                if mt:
                    i=int(mt.group(1))
                    if i in raw: raise ValueError(f'duplicate source {i}')
                    raw[i]=(file, z.read(item).decode('utf-8','replace'))
    return raw

def shingle(t,i):return tuple(t[i:i+N])

def make_index(src):
    idx=collections.defaultdict(list)
    for i in range(max(0,len(src)-N+1)):
        key=shingle(src,i)
        if len(idx[key])<6:idx[key].append(i)
    return idx

def get_alignment(rawtokens, body, idx):
    t=tokens(body)
    covered=bytearray(len(rawtokens))
    bodymatched=bytearray(len(t))
    matches=[]
    for j in range(max(0,len(t)-N+1)):
        hits=idx.get(shingle(t,j))
        if not hits:continue
        for k in range(j,j+N):bodymatched[k]=1
        # Match all positions (incl recurring headings), then group reliable hits.
        for k in hits:
            matches.append((j,k))
            covered[k:k+N]=b'\x01'*N
    positions=[k for j,k in matches]
    # Eliminate isolated head/tail matches, use near the first/last matching chunks.
    return {'words':len(t),'tokens':t,'covered':covered,'bodymatched':bodymatched,
            'body_match_pct':round(100*sum(bodymatched)/max(1,len(t)),2),
            'src_first':min(positions) if positions else None,
            'src_last':max(positions)+N if positions else None,
            'matches':len(matches)}

def nearest_match_excerpt(src,at,n=20):
    if at is None:return ''
    return ' '.join(src[max(0,at):min(len(src),at+n)])

def clipping(s,n=135):
    s=' '.join(s.split())
    return s[:n]+('...' if len(s)>n else '')

def boundaries(raw):
    lines=raw.replace('\r\n','\n').replace('\r','\n').split('\n')
    s=next((i for i,l in enumerate(lines) if re.search(r'^\s*\*{3}\s*START OF (?:THE|THIS) PROJECT GUTENBERG',l,re.I)),None)
    e=next((i for i,l in enumerate(lines) if re.search(r'^\s*\*{3}\s*END OF (?:THE|THIS) PROJECT GUTENBERG',l,re.I)),None)
    return '\n'.join(lines[(s+1 if s is not None else 0):(e if e is not None else len(lines))])

def classify(a,b,src):
    if not a or not b:return 'not_comparable'
    lo=min(x for x in (a['src_first'],b['src_first']) if x is not None) if (a['src_first'] is not None or b['src_first'] is not None) else None
    hi=max(x for x in (a['src_last'],b['src_last']) if x is not None) if (a['src_last'] is not None or b['src_last'] is not None) else None
    if lo is None:return 'alignment_failed'
    # Exclude a tiny number of unmatched tokens at both ends.
    span=max(1,hi-lo)
    old_cov=sum(a['covered'][lo:hi])/span
    new_cov=sum(b['covered'][lo:hi])/span
    if min(a['body_match_pct'],b['body_match_pct'])<80:
        return 'review_source_mismatch_or_extra_text'
    if abs(old_cov-new_cov)<.005:
        return 'roughly_equal_source_coverage'
    if new_cov-old_cov >= .05:
        return 'new_covers_more_source'
    if old_cov-new_cov >= .05:
        return 'old_covers_more_source'
    return 'small_source_coverage_difference'

def main():
    old=loads_corpus('old.zip');new=loads_corpus('new.zip');sources=loads_sources()
    rows=[]; counts=collections.Counter()
    for z,i in enumerate([id for k,id in enumerate(sorted(set(old)|set(new))) if k % int(os.getenv("SHARD_COUNT", "1")) == int(os.getenv("SHARD_INDEX", "0"))]):
        o=old.get(i);n=new.get(i);r=sources.get(i)
        row={'gutenberg_id':i,'old_present':bool(o),'new_present':bool(n),'source_present':bool(r),
             'title':(n or o)['title'],'old_folder':o['folder'] if o else '',
             'new_folder':n['folder'] if n else '', 'source_archive':r[0] if r else '',
             'old_opening':clipping(o['body']) if o else '', 'new_opening':clipping(n['body']) if n else '',
             'old_ending':clipping(o['body'][-180:]) if o else '', 'new_ending':clipping(n['body'][-180:]) if n else ''}
        if not r:
            row.update({'classification':'source_unavailable','assessment':'Cannot verify: no archived Gutenberg source.'})
        else:
            sr=boundaries(r[1]); st=tokens(sr);idx=make_index(st)
            a=get_alignment(st,o['body'],idx) if o else None
            b=get_alignment(st,n['body'],idx) if n else None
            for label,al in [('old',a),('new',b)]:
                if al:
                    row[label+'_words']=al['words'];row[label+'_body_source_match_pct']=al['body_match_pct']
                    row[label+'_src_start_word']=al['src_first'];row[label+'_src_end_word']=al['src_last']
                else:
                    row[label+'_words']='';row[label+'_body_source_match_pct']='';row[label+'_src_start_word']='';row[label+'_src_end_word']=''
            row['source_words_after_envelope']=len(st)
            clas=classify(a,b,st)
            row['classification']=clas
            if a and b and a['src_first'] is not None and b['src_first'] is not None:
                lo=min(a['src_first'],b['src_first']);hi=max(a['src_last'],b['src_last'])
                span=max(1,hi-lo)
                ac=sum(a['covered'][lo:hi]);bc=sum(b['covered'][lo:hi]); union=sum(x or y for x,y in zip(a['covered'][lo:hi],b['covered'][lo:hi]))
                oldonly=sum(x and not y for x,y in zip(a['covered'][lo:hi],b['covered'][lo:hi]));newonly=sum(y and not x for x,y in zip(a['covered'][lo:hi],b['covered'][lo:hi]))
                row.update({'comparison_source_span_words':span,'old_source_covered_words':ac,'new_source_covered_words':bc,
                            'old_source_coverage_pct':round(ac/span*100,2),'new_source_coverage_pct':round(bc/span*100,2),
                            'new_only_aligned_source_words':newonly,'old_only_aligned_source_words':oldonly,
                            'shared_coverage_pct':round(union/span*100,2),
                            'new_start_shift_source_words':b['src_first']-a['src_first'],
                            'new_end_shift_source_words':b['src_last']-a['src_last'],
                            'before_earliest_extraction':nearest_match_excerpt(st,max(0,lo-35),35),
                            'source_text_at_earliest_extraction':nearest_match_excerpt(st,lo,25),
                            'source_text_at_latest_extraction_end':nearest_match_excerpt(st,max(0,hi-25),25)})
                if ac and bc:
                    if newonly>oldonly+80 and newonly>oldonly*2:assessment='New retains substantially more original words; review whether these are narrative or front matter.'
                    elif oldonly>newonly+80 and oldonly>newonly*2:assessment='Old retains substantially more original words; review for new truncation or old editorial residue.'
                    else: assessment='Substantially similar original-word coverage; inspect start/end and internal differences.'
                    if a['body_match_pct']<90 or b['body_match_pct']<90:assessment+=' One/both bodies have weak exact word alignment; may contain non-original material or textual variants.'
                    row['assessment']=assessment
            elif a or b:
                row['assessment']='Only one corpus has a body. Alignment verifies text presence, not editorial boundaries.'
            else:row['assessment']='No aligned body text.'
        counts[row['classification']]+=1
        rows.append(row)
        if z%250==0:print('analyzed',z,'/',len(set(old)|set(new)),flush=True)
    fields=list(dict.fromkeys(k for row in rows for k in row))
    with (ROOT/('gutenberg_source_verification_'+os.getenv('SHARD_INDEX','0')+'.csv')).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    print('counts',counts)
    for key in ['new_only_aligned_source_words','old_only_aligned_source_words']:
        print('\n',key)
        for x in sorted(rows,key=lambda r:int(r.get(key,0)),reverse=True)[:12]:print(x['gutenberg_id'],x['title'][:38],x.get(key),x.get('new_start_shift_source_words'),x.get('new_end_shift_source_words'), x.get('old_body_source_match_pct'),x.get('new_body_source_match_pct'))
    print('source unavailable',[(r['gutenberg_id'],r['title']) for r in rows if not r['source_present']])
    return rows
if __name__=='__main__':main()
