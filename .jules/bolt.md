## 2026-07-08 - String split vs Regex findall Performance
**Learning:** For simple word tokenization based on whitespace, Python's built-in `str.split()` method is roughly 3-4x faster than compiling and running the equivalent regular expression `re.compile(r"\S+").findall(text)`, while yielding exactly the same word count result, handling both ASCII and Unicode whitespace correctly.
**Action:** Default to using `str.split()` for basic whitespace tokenization or word counting instead of regex, as it is faster, safer, and cleaner.
