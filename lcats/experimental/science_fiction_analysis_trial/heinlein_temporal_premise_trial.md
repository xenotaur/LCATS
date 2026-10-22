# Premise-first trial on six control stories for the temporal-reference design

Work item: WI-SF-0123. This is the evidence file cited by
`project/design/proposals/proposed/heinlein-temporal-reference/00_proposal.md`.

## What this is, and what it is not

A hand classification of the plot-relevant factual premises of the six stories used as
Heinlein controls in WI-SF-0119, made by one rater (Claude) from a full read of each story in
`corpora/`. No model was called. It is **not** a measurement of any detector and **not** a
sample of the corpus: the six stories were chosen as controls (two realist negatives, a
fairy-tale negative, three science-fiction positives), so the proportions below say nothing
about how often dates matter overall. The classification has not been checked by a second
rater or the owner.

The vocabulary is the one the proposal defines. Each premise has a materiality (`central`,
`substantial`, `incidental`, as in `src/lcats/analysis/science_fiction/models.py:49-55`), a
`novel_at_composition` value (`true`, `false` or `unknown`: is the claim new relative to the author's world), and a
**standing timeline**: periods in which the claim was `supported`, `open` (speculative but not
contradicted), `contested`, or `contradicted`. From the timeline the proposal derives the
plausibility of the premise at composition and today, and an outcome relation (`stable`,
`still_open`, `realized`, `falsified`, `not_assessable`). A dated prediction whose date has
passed also carries a separate `calendar_expired` flag, which Python derives from the date. A
*speculative* premise is a counted premise that is novel at composition or whose standing is not
`supported` at some date in the interval.

## Composition dates and their sources

| Story | First published | Source and strength | Author | Interval used |
|---|---|---|---|---|
| Bell (Andersen) | May 1845 | [Andersen Centre register](https://andersen.sdu.dk/vaerk/register/info_e.html?vid=76); a search-result summary, not opened by me | 1805-1875 | 1845 |
| 2 B R 0 2 B (Vonnegut) | January 1962 | [Wikipedia](https://en.wikipedia.org/wiki/2_B_R_0_2_B); I opened this page and it states the month | 1922-2007 | up to January 1962 |
| A Bad Day for Sales (Leiber) | July 1953 | [a story review that states "First published in the July 1953 issue of Galaxy Science Fiction"](https://sffremembrance.com/2025/03/11/short-story-review-a-bad-day-for-sales-by-fritz-leiber/); other search results agree, and I opened only this one | 1910-1992 | 1953 |
| A Case of Sunburn (Fontenay) | April 1957, IF | [Internet Archive scan of the issue](https://archive.org/details/1957-04_IF); the page lists the story and attributes its contents to ISFDB, which I did not open | 1917-2007; first story 1954, from a search-result summary of the [SF Encyclopedia](https://www.sf-encyclopedia.com/entry/fontenay_charles_l) (the page itself returned HTTP 429 and was not opened) | 1957 |
| The Blue Cross (Chesterton) | 23 July 1910, Saturday Evening Post | [Wikipedia, Father Brown](https://en.wikipedia.org/wiki/Father_Brown); I opened this page and it states the date and the first title, "Valentin Follows a Curious Trail"; a search result gave June 1910 for the same appearance | 1874-1936 | 1910 |
| Brown Wolf (London) | **not confirmed** | One reprint listing says Everybody's Magazine with no date; the story is in a collection a search result dates to 1906; the story's own text sets it about 1901 (offsets below) | 1876-1916 | about 1901 to 1906, an inference |

The corpus records the year as "Unknown" for these stories (`src/lcats/gatherers/parser.py:1457`).
For Sunburn the author's lifespan alone does not help: with only the career window
(1954-2007) the interval straddles the 1965 flip below, and only the publication source
resolves it.

## Per-story premises

Offsets are 0-based character offsets into the `body` field of each `story.json`; the
script in the last section finds each quote and reports them. "Written" is the plausibility of
the premise over the composition interval; "today" is its plausibility on the analysis date.

### Bell (Andersen)

| Premise (offset) | Materiality | Novel | Standing timeline | Written / today / relation | Notes |
|---|---|---|---|---|---|
| An unexplained bell sound draws the townspeople; a character reports an owl, a child says the bell "does not exist" (2534, 4816) | central | n/a | not treated as a factual premise | n/a | judgment call: an allegorical, unexplained phenomenon makes no testable claim |
| Apes that speak and threaten the prince (8630) | incidental | unknown | contradicted at every date | absent / absent / stable | not counted; novelty is unknown because a folktale presents such elements as ordinary |
| Apples that look like soap bubbles (9046) | incidental | unknown | decorative | n/a | not counted |
| A holy bell and blessed spirits at the climax (11656) | substantial | unknown | contradicted at every date (judgment call) | absent / absent / stable | counted; judgment call: treated as contradicted because the story offers no natural account of it |

Plausibility as written: `absent`; today: `absent`; a date is not needed. `calendar_expired`:
none. Speculative premises: yes, because the counted supernatural element has a `contradicted`
standing (its novelty is `unknown`, a judgment call: a folktale presents such elements as
ordinary, so they are not clearly new relative to the author's world). `different` as written: `ambiguous`,
and with plausibility `absent` the verdict is `does_not_qualify`.

### 2 B R 0 2 B (Vonnegut)

| Premise (offset) | Materiality | Novel | Standing timeline | Written / today / relation | Notes |
|---|---|---|---|---|---|
| Aging and all diseases cured (120) | central | yes | open at every date | present / present / still_open | |
| US population stabilized at forty million, average age 129 (226) | substantial | yes | open at every date | present / present / still_open | |
| A birth requires a volunteer death by law (8832) | central | yes | open at every date | present / present / still_open | |
| The "good old days" when the Earth had twenty billion people, heading to forty, eighty and one hundred and sixty billion (10430) | substantial | no | open: a projection when written and not yet reached | present / present / still_open | the story gives no year for the twenty billion |
| "In the year 2000", before scientists stepped in, there was not enough drinking water and nothing to eat but seaweed (11011) | substantial | no | open until 2000; contradicted afterwards | present / absent (excluded) / falsified | `calendar_expired` true; judgment calls: the sentence is partly counterfactual ("before scientists stepped in"), and the premise could be `incidental` |

Counted premises are present at composition and, with the calendar-expired sentence excluded,
today. Plausibility as written: `present`; today: `present`. A date is not needed beyond the
upper bound. Speculative premises: yes. The world population passed six billion near 1999
(the UN designated 12 October 1999 as the
[Day of 6 Billion](https://press.un.org/en/1999/19990920.pop738.html)), so the year-2000
sentence is not how the year turned out.

### A Bad Day for Sales (Leiber)

| Premise (offset) | Materiality | Novel | Standing timeline | Written / today / relation | Notes |
|---|---|---|---|---|---|
| A mobile sales robot (823) | central | yes | open | present / present / still_open | judgment call: mobile sales and delivery robots now exist, so "partly realized" is arguable |
| A missile strike on Manhattan, a "Hot Truce" (338, 8221, 8789) | central | yes | open; undated | present / present / still_open | no stated date, so not calendar-expired |
| Weather-controlled air (7896) | incidental | yes | open | present / present / still_open | not counted |
| Advertising copy about a Martian sunrise (6900) | incidental | no | advertising copy, not a claim of a settled Mars | n/a | not counted |

Plausibility as written: `present`; today: `present`; no date needed. Speculative premises:
yes.

### A Case of Sunburn (Fontenay)

| Premise (offset) | Materiality | Novel | Standing timeline | Written / today / relation | Notes |
|---|---|---|---|---|---|
| Mars has a protective blue mist that shields the surface from the sun (932, 34221) | central | yes | open until July 1965; contested from the first close-up images by Mariner 4 on [15 July 1965](https://nssdc.gsfc.nasa.gov/imgcat/html/object_page/m04_01d.html); contradicted today (my reading of the Mariner results, not sourced beyond the flyby date) | present if composed before July 1965 / absent / falsified once the interval is known | the end of the contested period is not verified; that the premise was not contradicted in 1957 is my reading and is not checked against 1950s sources |
| The captured station "amplifies the magnetic field of Mars" (4812) | central | yes | open until July 1965; contested afterwards: search-result summaries of NASA pages say Mariner 4 found no detectable field, that this was not conclusively determined, and that Mars is now accepted to be essentially without an intrinsic field of any significance | present if before July 1965 / absent / falsified once the interval is known | the NASA pages were not opened |
| Earth's magnetic field interferes with the mist, and the station amplifies fields (34671) | central | yes | an invented mechanism that depends on the two premises above | follows them | the "contrary new theory" case in the rubric text |
| A settled Mars with dome cities, canals and green lowlands (29401) | substantial | yes | same timeline as the mist | present if before July 1965 / absent / falsified once the interval is known | |
| Mars colony founded in 1985, story dated June 2020 (12152, 11642) | substantial | yes | a dated prediction | present / absent (excluded) / falsified | `calendar_expired` true; a dated prediction, so the relation needs no interval |
| Gravity boats, heat guns, spaceships | incidental | yes | open | n/a | not counted |

Plausibility as written: `present` if composed before July 1965 (it was published in April
1957); `ambiguous` with that condition if only the career window were known. Today: `absent`
(the calendar-expired claim is excluded). A date is needed. Speculative premises: yes.

### The Blue Cross (Chesterton)

| Premise (offset) | Materiality | Novel | Standing timeline | Written / today / relation | Notes |
|---|---|---|---|---|---|
| The setting is London during the Eucharistic Congress (1459) | substantial | no | supported; contemporary to the author | present / present / stable | the text gives no year; the congress was held in London on 9 to 13 September 1908 (from a search-result summary, not opened), which is an inference from outside the text |
| A thief's tricks: messages photographed on microscope slides, a portable pillar-box (3276, 3598) | incidental | no | supported; tricks, not speculative science | n/a | a model could mistake a "portable pillar-box" for an invention; not counted |
| An argument that reason is supreme (35779) | incidental | no | an argument, not a premise about the world | n/a | |

No speculative premises: every counted premise is supported and none is novel, so the flag is false
and plausibility as written is `present` (the counted premise is supported). The keyword scan in the script finds `invent`, `machine` and
`scien`: `invent` is the pillar-box trick above, `machine` is a philosophical phrase ("a
thinking machine"), and `scien` occurs in "nescience" and "conscientiously". As written,
`different` is absent: the story is set in its author's present. Read against today, 1900s
London differs from here-and-now.

### Brown Wolf (London)

| Premise (offset) | Materiality | Novel | Standing timeline | Written / today / relation | Notes |
|---|---|---|---|---|---|
| A dog travels up to 150 miles a day to return north (7441, 6929) | substantial | no | supported, strained | present / present / stable | judgment call: an exaggeration, not an established-fact violation |
| The dog is a Klondike dog (15924) | incidental | no | a neighbor's claim | n/a | |
| Setting: California about 1901, with a mail contract and a Klondike past (22116, 22456) | substantial | no | supported; contemporary to the author | present / present / stable | |

No speculative premises: the speculative-premises flag is false and plausibility as written is
`present` (the counted premises are supported). The keyword
scan finds one hit, a simile about "a traveller from another planet". As written, `different`
is absent. Read against today, the setting is a past era.

## Results

| Story | Date-sensitive counted premise | Calendar-expired claim | Plausibility as written | Plausibility today | Date needed |
|---|---|---|---|---|---|
| Bell | no | no | absent | absent | no |
| 2 B R 0 2 B | no | yes (year 2000) | present | present (expired sentence excluded) | no |
| A Bad Day for Sales | no | no | present | present | no |
| A Case of Sunburn | yes (Mars) | yes (1985, 2020) | present if before July 1965 | absent | yes |
| The Blue Cross | no | no | present (no speculative premises) | present | no |
| Brown Wolf | no | no | present (no speculative premises) | present | no |

One of six stories needs a date for its physical premises; two carry calendar-expired claims;
two realist stories show the same author-versus-reader time problem for the `different`
condition. This is six hand-picked controls by one rater and does not estimate how often dates
matter in the corpus.

## Judgment calls and limits

- Whether Bell's unexplained bell is a factual premise at all, whether supernatural claims count as contradicted, and whether a folktale's supernatural elements are novel relative to the author's world (recorded as `unknown`).
- Whether the Vonnegut year-2000 sentence is `substantial` or `incidental`, and how to treat its counterfactual wording.
- Whether Leiber's robot is `still_open` or partly realized.
- Whether Sunburn's mist was contradicted by knowledge available in 1957 (not checked against 1950s sources), and the end of the contested period for the mist and the magnetic field.
- Whether Brown Wolf's travel speed is an exaggeration or a violation.
- Brown Wolf's first appearance is unconfirmed; the Andersen and Brown Wolf collection dates, the Mars magnetic-field result, and the 1908 congress come from search-result summaries that I did not open; I did not open ISFDB.
- One rater, no second check, and six hand-picked stories.

## Reproduction

Run from the `lcats/` project root with the corpora directory in `CORPORA_ROOT` (default
`corpora`); it needs only the Python standard library. It finds each quoted passage with
flexible whitespace, reports its offset, and prints the keyword scan for the two realist
stories.

```python
import json
import os
import re

ROOT = os.environ.get("CORPORA_ROOT", "corpora")

CITES = {
    "anderson/bell": [
        "the sound proceeded from a very large owl",
        "In reality the bell does not exist",
        "The ugly apes sat upon the trees, and grinned",
        "apples of which looked exactly like large soapbubbles",
        "blessed spirits floated around them",
    ],
    "mass_quantities/2_b_r_0_2_b__vonnegut": [
        "All diseases were conquered. So was old age.",
        "The population of the United States was stabilized at forty-million souls.",
        "the population of the Earth was twenty billion",
        "before scientists stepped in and laid down the law",
        "no newborn child could survive unless the parents of the child could find someone who would volunteer to die",
    ],
    "mass_quantities/a_bad_day_for_sales__leiber": [
        "Robie was the logical conclusion of the development of vending machines",
        "the latest news about the Hot Truce",
        "plunged down at better than three miles a second",
        "weather-controlled air",
        "the passionate claws of a Martian sunrise",
        "the silver-green bud bloomed above Manhattan",
    ],
    "mass_quantities/a_case_of_sunburn__fontenay": [
        "the blue mist of Mars was beginning to settle toward the ground",
        "the first Martian colony was established at Mars City in the Earth year 1985",
        "the Earth date, June 1, 2020",
        "the dark green areas of Syrtis and Hadriacum were plainly visible",
        "only the blue mist of Mars protects its surface from the hard rays of the sun",
        "an experimental laboratory that amplifies the magnetic field of Mars",
        "It's the Earth's magnetic field, not that of Mars, that interferes with the blue mist",
    ],
    "chesterton/blue_cross": [
        "the Eucharistic Congress, then taking place in London",
        "he invented a portable pillar-box",
        "photographing his messages infinitesimally small upon the slides of a microscope",
        "reason is always reasonable",
    ],
    "london/brown_wolf": [
        "In 1898 I refused five thousand dollars",
        "lookin' for 'm for three years",
        "cover as high as a hundred and fifty miles",
        "The homing instinct, Irvine called it",
        "He's a Klondike dog",
    ],
}

SCAN = r"invent|machine|robot|future|scien|electric|telephone|rocket|planet|atom"


def body(story):
    with open(f"{ROOT}/{story}/story.json") as handle:
        return json.load(handle)["body"]


def locate(text, quote):
    # Whitespace in the corpus bodies includes line breaks and indentation,
    # and some apostrophes are typographic, so match words with flexible
    # whitespace and either apostrophe.
    words = [re.escape(word).replace("'", "['’]") for word in quote.split()]
    match = re.search(r"\s+".join(words), text)
    return None if match is None else match.start()


for story, quotes in CITES.items():
    text = body(story)
    print(f"== {story} ({len(text)} chars)")
    for quote in quotes:
        offset = locate(text, quote)
        print("  ", "MISSING" if offset is None else f"offset {offset}", "|", quote[:70].rstrip())
    if story in ("chesterton/blue_cross", "london/brown_wolf"):
        hits = sorted({m.group(0).lower() for m in re.finditer(SCAN, text, re.I)})
        print("   keyword scan hits:", hits)
```

Output as of this commit:

```text
== anderson/bell (11762 chars)
   offset 2534 | the sound proceeded from a very large owl
   offset 4816 | In reality the bell does not exist
   offset 8630 | The ugly apes sat upon the trees, and grinned
   offset 9046 | apples of which looked exactly like large soapbubbles
   offset 11656 | blessed spirits floated around them
== mass_quantities/2_b_r_0_2_b__vonnegut (14409 chars)
   offset 120 | All diseases were conquered. So was old age.
   offset 226 | The population of the United States was stabilized at forty-million so
   offset 10430 | the population of the Earth was twenty billion
   offset 11011 | before scientists stepped in and laid down the law
   offset 8832 | no newborn child could survive unless the parents of the child could f
== mass_quantities/a_bad_day_for_sales__leiber (13279 chars)
   offset 823 | Robie was the logical conclusion of the development of vending machine
   offset 338 | the latest news about the Hot Truce
   offset 8221 | plunged down at better than three miles a second
   offset 7896 | weather-controlled air
   offset 6900 | the passionate claws of a Martian sunrise
   offset 8789 | the silver-green bud bloomed above Manhattan
== mass_quantities/a_case_of_sunburn__fontenay (35858 chars)
   offset 932 | the blue mist of Mars was beginning to settle toward the ground
   offset 12152 | the first Martian colony was established at Mars City in the Earth yea
   offset 11642 | the Earth date, June 1, 2020
   offset 29401 | the dark green areas of Syrtis and Hadriacum were plainly visible
   offset 34221 | only the blue mist of Mars protects its surface from the hard rays of
   offset 4812 | an experimental laboratory that amplifies the magnetic field of Mars
   offset 34671 | It's the Earth's magnetic field, not that of Mars, that interferes wit
== chesterton/blue_cross (46342 chars)
   offset 1459 | the Eucharistic Congress, then taking place in London
   offset 3598 | he invented a portable pillar-box
   offset 3276 | photographing his messages infinitesimally small upon the slides of a
   offset 35779 | reason is always reasonable
   keyword scan hits: ['invent', 'machine', 'scien']
== london/brown_wolf (31817 chars)
   offset 22116 | In 1898 I refused five thousand dollars
   offset 22456 | lookin' for 'm for three years
   offset 7441 | cover as high as a hundred and fifty miles
   offset 6929 | The homing instinct, Irvine called it
   offset 15924 | He's a Klondike dog
   keyword scan hits: ['planet']
```
