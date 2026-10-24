"""Experiment-only extension of the existing cleaner's terminal-notice grammar.

The production module is loaded into a separate namespace, then ONLY its notice
regular expression is extended. This intentionally tests a minimal private-rule
change without copying the cleaner, modifying the imported production module or
changing extraction. The caller pins the module bytes; this helper alone is not
an approved product policy. See the terminal-notice audit results README.
"""

import importlib.util
import pathlib
import re
import sys

from lcats.gettenberg import cleanup


PATTERN = (
    r"End[ \t]+of[ \t]+(?:Project[ \t]+Gutenberg's[ \t]+|"
    r"the[ \t]+Project[ \t]+Gutenberg[ \t]+EBook[ \t]+of[ \t]+)"
    r"([^ \t].*),[ \t]+by[ \t]+(.+)"
)


def load_candidate():
    """Isolate the candidate; inherit all envelope, title and ambiguity guards.

    The pre-existing rule corroborates the notice title with the end marker and
    requires a nonempty author, not catalog-author equality. This experiment keeps
    that contract exactly. A notice must be the final nonblank physical line before
    the unique accepted end marker. No wrapped notice or general footer heuristic
    is added. Registration is needed by dataclasses during this isolated import.
    """
    name = "gettenberg_terminal_notice_experiment"
    spec = importlib.util.spec_from_file_location(name, pathlib.Path(cleanup.__file__))
    module = importlib.util.module_from_spec(spec)
    previous = sys.modules.get(name)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        if previous is None:
            del sys.modules[name]
        else:
            sys.modules[name] = previous
    module._END_NOTICE = re.compile(PATTERN, re.IGNORECASE | re.ASCII)
    return module
