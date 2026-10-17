"""Read-only genre example using one explicitly supplied gettenberg catalog.

Run from lcats/: python KMo/genre.py CATALOG_SQLITE CORPUS_ROOT
The catalog must already exist (see lcats catalog setup). This script performs no
setup, network requests, or corpus writes. It prints genre counts; invalid input
raises an exception and exits nonzero. Classification rules live in utils.genre.
"""

import argparse
import collections
import json

from lcats import stories
from lcats.gettenberg import catalog
from lcats.utils import genre


def main(argv=None):
    """Classify a local corpus using the selected read-only catalog file."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("catalog")
    parser.add_argument("corpus")
    args = parser.parse_args(argv)
    corpus = stories.Corpora(args.corpus)
    with catalog.Catalog(args.catalog) as library:
        counts = collections.Counter(
            genre.get_genre_for_story(story, catalog=library)
            for story in corpus.stories
        )
    print(json.dumps(dict(sorted(counts.items())), indent=2))


if __name__ == "__main__":
    main()
