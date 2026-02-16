# Python Coding Style Guide

This document summarizes our team’s coding style rules.
They are based on the **Google Python Style Guide**, with fallbacks to **PEP 8**, plus our own **local rules** which take precedence.

---

## 📖 For Human Developers

### Order of Precedence

1. **Local Team Rules** (highest priority).
2. **Google Python Style Guide** — [https://google.github.io/styleguide/pyguide.html](https://google.github.io/styleguide/pyguide.html).
3. **PEP 8** — [https://peps.python.org/pep-0008/](https://peps.python.org/pep-0008/) (fallback only).

---

### Local Rules (Overrides)

#### Imports

* Prefer entire modules:

  ```python
  import pathlib
  from project.submodule import tools
  ```
* Avoid aliases, except:

  * Standard: `import numpy as np`, `import pandas as pd`.
  * Name collisions: `import module_conflict as mc`.
  * Very long names: `import very_long_package_name as vlpn`.
* For nested packages:

  ```python
  from top.level import lower
  ```

  instead of aliasing.

**Good:**

```python
import pathlib
from data.loader import fetch
```

**Bad:**

```python
import pathlib as pl
import data.loader as loader
```

#### Unit Tests

* Use **unittest** as the default framework.
* Mocking is allowed, but **prefer upstream objects with stubbed/mocked internals** over faking entire outputs.

**Good:**

```python
class TestMath(unittest.TestCase):
    def test_add(self):
        calc = Calculator()
        self.assertEqual(calc.add(2, 3), 5)
```

**Bad:**

```python
class TestMath(unittest.TestCase):
    @patch("Calculator.add", return_value=5)
    def test_add(self, mock_add):
        self.assertEqual(mock_add(2, 3), 5)
```

#### Code Formatting & Changes

* Apply the **default VSCode formatter** before check-in.
* Keep **functional changes** and **style-only changes** in separate commits.
* When editing existing code, **follow the current module’s style**; do not reformat the entire file just to make functional changes unless absolutely necessary. Add new code in the style of the file or directory.
* Preserve **existing comments** when making revisions.

**Good:**

```python
# Existing code style: single quotes
name = 'Alice'

# New code follows the same style
city = 'Paris'
```

**Bad:**

```python
# Existing code style: single quotes
name = 'Alice'

# New code mixes styles unnecessarily
city = "Paris"
```

#### Docstrings

* Use Google-style docstrings with `Args`, `Returns`, `Raises`.
* Exception: short, obvious functions may use a one-line docstring.

**Good:**

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

**Bad:**

```python
def add(a, b):
    # Adds two numbers
    return a + b
```

#### Spacing and Line Length

* Use 4 spaces per indentation level.
* Keep line length to **80–100 characters**.
* Add spaces around operators and after commas, but not before parentheses.

**Good:**

```python
result = (a + b) * (c - d)
items = [1, 2, 3, 4]

if value == 42:
    print("Answer found!")
```

**Bad:**

```python
result=(a+b)*(c-d)
items=[1,2,3,4]

if(value==42):print("Answer found!")
```

---

### Google Style (Baseline)

* Explicit imports > wildcards.
* Triple-quoted docstrings.
* Type annotations encouraged.
* 4 spaces per indent, 80–100 character lines.

### PEP 8 (Fallbacks)

* Import grouping: stdlib → third-party → local.
* Blank lines, spacing, and other general formatting rules.

---

## 🤖 For Language Models (LLM Assistants)

When generating Python code, follow these rules **in order of precedence**:

1. **Local Rules:**

   * Imports: `import module` or `from top.level import lower`. No aliases except `numpy as np`, `pandas as pd`, conflict resolution, or very long names.
   * Unit tests: use `unittest`; mocks allowed but prefer upstream objects with stubbed internals.
   * Formatting: assume VSCode default; separate style vs. functional changes; follow the module’s existing style; preserve comments.
   * Docstrings: Google-style (`Args`, `Returns`, `Raises`), except one-line for trivial functions.
   * Spacing and line length: 4 spaces indentation, 80–100 char lines, spaces around operators and commas.

2. **Google Python Style Guide** (when not covered by local rules).

3. **PEP 8** (fallback only).

**Always generate code that can be dropped directly into existing files** with minimal disruption and consistent style.

---
