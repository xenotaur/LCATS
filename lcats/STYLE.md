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

GOOD:
```python
from lcats.utils import names
names.normalize(...)
```

BAD:
```python
from lcats.utils.names import normalize
```

---

## 3.1 Aliases

Aliases should be avoided unless:
- Widely accepted (`np`, `pd`)
- Resolving name conflicts
- Necessary for readability

Do not alias LCATS modules arbitrarily.

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
- Mirror package structure

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

```python
def func(x):
    """Short description.

    Args:
        x (int): description

    Returns:
        int
    """
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

## Summary

LCATS is both:
- a software system
- a research instrument

This style guide enforces:
- clarity
- reproducibility
- structural rigor
