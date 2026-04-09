# LCATS STYLE GUIDE (Expanded)

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

Always import modules, never symbols:

GOOD:
```python
import lcats.utils.names as names
```

BAD:
```python
from lcats.utils.names import url_to_filename
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

Tools:
- black
- ruff

Commands:
```bash
scripts/format
scripts/lint --fix
```

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

All public functions require docstrings:

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
