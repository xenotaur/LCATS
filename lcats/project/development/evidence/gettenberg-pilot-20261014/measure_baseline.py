"""Read-only, bounded audit of an existing Gutenberg archive and SQLite cache."""
import collections
import hashlib
import json
import pathlib
import resource
import sqlite3
import sys
import tarfile
import time
from lxml import etree

archive = pathlib.Path(sys.argv[1]).resolve()
database = pathlib.Path(sys.argv[2]).resolve()
output = pathlib.Path(sys.argv[3])
start = time.monotonic()
limits = dict(archive_bytes=256 * 1024**2, expanded_bytes=4 * 1024**3,
              member_bytes=8 * 1024**2, members=200000, seconds=180)
if archive.stat().st_size > limits['archive_bytes']:
    raise ValueError('compressed archive exceeds byte limit')
def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()
identity = {str(p.name): {'size_bytes': p.stat().st_size, 'sha256': digest(p),
                         'mtime_ns': p.stat().st_mtime_ns} for p in [archive, database]}
ns={'pg':'http://www.gutenberg.org/2009/pgterms/', 'dc':'http://purl.org/dc/terms/',
    'rdf':'http://www.w3.org/1999/02/22-rdf-syntax-ns#'}
tags=collections.Counter(); attributes=collections.Counter(); categories=collections.Counter()
features={}; samples={}; max_member=0; total_bytes=0; count=0
parser=etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False)
with tarfile.open(archive,'r|bz2') as stream:
    for member in stream:
        count+=1
        if count > limits['members'] or time.monotonic()-start >= limits['seconds']:
            raise ValueError('archive member count or elapsed-time limit exceeded')
        max_member=max(max_member,member.size)
        if member.size < 0 or member.size > limits['member_bytes']:
            raise ValueError('archive member exceeds byte limit')
        total_bytes+=member.size
        if total_bytes > limits['expanded_bytes']:
            raise ValueError('expanded archive exceeds byte limit')
        if not member.isfile():
            categories['directory' if member.isdir() else 'other_nonregular']+=1
            stream.members.clear();continue
        if not member.name.endswith('.rdf'):
            categories['non_rdf_file']+=1; stream.members.clear();continue
        raw=stream.extractfile(member).read(limits['member_bytes']+1)
        if b'<!DOCTYPE' in raw or b'<!ENTITY' in raw:
            raise ValueError('DTD/entity in '+member.name)
        root=etree.fromstring(raw, parser=parser)
        books=root.findall('pg:ebook', ns)
        categories['ebook' if books else 'non_ebook_rdf']+=1
        for e in root.iter():
            if isinstance(e.tag,str): tags[e.tag]+=1; attributes.update(e.attrib.keys())
        checks={'alias':root.findall('.//pg:alias',ns),'alternative_title':root.findall('.//dc:alternative',ns),
                'multiple_languages':len(root.findall('.//pg:ebook/dc:language',ns))>1,
                'non_creator_role':any('loc.gov/loc.terms/relators/' in t.tag for t in root.iter() if isinstance(t.tag,str)),
                'non_ebook_rdf':not books}
        for key, value in checks.items():
            if value and key not in features:
                features[key]={'member':member.name,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
                samples[key]=raw.decode('utf-8')
        if member.name.endswith('/pg84.rdf') or member.name.endswith('/pg1.rdf'):
            samples[member.name.split('/')[-1]]=raw.decode('utf-8')
        stream.members.clear()
archive_seconds=time.monotonic()-start
connection=sqlite3.connect(database.as_uri()+'?mode=ro&immutable=1',uri=True)
connection.execute('PRAGMA query_only=ON')
tables=[r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
counts={t:connection.execute('SELECT COUNT(*) FROM "'+t+'"').fetchone()[0] for t in tables}
queries={}
for name,sql in [('language_en',"SELECT gutenbergbookid FROM books JOIN languages ON languages.id=books.languageid WHERE languages.name='en' ORDER BY gutenbergbookid LIMIT 100"),('id_84', 'SELECT * FROM books WHERE gutenbergbookid=84')]:
 t=time.perf_counter(); rows=connection.execute(sql).fetchall(); queries[name]={'sql':sql,'elapsed_seconds':time.perf_counter()-t,'row_count':len(rows),'first_row':rows[0] if rows else None}
connection.close()
for p in [archive,database]:
 if identity[p.name]['mtime_ns'] != p.stat().st_mtime_ns:
  raise ValueError('audit input changed during measurement: '+p.name)
result={'schema_version':1,'bounds':limits,'identity':identity,'provenance':'Pre-existing local cache; original retrieval URL/time and DB-to-archive correspondence unverified. Hashes identify observed bytes, not retrieval provenance.', 'members':count,'categories':dict(categories),'expanded_bytes':total_bytes,'max_member_bytes':max_member,'xml_elements':dict(sorted(tags.items())),'xml_attributes':dict(sorted(attributes.items())),'feature_examples':features,'database_table_counts':counts,'queries':queries,'archive_audit_seconds':archive_seconds,'elapsed_seconds':time.monotonic()-start,'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'peak_rss_method':'resource.getrusage(RUSAGE_SELF).ru_maxrss on macOS (bytes), includes Python/parser/hash/database audit','network_bytes':0,'temporary_extracted_files':0,'samples_saved_separately_for_inspection':list(samples)}
output.write_text(json.dumps(result,indent=2)+'\n')
output.with_name('rdf_samples.json').write_text(json.dumps(samples,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['members','categories','feature_examples','elapsed_seconds','peak_rss_bytes']},indent=2))
