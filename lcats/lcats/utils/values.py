"""Utility functions for processing transformations of values."""

from typing import Any, Iterable, Mapping, Optional, Set, Union


def strings_from_sql(rows: Iterable[Mapping[str, Any] | tuple]) -> Set[str]:
    """Normalize sqlite rows (tuple or dict) to a set of string values."""
    out: Set[str] = set()
    for r in rows:
        if isinstance(r, (tuple, list)):
            if r and r[0] is not None:
                out.add(str(r[0]))
        else:
            v = r.get("v")
            if v is not None:
                out.add(str(v))
    return out


def strings_as_list(x: Optional[Union[str, Iterable[str]]]) -> Optional[list]:
    """Convert a string or iterable of strings to a list of strings, or None."""
    if x is None:
        return None
    if isinstance(x, (list, tuple, set)):
        return list(x)
    return [str(x)]
