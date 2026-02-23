PR Request to Improve Coverage
Create a tests-only PR to improve coverage for:

TARGET MODULE:
{{TARGET_MODULE_GHA}}

==================================================
ENVIRONMENT BOOTSTRAP (MANDATORY FIRST STEP)
==================================================

Before doing anything else, prepare the development environment exactly as follows.

From the repository root:

    cd lcats
    python -m pip install --upgrade pip
    python -m pip install -e ".[test]"

Do NOT run tests or coverage before this succeeds.

Do NOT modify project files to fix missing dependencies.
If installation fails, stop and report the error.
NOTE: If black/ruff are not available after this install, stop and report it.
Do NOT modify project code to resolve missing tools.
Do NOT pipe commands through head/tail.
If you must use pipes, enable: set -o pipefail


==================================================
CONSTRAINTS (strict)
==================================================

- Edit ONLY files under: lcats/tests/
- Do NOT modify any production code under lcats/lcats/
- Follow AGENTS.md and lcats/tests/AGENTS.md
- Use unittest only
- Use module imports only:
      from lcats.<submodule> import <module>
- Avoid mocks unless absolutely necessary
- Tests must be deterministic
- Prefer parameterized.expand for curated case tables
- Prefer subTest only for range/programmatic iteration
- Do not reformat unrelated files


==================================================
OUTPUT HANDLING (MANDATORY)
==================================================

LCATS includes user-facing and debug printing. Unit tests must not generate noisy output.

- If code under test prints but the print content is NOT a stable user-facing contract:
Wrap the call with suppress_output().

- If the printed output IS meaningful user-facing output (a "report" / key warning / status):
Use capture_output() and assert only on stable substrings (avoid exact whole-output equality).

Use helpers from:
lcats/tests/utils/capture.py

Do NOT modify production code to remove or change printing.


==================================================
PROCESS (required sequence)
==================================================

1) After bootstrap, run:

       scripts/coverage

2) Identify uncovered lines/functions/branches in:
       {{TARGET_MODULE_GHA}}

3) Summarize:
   - Which functions/branches are uncovered
   - Why they are currently untested
   - Which semi-private helpers (leading underscore) are worth testing directly

4) Propose a small, focused set of new test cases to cover the missing logic.

5) Implement tests:
   - Prefer adding to existing *_test.py if appropriate
   - Otherwise create:
         {{SUGGESTED_TEST_PATH}}
   - Use parameterized.expand for curated edge-case tables
   - Use unittest.TestCase assertion methods only

6) Run:

       scripts/test

7) Run:

       scripts/coverage

8) Format and lint (MANDATORY; only changed files):
    - Compute changed python files:
      CHANGED=$(git diff --name-only origin/main...HEAD -- "*.py")
      echo "$CHANGED"
   - Run Black on changed files only:
      python -m black $CHANGED
   - Run Ruff on changed files only:
      python -m ruff check $CHANGED
   - If either fails, fix the changed test file(s) and re-run until both pass.   - Do NOT reformat unrelated files

9) In the PR description include:
   - Before/after coverage numbers for the target module
   - List of newly covered lines or branches
   - Confirmation that scripts/test passed
   - Confirmation that Black and Ruff passed
   - The exact commands run for black and ruff
   - Their successful exit status

==================================================
FAILURE POLICY
==================================================

- If coverage cannot be improved without modifying production code,
  stop and explain why instead of editing production code.

- If tests fail due to missing dependencies, do NOT modify code.
  Re-run bootstrap.

- If lint fails, fix only the changed test files.


==================================================
ACCEPTANCE CRITERIA
==================================================

- Coverage improves specifically for {{TARGET_MODULE_GHA}}
- Only test files were changed
- scripts/test passes
- Black formatting is clean
- Ruff lint is clean
- No unrelated changes in the diff
