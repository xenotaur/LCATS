## 2026-08-10 - Regex Compilation Overhead
**Learning:** Python caches inline regex compilation internally, but heavily used functions (e.g. string normalization in tight loops like `canonical_author.py:parse_name`) still experience overhead from cache lookup and `re.sub`/`re.search` wrapper calls.
**Action:** Always pre-compile frequently used regular expression patterns at the module level when executing within tight loops, especially for text-heavy normalization or parsing.
## 2026-08-24 - Native string functions vs Regex overhead
**Learning:** For basic whitespace tokenization (e.g., counting words), native string methods like `str.split()` run significantly faster (~4-5x) than equivalent regular expressions like `re.findall(r"\S+", text)` because they avoid regex engine evaluation overhead.
**Action:** Always prefer native string methods over regex for simple parsing and tokenization tasks, especially when performance is critical.
