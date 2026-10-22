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
rater or the owner. The vocabulary is the one proposed in the design: materiality
(`central`, `substantial`, `incidental`, as in `src/lcats/analysis/science_fiction/models.py:49-55`),
a change window (when a fact first became doubtful and when it became settled), an outcome
relation to today (`stable` meaning unchanged between composition and today, whether the
premise held or never did; `still open`; `realized`; `falsified`; `not assessable`), and a
separate `calendar_expired` flag for dated predictions whose date has passed.

## Composition dates and their sources

| Story | First published | Source and strength | Author | Interval used |
|---|---|---|---|---|
| Bell (Andersen) | May 1845 | [Andersen Centre register](https://andersen.sdu.dk/vaerk/register/info_e.html?vid=76); one source | 1805-1875 | 1845 |
| 2 B R 0 2 B (Vonnegut) | January 1962 | [Wikipedia](https://en.wikipedia.org/wiki/2_B_R_0_2_B); I opened this page and it states the month | 1922-2007 | up to January 1962 |
| A Bad Day for Sales (Leiber) | July 1953 | [a story review that states "First published in the July 1953 issue of Galaxy Science Fiction"](https://sffremembrance.com/2025/03/11/short-story-review-a-bad-day-for-sales-by-fritz-leiber/); other search results agree, and I opened only this one | 1910-1992 | 1953 |
| A Case of Sunburn (Fontenay) | April 1957, IF | [Internet Archive scan of the issue, whose contents are excerpted from ISFDB](https://archive.org/details/1957-04_IF) and the Telltale Books author index; the page lists the story and attributes its contents to ISFDB, which I did not open; the Telltale Books index also gives April 1957 but I did not open it | 1917-2007; first story 1954, from a search-result summary of the [SF Encyclopedia](https://www.sf-encyclopedia.com/entry/fontenay_charles_l) (the page itself returned HTTP 429 and was not opened) | 1957 |
| The Blue Cross (Chesterton) | 23 July 1910, Saturday Evening Post | [Wikipedia, Father Brown](https://en.wikipedia.org/wiki/Father_Brown); I opened this page and it states the date and the first title, "Valentin Follows a Curious Trail"; a search result gave June 1910 for the same appearance | 1874-1936 | 1910 |
| Brown Wolf (London) | **not confirmed** | One reprint listing says Everybody's Magazine with no date; the story is in a collection a search result dates to 1906; the story's own text sets it about 1901 (offsets below) | 1876-1916 | about 1901 to 1906, an inference |

The corpus records the year as "Unknown" for these stories (`src/lcats/gatherers/parser.py:1457`).
For Sunburn the author's lifespan alone does not help: with only the career window
(1954-2007) the interval straddles the 1965 flip below, and only the publication source
resolves it.

## Per-story premises

Offsets are 0-based character offsets into the `body` field of each `story.json`; the
script in the last section finds each quote and reports them.

### Bell (Andersen)

| Premise (offset) | Materiality | Stability and window | Outcome to today | Notes |
|---|---|---|---|---|
| An unexplained bell sound draws the townspeople; a character reports an owl, a child says the bell "does not exist" (2534, 4816) | central | no fact claimed; no theory offered | stable | judgment call: an allegorical, unexplained phenomenon is not clearly a factual premise |
| Apes that speak and threaten the prince (8630) | incidental | never established at any date | stable | not counted |
| Apples that look like soap bubbles (9046) | incidental | decorative | stable | not counted |
| A holy bell, blessed spirits at the climax (11656) | substantial | supernatural; never established | stable | counted |

Counted premises: the spirits at the climax are absent at every date. Plausibility as written:
`absent`; today: `absent`; a date is not needed. `calendar_expired`: none. Speculative
premises: yes.

### 2 B R 0 2 B (Vonnegut)

| Premise (offset) | Materiality | Stability and window | Outcome to today | Notes |
|---|---|---|---|---|
| Aging and all diseases cured (120) | central | speculative; not contradicted at any date | still open | |
| US population stabilized at forty million, average age 129 (226) | substantial | speculative; not contradicted | still open | |
| A birth requires a volunteer death by law (8832) | central | social premise; not contradicted | still open | |
| In the year 2000 the Earth had twenty billion people and was heading to forty (10430) | substantial | a projection when written; falsified once 2000 passed (the UN marked six billion on [12 October 1999](https://press.un.org/en/1999/19990920.pop738.html)) | falsified | `calendar_expired` true; judgment call: backstory could be counted `incidental` |

Counted premises are present at composition and, with the calendar-expired backstory excluded,
today. Plausibility as written: `present`; today: `present`. A date is not needed beyond the
upper bound. Speculative premises: yes.

### A Bad Day for Sales (Leiber)

| Premise (offset) | Materiality | Stability and window | Outcome to today | Notes |
|---|---|---|---|---|
| A mobile sales robot (823) | central | speculative; not contradicted | still open | |
| A missile strike on Manhattan, a "Hot Truce" (338, 8221, 8789) | central | speculative future history, undated; not contradicted | still open | no stated date, so not calendar-expired |
| Weather-controlled air (7896) | incidental | speculative | still open | not counted |
| Advertising copy about a Martian sunrise (6900) | incidental | advertising copy, not a claim of a settled Mars | stable | not counted |

Plausibility as written: `present`; today: `present`; no date needed. Speculative premises:
yes.

### A Case of Sunburn (Fontenay)

| Premise (offset) | Materiality | Stability and window | Outcome to today | Notes |
|---|---|---|---|---|
| Mars has a protective blue mist that shields the surface from the sun (932, 34221) | central | time-sensitive: window start is the first close-up images from Mariner 4 on [15 July 1965](https://nssdc.gsfc.nasa.gov/imgcat/html/object_page/m04_01d.html); the end of the window (consensus) is not verified | falsified | judgment call: that the premise was not contradicted in 1957 is my reading and is not checked against 1950s sources |
| Earth's magnetic field interferes with the mist, and the captured station amplifies fields (34671) | central | an invented mechanism that depends on the mist | falsified | the "contrary new theory" case in the rubric text |
| A settled Mars with dome cities, canals and green lowlands (29401) | substantial | time-sensitive, same window | falsified | |
| Mars colony founded in 1985, story dated June 2020 (12152, 11642) | substantial | a dated prediction | falsified | `calendar_expired` true |
| Gravity boats, heat guns, spaceships | incidental | speculative | still open | not counted |

Plausibility as written: `present` if composed before July 1965 (it was published in April 1957);
`ambiguous` if only the career window were known. Today: `absent`. A date is needed. Speculative
premises: yes.

### The Blue Cross (Chesterton)

| Premise (offset) | Materiality | Stability and window | Outcome to today | Notes |
|---|---|---|---|---|
| The setting is London during the 1908 Eucharistic Congress (1459) | substantial | a real event; contemporary to the author | stable | |
| A thief's tricks: messages photographed on microscope slides, a portable pillar-box (3276, 3598) | incidental | tricks, not speculative science | stable | a model could mistake a "portable pillar-box" for an invention; not counted |
| An argument that reason is supreme (35779) | incidental | argument, not a premise about the world | stable | |

No speculative premises: plausibility as written is `present` by the no-premises rule, with the
speculative-premises flag false. The keyword scan in the script finds `invent`, `machine` and
`scien` only in the senses above. As written, `different` is absent: the story is set in its
author's present. Read against today, 1908 London differs from here-and-now.

### Brown Wolf (London)

| Premise (offset) | Materiality | Stability and window | Outcome to today | Notes |
|---|---|---|---|---|
| A dog travels up to 150 miles a day to return north (7441, 6929) | substantial | strained but not an established-fact violation | stable | judgment call |
| The dog is a Klondike dog (15924) | incidental | a neighbor's claim | stable | |
| Setting: California about 1901, with a mail contract and a Klondike past (22116, 22456) | substantial | contemporary to the author | stable | |

No speculative premises: plausibility as written `present` by the no-premises rule. The keyword
scan finds one hit, a simile about "a traveller from another planet". As written, `different`
is absent. Read against today, the setting is a past era.

## Results

| Story | Date-sensitive counted premise | Calendar-expired claim | Plausibility as written | Plausibility today | Date needed |
|---|---|---|---|---|---|
| Bell | no | no | absent | absent | no |
| 2 B R 0 2 B | no | yes (year 2000) | present | present (backstory excluded) | no |
| A Bad Day for Sales | no | no | present | present | no |
| A Case of Sunburn | yes (Mars) | yes (1985, 2020) | present if before July 1965 | absent | yes |
| The Blue Cross | no | no | present (no premises) | present | no |
| Brown Wolf | no | no | present (no premises) | present | no |

One of six stories needs a date for its physical premises; two carry calendar-expired claims;
two realist stories show the same author-versus-reader time problem for the `different`
condition. This is six hand-picked controls by one rater and does not estimate how often dates
matter in the corpus.

## Judgment calls and limits

- Whether Bell's unexplained bell is a factual premise at all.
- Whether the Vonnegut year-2000 backstory is `substantial` or `incidental`.
- Whether Sunburn's mist was contradicted by knowledge available in 1957 (not checked against 1950s sources).
- The Andersen date and the Brown Wolf collection date come from search-result summaries that I did not open.
- Whether Brown Wolf's travel speed is an exaggeration or a violation.
- Brown Wolf's first appearance is unconfirmed; the Sunburn and Blue Cross dates rest on one or two secondary sources, and I did not open ISFDB.
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
        print("  ", "MISSING" if offset is None else f"offset {offset}", "|", quote[:70])
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
