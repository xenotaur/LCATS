# LCATS tests: agent guidance

## Framework
- Use `unittest` only (no pytest).
- Follow existing naming: `*_test.py`.

## Test execution
- Always run `scripts/test` after making changes.
- Keep new tests deterministic; avoid reliance on clock/time/random unless seeded and justified.

## Imports (important)
- Use module imports only for LCATS code.
- Use `from package import module` syntax (do not use `import package.module as module`).

Example:
  - ✅ `from lcats.lcats.utils import canonical_author`
  - Use as: `canonical_author.parse_name(...)`
  - ❌ `import lcats.lcats.utils.canonical_author as canonical_author`
  - ❌ `from lcats.lcats.utils.canonical_author import parse_name`

## What to test
- Prefer pure/deterministic behavior.
- Use table-driven tests with `subTest` where appropriate.
- For serializers/extractors: add an invariant test such as “result can be `json.dumps`’d”.

## What not to do
- Do not add or expand print/debug output in tests.
- If existing tests print excessively, do not “fix” them unless asked.
