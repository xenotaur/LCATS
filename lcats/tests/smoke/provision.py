"""Explicit network-enabled Stanza smoke setup; never imported by tests.

Run after installing tests/smoke/requirements.txt in a dedicated environment.
Only the processors used by LCATS (and their model dependencies) are fetched.
The CI step timeout bounds downloads; inference is a separate offline command.
"""

import argparse
import json

from tests.smoke import resources


def main():
    """Provision the pinned Stanza resource release into the explicit directory."""
    argparse.ArgumentParser(description=__doc__).parse_args()
    spec = resources.manifest()
    root = resources.model_dir()
    import stanza

    stanza.download(
        "en",
        model_dir=str(root),
        processors="tokenize,pos,lemma,depparse",
        resources_version=spec["stanza_resources_version"],
        resources_url="https://raw.githubusercontent.com/stanfordnlp/stanza-resources/"
        + spec["stanza_resources_commit"],
    )
    print(json.dumps(resources.check("stanza"), indent=2))
    print(json.dumps(resources.check("spacy"), indent=2))


if __name__ == "__main__":
    main()
