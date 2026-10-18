"""Explicit Gutenberg CI maintenance; run from lcats/ with the project installed.

See `python tools/gettenberg_ci.py --help`. Preview is the default; --apply may
access Gutenberg or delete GitHub caches. No credentials are stored in outputs.
Catalog commands write only the supplied cache directory; cache deletion is
limited to one documented namespace/ref. Failures exit nonzero. The workflow
and docs/how-to/gettenberg-ci-maintenance.md describe inputs and cache retention.
"""

from lcats.dev import gettenberg_ci


if __name__ == "__main__":
    raise SystemExit(gettenberg_ci.main())
