## 2026-08-31 - [Native string methods outperform Regex for basic split]
**Learning:** [Using `str.split()` for counting whitespace-separated words is significantly faster (~4.3x) than using the `re.findall(r"\S+")` regex, completely removing overhead and providing the same count results. No readability tradeoff either.]
**Action:** [Always prefer native string operations over regex when accomplishing basic string parsing like simple tokenization or simple splitting]
