"""Runs the extractors we have."""

import lcats.gatherers.sherlock.gutenberg as sherlock
import lcats.gatherers.lovecraft.gutenberg as lovecraft
import lcats.gatherers.ohenry.gutenberg as ohenry
import lcats.gatherers.hemingway.gutenberg as hemingway
import lcats.gatherers.wodehouse.gutenberg as wodehouse
import lcats.gatherers.wilde_happy_prince.gutenberg as wilde_happy_prince
import lcats.gatherers.grimm.gutenberg as grimm
import lcats.gatherers.anderson.gutenberg as anderson
import lcats.gatherers.chesterton.gutenberg as chesterton
import lcats.gatherers.london.gutenberg as london
import lcats.gatherers.massQuantities.gutenberg1 as massQuantities

def run(dry_run=False):
    if not dry_run:
        print("Gathering data from the corpus.")
        print(sherlock.gather())
        print(lovecraft.gather())
        print(ohenry.gather())
        print(hemingway.gather())
        print(wilde_happy_prince.gather())
        print(wodehouse.gather())
        print(grimm.gather())
        print(anderson.gather())
        print(chesterton.gather())
        print(london.gather())
        print(massQuantities.gather())

        
    return "Gathering complete.", 0


if __name__ == '__main__':
    run()
