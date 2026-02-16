from gutenbergpy.gutenbergcache import GutenbergCache

GutenbergCache.create()
cache  = GutenbergCache.get_cache()

cache.native_query("SELECT * FROM books")
