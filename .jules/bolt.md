## 2026-08-10 - Regex Compilation Overhead
**Learning:** Python caches inline regex compilation internally, but heavily used functions (e.g. string normalization in tight loops like `canonical_author.py:parse_name`) still experience overhead from cache lookup and `re.sub`/`re.search` wrapper calls.
**Action:** Always pre-compile frequently used regular expression patterns at the module level when executing within tight loops, especially for text-heavy normalization or parsing.
## 2024-05-28 - Optimize whitespace tokenization
**Learning:** Native string methods like `str.split()` are much faster (~4x) than `re.findall(r'\S+', text)` for simple whitespace tokenization.
**Action:** Prefer `str.split()` over regex for simple word counting and whitespace tokenization tasks.
