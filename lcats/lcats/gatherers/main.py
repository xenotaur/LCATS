"""Runs the extractors we have."""

import lcats.gatherers.sherlock.gatherer as sherlock
import lcats.gatherers.lovecraft.gatherer as lovecraft
import lcats.gatherers.ohenry.gatherer as ohenry
import lcats.gatherers.hemingway.gatherer as hemingway
import lcats.gatherers.wodehouse.gatherer as wodehouse
import lcats.gatherers.wilde_happy_prince.gatherer as wilde_happy_prince
import lcats.gatherers.grimm.gatherer as grimm
import lcats.gatherers.anderson.gatherer as anderson
import lcats.gatherers.chesterton.gatherer as chesterton
import lcats.gatherers.london.gatherer as london
import lcats.gatherers.mass_quantities.gatherer as mass_quantities


GATHERERS = {
    "sherlock": sherlock,
    "lovecraft": lovecraft,
    "ohenry": ohenry,
    "hemingway": hemingway,
    "wilde_happy_prince": wilde_happy_prince,
    "wodehouse": wodehouse,
    "grimm": grimm,
    "anderson": anderson,
    "chesterton": chesterton,
    "london": london,
    "mass_quantities": mass_quantities,
}


def run(gatherers="ALL", dry_run=False):
    """Run the gatherers."""
    if gatherers == "ALL":
        gatherers = list(GATHERERS.keys())

    print("Gathering data from the corpus.")
    print(f"Gatherers to run: {', '.join(gatherers)}")
    for gatherer in gatherers:
        if gatherer not in GATHERERS:
            print(f"Unknown gatherer: {gatherer}")
            continue
        print(f"Running gatherer: {gatherer}")
        if dry_run:
            print(f"Dry run: would run {gatherer}.gather()")
        else:
            GATHERERS[gatherer].gather()

    return "Gathering complete.", 0


if __name__ == '__main__':
    run()
