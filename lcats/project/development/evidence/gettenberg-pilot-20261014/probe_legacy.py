"""Observe the installed legacy query path using a read-only existing DB."""
import json
import pathlib
import sqlite3
import sys
from unittest import mock
from gutenbergpy.caches import sqlitecache
from lcats.gettenberg import api
from lcats.gettenberg import cache

database=pathlib.Path(sys.argv[1]).resolve()
legacy=sqlitecache.SQLiteCache()
legacy.connection=sqlite3.connect(database.as_uri()+'?mode=ro&immutable=1',uri=True)
legacy.cursor=legacy.connection.cursor()
legacy.connection.execute('PRAGMA query_only=ON')
rows=legacy.query(languages=['en'])
result={'upstream_en_count':len(rows),'upstream_row_type':type(rows[0]).__name__, 'upstream_row_example':rows[0], 'factory_substitution':'Only cache acquisition factory replaced with real read-only SQLiteCache; actual query and wrapper implementations executed; no network.'}
with mock.patch.object(cache,'ensure_gutenberg_cache',return_value=legacy):
 result['public_wrapper_en_count']=len(api.get_etexts(languages='en'))
 try:
  api.get_matching_rows(languages='en',downloadtype=['text/plain'])
 except TypeError as error:
  result['mapping_probe_error']=str(error)
  result['mapping_probe_scope']='Diagnostic list-valued downloadtype bypasses separate string-iteration bug; not a supported public API call.'
legacy.connection.close()
print(json.dumps(result,indent=2))
