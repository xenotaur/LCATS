
## 2026-07-14 - SQL Injection Risk via String Concatenation in Cache Query
**Vulnerability:** A local SQLite query in `metadata.py` passed the parameter `number` directly to a query string: `"Select * from authors where id=" + str(number)`.
**Learning:** This existed because the local cache wrapper (`native_query`) doesn't enforce or encourage parameterized queries by default, leading to naive string concatenation for IDs.
**Prevention:** When unable to use parameterized queries, strictly enforce types using standard Python casting (e.g. `int()`) on all input variables before string interpolation.
