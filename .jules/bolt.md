## 2024-11-09 - Faster Title Detection with Native Split
**Learning:** `re.split(r"\s+", line)` inside a list comprehension to filter empty strings is a performance anti-pattern. Native `line.split()` is significantly faster and natively handles empty string filtering for whitespace splits.
**Action:** Always prefer native string `.split()` for simple whitespace separation over compiling and running regular expressions.
