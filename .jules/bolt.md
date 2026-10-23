## 2026-08-10 - Regex Compilation Overhead
**Learning:** Python caches inline regex compilation internally, but heavily used functions (e.g. string normalization in tight loops like `canonical_author.py:parse_name`) still experience overhead from cache lookup and `re.sub`/`re.search` wrapper calls.
**Action:** Always pre-compile frequently used regular expression patterns at the module level when executing within tight loops, especially for text-heavy normalization or parsing.
## 2023-10-27 - Fast Whitespace Tokenization
**Learning:** `re.findall(r"\S+", text)` is surprisingly slow compared to `text.split()` for counting non-whitespace tokens. `text.split()` is implemented in C and runs about ~4.5x faster in benchmarks on this codebase.
**Action:** Replace `re.findall(r"\S+", text)` with `text.split()` for basic word counting based on whitespace boundaries.
