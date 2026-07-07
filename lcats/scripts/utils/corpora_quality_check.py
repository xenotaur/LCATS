#!/usr/bin/env python
from lcats.analysis import corpus_survey


def main() -> int:
    """Thin wrapper that delegates to the library implementation."""
    return corpus_survey.main()


if __name__ == "__main__":
    raise SystemExit(main())
