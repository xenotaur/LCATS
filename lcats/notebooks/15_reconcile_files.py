"""Read-only command-line companion to notebook 15.

Run from lcats/: python notebooks/15_reconcile_files.py LEFT RIGHT
Both arguments are collection directories with bucket/story.json files. Prints
JSON to stdout; redirect explicitly to retain results. No catalog/network/write
access is used. Invalid input raises an exception and exits nonzero.
"""

import argparse
import json

from lcats.analysis.corpus import reconciliation


def main(argv=None):
    """Compare explicitly selected directories and print the structured result."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left")
    parser.add_argument("right")
    args = parser.parse_args(argv)
    print(
        json.dumps(reconciliation.compare_collections(args.left, args.right), indent=2)
    )


if __name__ == "__main__":
    main()
