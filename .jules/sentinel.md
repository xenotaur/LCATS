## 2024-07-06 - SQL Injection in Gutenberg Cache Queries
**Vulnerability:** Found a SQL injection vulnerability in `lcats/lcats/gettenberg/metadata.py` where the `convert_to_name` function dynamically concatenated unvalidated user input (`number`) into a SQL query executed via `native_query()`.
**Learning:** The database wrapper `gutenbergpy` exposes `native_query()`, a function that takes raw SQL. Since the underlying function is opaque and standard DB-API parameterization syntax (like `?` or `%s`) might not be natively supported by the wrapper, developers reverted to string concatenation without type validation.
**Prevention:** Always cast numeric inputs strictly to integers (e.g. `int(number)`) before string concatenation if parameterization is not available.
