# LCATS Style Guide (Canonical)

This document is the authoritative style and engineering guide for LCATS.

All contributors (human and agent) must follow `STYLE.md`.  
Any older or conflicting style documents are deprecated and should not be used.

## Quick Start (Human Summary)

If you follow only a few rules, follow these:

1. **Imports**
   - Always import modules, not symbols  
   - `from lcats.utils import names`  
   - `names.normalize(...)`

2. **Formatting**
   - Run `scripts/format` and `scripts/lint` before committing  
   - Do not rely on editor formatting

3. **Docstrings**
   - Use Google-style docstrings for most functions  
   - One-line docstrings are fine for trivial functions

4. **Aliases**
   - Avoid aliases unless standard (`np`, `pd`), necessary, or clearly helpful

5. **Tests**
   - Use `unittest` (not `pytest`)  
   - Prefer deterministic tests
   - Use the `capture` library to suppress print output.

6. **General Principle**
   - Prefer clarity and consistency over cleverness

For full details, see the sections below.


## 0. Style Precedence

When style rules overlap, apply them in this order:

1. Rules in this file (`STYLE.md`)
2. Google Python Style Guide (for unspecified cases)
3. PEP 8 (fallback only)

If an older document conflicts with this guide, `STYLE.md` wins.

---

## 1. Philosophy

LCATS is a research-grade system for:
- Narrative intelligence
- Case-based reasoning (CBR)
- Retrieval-augmented generation (RAG)

The system must prioritize:
- Reproducibility
- Inspectability
- Extensibility
- Conceptual clarity

Guiding rules:
- Explicit > implicit
- Simple > clever
- Deterministic > stochastic (in tests)
- Data-first design

---

## 2. Repository Structure

```
<root>/
├── corpora/        # DATA ONLY (no code)
├── experiments/    # Experimental pipelines (non-production)
├── lcats/          # EXECUTION ROOT
│   ├── lcats/      # Python package (import root)
│   ├── tests/
│   ├── scripts/
│   ├── tools/
│   ├── notebooks/
│   ├── output/
│   └── ...
```

Key rules:
- `<root>/lcats` = execution + tooling layer
- `<root>/lcats/lcats` = importable module
- No code in `corpora/` or `experiments/`

---

## 3. Imports

Always import modules, not symbols, and access functionality via the module namespace.

Preferred forms:
- Standard library: `import pathlib`
- LCATS modules: `from lcats.utils import names`

GOOD:
```python
import pathlib
from lcats.utils import names

config_path = pathlib.Path("config.yaml")
normalized = names.normalize(config_path.stem)
```

BAD:
```python
import pathlib as pl
from lcats.utils.names import normalize
import lcats.utils.names as n

config_path = pl.Path("config.yaml")
normalized = normalize(config_path.stem)
```

Use nested package imports in module form rather than symbol imports.

### 3.2 Human-Oriented Examples (Imports)

The examples above are normative examples for day-to-day import choices and are intended to make the import policy easier to apply during code review.

---

## 3.1 Aliases

Aliases should be avoided unless:
- Widely accepted (`np`, `pd`)
- Resolving name conflicts
- Necessary for readability when names are unusually long

Do not alias LCATS modules arbitrarily.

GOOD:
```python
import numpy as np
import pandas as pd
from lcats.retrieval import ranking
from lcats.retrieval import ranking as case_ranking  # collision/readability case
```

BAD:
```python
from lcats.retrieval import ranking as r
from lcats.utils import names as n
```

---

## 4. Code Design

### Functions
- Single responsibility
- Prefer pure functions
- Avoid hidden state

### Naming
- snake_case (functions)
- PascalCase (classes)
- UPPER_CASE (constants)

### Python Baseline Conventions
- Use 4 spaces for indentation
- Keep lines roughly within 80–100 characters where practical
- Use explicit imports; avoid wildcard imports
- Add type annotations when they improve clarity
- When modifying existing files, preserve local style and existing comments unless a change is intentional and justified

---

## 5. Data & Schemas

All core data must be:
- JSON-serializable
- Schema-consistent
- Human-readable

Preferred:
- JSON (primary)
- YAML (configs)

Future:
- JSON Schema or Pydantic strongly recommended

---

## 6. Encoding

Always use UTF-8:

```python
open(path, "r", encoding="utf-8")
```

---

## 7. Logging & Progress

- Use `logging`, not print
- Use `tqdm` for long loops

---

## 8. Testing

Framework: unittest ONLY

Run:
```bash
python -m unittest discover -s tests -p "*_test.py"
```

Rules:
- Deterministic tests only
- No network calls (unless mocked)
- Avoid printing or use the lcats.utils.capture library to suppress output
- Mirror package structure - test sample_module in sample_module_tests
- Mocking is allowed, but prefer testing behavior through upstream objects with stubbed internals rather than mocking the exact method under test

GOOD:
```python
import unittest


class TestMath(unittest.TestCase):
    def test_add(self):
        calc = Calculator()
        self.assertEqual(calc.add(2, 3), 5)
```

BAD:
```python
import unittest
from unittest.mock import patch


class TestMath(unittest.TestCase):
    @patch("lcats.math.Calculator.add", return_value=5)
    def test_add(self, mock_add):
        self.assertEqual(mock_add(2, 3), 5)
```

---

## 9. Scripts

Location:
```
<root>/lcats/scripts
```

Rules:
- Thin wrappers only
- No core logic
- Must support:
  - --help
  - --check
  - --dry-run

---

## 10. Formatting & Linting

Formatting and linting are governed by:
- `scripts/format` (Black)
- `scripts/lint` (Ruff)

Editors must conform to project configuration.

CI must enforce:
- formatting clean
- lint clean

### 10.1 Human-Oriented Examples (Formatting and Readability)

When editing existing files, minimize unnecessary churn:
- Keep functional changes and style-only changes separate when feasible
- Follow the existing file/module style while editing
- Do not reformat an entire file unless required for the task
- Preserve existing comments when revising nearby code
- New code should match surrounding style

Example (style continuity):

GOOD:
```python
# Existing code style: single quotes
name = 'Alice'

# New code follows the same style
city = 'Paris'
```

BAD:
```python
# Existing code style: single quotes
name = 'Alice'

# New code mixes styles without need
city = "Paris"
```

Spacing/readability examples (tooling remains authoritative):

GOOD:
```python
result = (a + b) * (c - d)
items = [1, 2, 3, 4]

if value == 42:
    print("Answer found!")
```

BAD:
```python
result=(a+b)*(c-d)
items=[1,2,3,4]

if(value==42):print("Answer found!")
```

---

## 11. Determinism

Required:
- Seed randomness
- Stable ordering
- No time-dependent outputs

---

## 12. Dependencies

- Minimal
- Declared in pyproject.toml
- Prefer stable libraries

---

## 13. Narrative Alignment (CRITICAL)

Code must reflect narrative structure:
- scenes
- sequences
- cases

Avoid:
- opaque pipelines
- uninspectable transformations

---

## 14. Documentation

Use Google-style docstrings for non-trivial public functions.
One-line docstrings are acceptable for trivial functions.
For Google-style docstrings, use sections such as `Args`, `Returns`, and `Raises` when applicable.

GOOD:
```python
def add(a: int, b: int) -> int:
    """Adds two integers.

    Args:
        a: First integer.
        b: Second integer.

    Returns:
        Sum of a and b.
    """
    return a + b
```

Also good for trivial functions:
```python
def is_even(value: int) -> bool:
    """Return True when value is even."""
    return value % 2 == 0
```

BAD:
```python
def add(a, b):
    # Adds two numbers
    return a + b
```

---

## 15. CI / PR Rules

All PRs must:
- Pass tests
- Pass lint/format
- Not break scripts
- Avoid regressions

---

## 16. Editor Contract (IMPORTANT)

All contributors must:
- Respect module import rules
- Preserve structure boundaries
- Avoid introducing hidden coupling

---

## 17. RAG / CBR Conventions

Pipelines should follow:

gather → extract → index → retrieve → adapt → evaluate

Each stage must:
- Be testable
- Be inspectable
- Emit intermediate artifacts

---

## 18. Future Extensions

Recommended:
- Schema validation (Pydantic)
- Evaluation benchmarks
- Dataset versioning
- Experiment tracking

---

## 19. For Agents / LLM Assistants

When generating or editing code for LCATS, apply rules in this order:

1. Local LCATS rules in this file
2. Existing project/tooling constraints (`scripts/format`, `scripts/lint`, existing module style)
3. Google Python Style guidance when a local rule does not specify behavior
4. PEP 8 only as fallback when neither local rules nor Google guidance cover the case

Agent operating rules:
- Prefer drop-in-ready code with minimal disruption to the edited file
- Preserve existing comments and nearby code style unless intentionally changing style
- Do not invent new style rules not documented here
- Keep functional changes separate from style-only changes when possible
- Follow LCATS import policy (`import module` / `from package import module`, not symbol imports)
- Use `unittest` for tests and avoid over-mocking the exact behavior under test

---

## Summary

LCATS is both:
- a software system
- a research instrument

This style guide enforces:
- clarity
- reproducibility
- structural rigor
