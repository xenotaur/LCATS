"""Pure analysis functions over genre-count data, independent of rendering."""


def sorted_counts(counts: dict) -> list[tuple[str, int]]:
    """Return (label, count) pairs sorted by count descending, then label."""
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def counts_with_no_signal(counts: dict, no_usable_signal_count: int) -> dict:
    """Return a copy of counts with an explicit "no usable signal" category."""
    result = dict(counts)
    if no_usable_signal_count:
        result["no usable signal"] = no_usable_signal_count
    return result


def total_count(counts: dict) -> int:
    """Sum every count in the mapping."""
    return sum(counts.values())
