## 2024-07-06 - SQL Injection in Gutenberg Cache Queries
**Vulnerability:** Found a SQL injection vulnerability in `lcats/lcats/gettenberg/metadata.py` where the `convert_to_name` function dynamically concatenated unvalidated user input (`number`) into a SQL query executed via `native_query()`.
**Learning:** The database wrapper `gutenbergpy` exposes `native_query()`, a function that takes raw SQL. Since the underlying function is opaque and standard DB-API parameterization syntax (like `?` or `%s`) might not be natively supported by the wrapper, developers reverted to string concatenation without type validation.
**Prevention:** Always cast numeric inputs strictly to integers (e.g. `int(number)`) before string concatenation if parameterization is not available.
## 2024-07-06 - Unsafe SQL queries retrieving multiple columns
**Vulnerability:** A query for getting author names used `SELECT *` and then selected the result using index `[0][1]`. This is brittle and couples the logic to the database schema.
**Learning:** `SELECT *` should be avoided when only a specific column is needed. Furthermore, fetching rows without checking if any rows exist can lead to `IndexError`.
**Prevention:** Query exactly the columns needed (`SELECT name`), and handle empty results gracefully by checking if `rows` is empty before indexing.
