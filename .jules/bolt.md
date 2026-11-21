## 2026-08-10 - Regex Compilation Overhead
**Learning:** Python caches inline regex compilation internally, but heavily used functions (e.g. string normalization in tight loops like `canonical_author.py:parse_name`) still experience overhead from cache lookup and `re.sub`/`re.search` wrapper calls.
**Action:** Always pre-compile frequently used regular expression patterns at the module level when executing within tight loops, especially for text-heavy normalization or parsing.

## 2026-09-14 - Native String Methods over Regex for Simple Tokenization
**Learning:** For simple whitespace tokenization (e.g. counting words), native string methods like `str.split()` are significantly faster than regex equivalents like `re.compile(r"\S+").findall(text)` because they avoid regex evaluation overhead.
**Action:** Always prefer native string methods over regular expressions for basic string splitting and whitespace tokenization when complex regex features are not required.
