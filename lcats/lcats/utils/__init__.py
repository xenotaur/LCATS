# lcats/utils/__init__.py
from __future__ import annotations
import warnings

# Re-export the legacy utils API so `import lcats.utils` keeps working.
# Everything that used to live in utils.py now lives in compat.py.
from .compat import *  # noqa: F401,F403  (intentionally re-export full legacy surface)

# Optionally, nudge users toward the new submodules (one-time warning per process)
warnings.warn(
    "lcats.utils is now a package. Legacy utilities are still available via "
    "`import lcats.utils`, but consider importing specific submodules, e.g. "
    "`from lcats.utils import names`.",
    category=DeprecationWarning,
    stacklevel=2,
)

# Explicitly expose submodules on the package so `from lcats.utils import names` works.
from . import names  # now accessible as lcats.utils.names

# Keep a tidy __all__: legacy names + submodule handles you want importable
try:
    from .compat import __all__ as _legacy_all
except Exception:
    _legacy_all = []

__all__ = list(_legacy_all) + ["names"]
