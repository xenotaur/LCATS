# Composition-date source evaluation (ISFDB and free alternatives)

Date: 2026-11-11. Work item: `WI-SF-0128`. Governing design:
`PROP-LCATS-HEINLEIN-TEMPORAL-REFERENCE` (D4, Open Question 8).

This report evaluates where a story's first-publication date can come from, for
use as an UPPER bound on its composition date. It does not set any date. The
dates below are proposals for owner review, each labelled by how well it was
checked. Only an owner-supplied date file (see `composition_sources.py`) makes
a date binding, and it overrides everything here.

## Method and limits (read first)

- All lookups were manual, read-only, sequential single-page views made by
  subagents on 2026-11-11, plus one `robots.txt` request I made myself to
  re-check the ISFDB finding. Nothing was scraped, crawled or downloaded, and
  no test or pipeline code queries any external service.
- The subagents read pages through a **summarising fetch tool**, not as raw
  text. Every page claim below is therefore "read via summarising fetch", not a
  primary check, and I did not re-open the pages except `robots.txt`. A
  summariser can misreport. The owner checks listed at the end close this gap.
- The second pass used about 47 page fetches plus searches, a little over the
  planned 45, and sent three fetches in parallel once. That parallel burst drew
  an HTTP 429 from the SF Encyclopedia, after which that site was not used again.
- Search-result snippets that were not opened are UNCONFIRMED and are not used
  as dates.
- "Worldcon pilot set" means the 10 stories in the `sample_stories` list of
  `manifests/worldcon_spike_manifest.json`; the six trial stories are among
  them.

## 1. ISFDB: could not be evaluated, and the verdict is "do not rely on it"

- **Access.** The ISFDB `robots.txt` was readable. The one title page and the
  two wiki policy pages the fetcher tried all returned **HTTP 403 Forbidden**.
  The fetcher stopped there, as instructed, and tried no mirror or workaround;
  so only three ISFDB pages were ever attempted, and no ISFDB coverage
  measurement exists.
  Consequence: ISFDB coverage of the ten stories, its dates, and its
  author dates are all UNCONFIRMED.
- **`robots.txt`** (https://www.isfdb.org/robots.txt, re-read by me): a
  content signal of `search=yes, ai-train=no, use=reference`, which the file
  calls an express reservation of rights under EU Directive 2019/790 Art. 4;
  many AI and training crawlers (including `ClaudeBot`, `GPTBot`, `CCBot`) are
  disallowed outright; and a non-standard `Crawl-delay: 1000` with
  `Request-rate: 1000`, units unstated, which I read as "do not crawl". The
  path used for title lookups is not disallowed for generic agents, but the
  403s show the site rejects automated fetchers in practice.
- **Terms.** The copyright and data-licensing wiki pages
  (`ISFDB:Copyright`, `ISFDB:Data_licensing`) returned 403, so the licence,
  attribution rule and any rate limit are **UNCONFIRMED**. I recall the data
  being published under a Creative Commons licence with downloadable dumps, but
  that is memory, not a checked fact, and must not be relied on.
- **Verdict.** ISFDB may NOT be relied on, programmatically or otherwise, on
  this evidence. If the owner wants it used, the owner reads its wiki terms in a
  browser, decides, and looks dates up by hand; the sanctioned bulk route (the
  official database dump) is untested and its terms unread. Nothing in the
  pipeline queries it.

## 2. Alternatives: terms and access

| Source | Licence and automated-access finding | Use |
|---|---|---|
| English Wikipedia | Text under CC BY-SA 4.0 (attribution, share-alike, indicate changes). `robots.txt` leaves article pages open, welcomes low-speed bots, disallows `/w/`, `/api/` and bulk tools such as wget. API etiquette pages not read. | Manual or low-rate reads with attribution. Programmatic API use not checked. |
| SF Encyclopedia (sf-encyclopedia.com) | No `robots.txt` (404); footer says content is copyrighted by its editors; no licence or terms page found; entry pages rate-limited (HTTP 429 under three near-simultaneous requests). | Manual, one page at a time, cited not copied. Ask the editors before any systematic use. |
| Project Gutenberg | Robot policy: the site is for humans, automated access it notices can be IP-blocked; sanctioned routes are the machine-readable catalogue feed and ebook harvesting with a delay. Catalogue pages are metadata; the "Produced from ..." line is the transcribers' source note, not a scholarly claim. | Official catalogue feed only; do not scrape ebook HTML pages. |
| Internet Archive | `robots.txt` disallows only `/control/` and `/report/`; its Terms of Use text could not be read through the fetcher. Item contents metadata for the pulp issue it was checked on is excerpted from ISFDB, so it is not independent of it. | Manual; owner reads the terms. Treat contents lists as ISFDB-derived. |
| Andersen Centre (andersen.sdu.dk), Visual Haggard | Single scholarly pages used for one story each; terms not reviewed. | Citation only. |

## 3. Coverage on the ten stories

"Two sources" means two pages the subagent reported opening and agreeing,
read via summarising fetch. Months are month precision unless marked day.

| Story (corpus id) | First publication proposed | Evidence | Status | Notes |
|---|---|---|---|---|
| 2 B R 0 2 B (`mass_quantities/2_b_r_0_2_b__vonnegut`) | January 1962, *If* | Wikipedia story page; SFE Vonnegut entry; Gutenberg 21279 note "Produced from Worlds of If, January 1962" | Two or more sources agree | Author 1922-2007 (SFE). *Bagombo Snuff Box* (1999) is a reprint. |
| A Bad Day for Sales (`.../a_bad_day_for_sales__leiber`) | July 1953, *Galaxy* | Wikipedia Leiber page; Gutenberg 50819 note | Two sources agree | No Wikipedia story page. The Gutenberg note is a transcription source, consistent with but not proof of first appearance. Author 1910-1992. |
| A Case of Sunburn (`.../a_case_of_sunburn__fontenay`) | April 1957, *Worlds of If* | Gutenberg 59825 note; the archive.org item page for the issue (its metadata lists the story) | Two pages agree, **weak independence**: the second is ISFDB-derived metadata, not the scan | The scan itself was not opened, so the date is not checked against the issue. Wikipedia's Fontenay page does not mention the story. Author 1917-2007. |
| The Colour out of Space (`lovecraft/the_colour_out_of_space`) | September 1927, *Amazing Stories* (written March 1927) | Wikipedia story page; Gutenberg 68236 note | Two sources agree | Author 1890-1937. |
| The Call of Cthulhu (`lovecraft/the_call_of_cthulhu`) | February 1928, *Weird Tales* (written summer 1926) | Wikipedia story page; Gutenberg 68283 note | Two sources agree | "Summer 1926" is Wikipedia only. |
| The Bell (`anderson/bell`) | May 1845, *Maanedsskrift for Boern* (Danish original *Klokken*) | Andersen Centre register; Wikipedia Andersen bibliography | Two sources agree, for the **Danish original** | The corpus text is an English translation inside a collection (Gutenberg 1597, "Andersen's Fairy Tales"), with no translation date. Author 1805-1875. |
| The Blue Cross (`chesterton/blue_cross`) | 23 July 1910 (day), *Saturday Evening Post*, as "Valentin Follows a Curious Trail"; UK *The Story-Teller* September 1910 | Wikipedia story page; Wikimedia Commons scan record | Two sources agree, **moderate independence** (both Wikimedia) | A blog snippet giving June 1910 was NOT opened and is UNCONFIRMED. Gutenberg 204 is the whole collection (*The Innocence of Father Brown*, 1911). Author 1874-1936. |
| Brown Wolf (`london/brown_wolf`) | UNCONFIRMED; possibly *Everybody's Magazine*, August 1906 | A search snippet of a finding aid only, not opened | **UNCONFIRMED** | Gutenberg 710 is a collection with no original-publication field. A collection copyright of 1906 is a plausible ceiling, also unopened. Author 1876-1916. |
| Eve's Diary (`.../eve_s_diary_complete__twain`) | December 1905, *Harper's Bazar* (book June 1906) | Wikipedia story page; Gutenberg 8525 "Original publication 1905" | Year agrees; **month single-source** | Wikipedia's lead says 1905 and its infobox 1906 (the book). Possible reprint question with *Their Husband's Wives* (1905). Author 1835-1910. |
| Long Odds (`.../long_odds__haggard`) | February 1886, *Macmillan's Magazine* | Visual Haggard; Wikipedia *Allan's Wife and Other Tales* ("1886") | Year agrees; **month single-source** | Collected December 1889. Gutenberg 2730 gives no source edition. Another story called "Long Odds" exists (Kenneth Grahame, 1895); the title alone is ambiguous. |

Coverage summary: nine of ten have a proposed first-publication date: six at
month precision with two agreeing sources (one of them, Sunburn, with weak
independence, and one, The Bell, for the Danish original), one at day
precision (The Blue Cross), and two where the year agrees but the month rests
on one source (Eve's Diary, Long Odds). The tenth, Brown Wolf, is unconfirmed.
No ISFDB figure is available for any of them.

## 4. Findings

- **The corpus `year` metadata is not a usable date.** It is `Unknown` for the
  `mass_quantities` stories, `0` for Blue Cross and Brown Wolf, `1911` for The
  Bell (probably an edition date; the corpus labels the author "Anderson" but
  Gutenberg 1597 is Hans Christian Andersen), and `1925` for both Lovecraft
  stories, which is neither their composition (1926-1927) nor publication
  (1927-1928). Do not read it as a source.
- **Collection and translation traps.** Four of the Gutenberg texts are
  collections or may contain extras (204, 710, 8525, and 1597 for The Bell), so
  the corpus unit may be a book. The Bell's first-publication date belongs to the Danish original, not
  the English text analysed; the translation date is unknown.
- **"Written" differs from "published".** For the Lovecraft stories and The
  Blue Cross the writing date differs from the first publication. The
  composition interval's upper bound is the publication; a documented writing
  date is separate, story-specific evidence and would be a lower bound only if
  the owner records it.
- **Independence.** Gutenberg's "Produced from" note names the issue
  transcribed, which usually is the first appearance for magazine stories but
  does not prove it. The archive.org contents list is ISFDB-derived, so using it
  with ISFDB, or in place of an independent source, overstates confidence.
- **The summariser.** The fetch tool reads and summarises. Treat every row as a
  lead that two human-opened pages confirm, not as a verified fact.

## 5. Verdict and recommended policy

1. **ISFDB: not relied on** (Section 1). No pipeline or test queries it.
2. **No source here is approved for automated lookup.** Wikipedia could be used
   at low rate with attribution, but its API etiquette was not reviewed;
   Gutenberg's sanctioned route is its catalogue feed, not page scraping; the SF
   Encyclopedia and Internet Archive terms are unclear or unread.
3. **First-publication dates may be used as an UPPER bound only,** entered by
   hand into the owner-dates file with the citation as `basis`, and only when
   two opened sources agree and the owner has checked them (a date with weak
   independence, like Sunburn's, needs the owner to open the issue scan). A single-source or year-only date is recorded as
   such (use the year), and an unconfirmed date is not used.
4. **The owner's override always wins.** A date used in the live run
   (`WI-SF-0131`) needs a cited source or an owner entry. A story whose date is
   wrong by a few years can flip a time-sensitive reading (A Case of Sunburn
   flips at Mariner 4, 15 July 1965); Sunburn's April 1957 date is two sources
   with weak independence and should be opened by the owner first.

## 6. For the owner to check by hand

1. ISFDB: read `ISFDB:Copyright` and `ISFDB:Data_licensing` in a browser and
   decide whether, and how, it may be used. Then spot-check its dates against
   the table above.
2. A Case of Sunburn: open the April 1957 *If* scan, not only its contents list.
3. Brown Wolf: open the *Everybody's Magazine* August 1906 issue (HathiTrust or
   Internet Archive) and confirm it is the first printing.
4. Eve's Diary: whether *Their Husband's Wives* (1905) predates the December
   1905 *Harper's Bazar* issue.
5. The Blue Cross: open the *Saturday Evening Post* scan, or discard the June
   1910 claim.
6. The Bell: a Danish-bibliography check, and the date of the English
   translation the corpus actually holds.
7. Long Odds: a second source for the February 1886 month, and confirm it is
   Haggard's story and not another of the same title.
8. Internet Archive Terms of Use, and the SF Encyclopedia's reuse terms (ask
   its editors before any systematic use).
9. For the four collection-level Gutenberg ebooks (204, 710, 8525, 1597),
   whether the corpus unit is the story or the book.

## 7. Pages opened

ISFDB: `https://www.isfdb.org/robots.txt` (opened twice, 200). Tried and
refused (403): `https://www.isfdb.org/cgi-bin/title.cgi?2B`,
`https://isfdb.org/wiki/index.php/ISFDB:Copyright`,
`https://isfdb.org/wiki/index.php/ISFDB:Data_licensing`. No ISFDB page was
retried or reached by another route.

Terms and robots: `https://en.wikipedia.org/wiki/Wikipedia:Reusing_Wikipedia_content`,
`https://en.wikipedia.org/robots.txt`, `https://sf-encyclopedia.com/`,
`https://sf-encyclopedia.com/frequently-asked-questions`,
`https://sf-encyclopedia.com/robots.txt` (404),
`https://www.gutenberg.org/policy/robot_access.html`,
`https://www.gutenberg.org/policy/permission.html`,
`https://archive.org/robots.txt`, `https://archive.org/about/terms.php` and
`https://archive.org/about/terms` (no terms text returned).

Dates: Project Gutenberg ebook pages 21279, 50819, 59825, 68236, 68283, 1597,
204, 710, 8525, 2730 (under `https://www.gutenberg.org/ebooks/`); Wikipedia
pages `2_B_R_0_2_B`, `Fritz_Leiber`, `Charles_L._Fontenay`,
`The_Colour_Out_of_Space`, `The_Call_of_Cthulhu`, `H._P._Lovecraft`,
`Hans_Christian_Andersen_bibliography`, `The_Blue_Cross_(short_story)`,
`The_Innocence_of_Father_Brown`, `G._K._Chesterton`, `Jack_London`,
`Eve%27s_Diary`, `Allan%27s_Wife_and_Other_Tales`; Wikimedia Commons
`File:SatEvePost72319.jpg`; `https://sf-encyclopedia.com/entry/vonnegut_kurt_jr`;
`https://archive.org/details/1957-04_IF`;
`https://andersen.sdu.dk/vaerk/register/info_e.html?vid=76`;
`https://www.visualhaggard.org/novels/60`. Several guessed Wikipedia pages
returned 404 (no story page exists for A Bad Day for Sales, The Bell, Brown
Wolf or Long Odds), and one SF Encyclopedia entry returned 429.
