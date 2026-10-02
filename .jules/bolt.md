## 2026-08-10 - Regex Compilation Overhead
**Learning:** Python caches inline regex compilation internally, but heavily used functions (e.g. string normalization in tight loops like `canonical_author.py:parse_name`) still experience overhead from cache lookup and `re.sub`/`re.search` wrapper calls.
**Action:** Always pre-compile frequently used regular expression patterns at the module level when executing within tight loops, especially for text-heavy normalization or parsing.
## 2026-09-21 - Python Whitespace Tokenization: split() vs regex
**Learning:** For basic whitespace word tokenization, native string `text.split()` runs significantly faster than the equivalent regex `re.compile(r"\S+").findall(text)` because it runs entirely in optimized C without regex evaluation overhead.
**Action:** Replace `re.findall(r"\S+", text)` with `text.split()` whenever only simple whitespace tokenization is needed.
