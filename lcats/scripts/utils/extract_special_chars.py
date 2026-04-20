#!/usr/bin/env python3
"""Legacy wrapper that delegates to lcats.analysis.corpus.specials_cli."""

from lcats.analysis.corpus import specials_cli


def main(argv=None) -> int:
    """Run special-character extraction through the canonical CLI module."""
    return specials_cli.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
