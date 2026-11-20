# Controls for the date-aware live validation (WI-SF-0131)

Status: chosen and recorded BEFORE any run, so the controls and their expected
outcomes cannot be shaped by a result. No model has read either story for this
purpose.

The work item adds two controls to the seven canary stories: a historical-fiction
story faithful to the author's own history, and an alternate-history story. The
owner chose them on 2026-11-19 from a keyword scan and a reading of the openings
(and, for one, the ending) of the candidates in `corpora/mass_quantities`.

## The two controls

| Role | Story | Corpus ID | Length | First published (opened source) |
|---|---|---|---|---|
| Faithful historical fiction | *The Perfect Tribute*, Mary Raymond Shipman Andrews (1860-1936) | `mass_quantities/the_perfect_tribute__andrews` | about 6,000 words | *Scribner's*, July 1906 |
| Alternate history | *He Walked Around the Horses*, H. Beam Piper (1904-1964) | `mass_quantities/he_walked_around_the_horses__piper` | about 8,100 words | *Astounding Science Fiction*, April 1948 |

The corpus records `year: Unknown` for both, so the dates come from the opened
sources below and are written to `heinlein_temporal_control_dates.json`
(format `lcats-composition-dates-v1`, read through
`lcats.analysis.science_fiction.composition_sources`). Both are publication months,
used as upper bounds only.

Sources opened on 2026-11-19 (all Wikipedia, so secondary):

- https://en.wikipedia.org/wiki/He_Walked_Around_the_Horses: first published in the
  April 1948 issue of Astounding Science Fiction (now Analog).
- https://en.wikipedia.org/wiki/H._Beam_Piper: born 23 March 1904, died about
  6 November 1964 (the page says the exact date is unknown); first short story 1947.
- https://en.wikipedia.org/wiki/Mary_Raymond_Andrews (the story's own title
  redirects here): "The Perfect Tribute" appeared in Scribner's in July 1906;
  the author lived 2 April 1860 to 2 August 1936.

Limits:

- Both Project Gutenberg pages (ebooks 18807 and 12830) returned HTTP 503 with a
  six-hour retry window and were not opened. A search-result summary said the
  Gutenberg note for Piper's story gives April 1948 and that the Scribner's book
  edition of Andrews's story is September 1906; neither is relied on.
- ISFDB is not used (see `composition_date_source_evaluation.md`).
- No lower bound is set for either story. Piper's first story was published in 1947,
  which would support a lower bound of 1947 for his; that is an inference left to
  the owner.

## Why these two

- *The Perfect Tribute* is set on 18 November 1863 on the train to Gettysburg, with
  real people (Lincoln, Seward, Everett). It is faithful in outline but carries the
  legend that Lincoln wrote the address on the train, which historians dispute. A
  contradicted premise about that scene is therefore not automatically a stage
  error; the report must say which kind it is.
- *He Walked Around the Horses* opens on the real 1809 disappearance of Benjamin
  Bathurst and follows it into a continuum where history differs. Real names and
  dates sit beside invented divergence, which is the case the counterfactual
  premise kind exists for.

Candidates considered and not chosen: *Remember the Alamo* (Fehrenbach; a clean
time-travel alternate history of the Alamo, a good second alternate-history control
if the owner wants a pair), *Crossroads of Destiny* (Piper; a hybrid, a story that
contains an alternate history), *The Toy Shop* (Gerry; a sentimental invented
episode in real Civil War Washington).

## Expected outcomes, fixed in advance

Agreed by the owner:

1. **Faithful historical fiction (*The Perfect Tribute*):** `different` is `absent`,
   and few or no counted premises are contradicted, because the story stays within
   the author's own history.
2. **Alternate history (*He Walked Around the Horses*):** the stage records
   `counterfactual_divergence` premises for the points where the story's history
   departs from the real one.

Derived from the code, not separately agreed:

3. The fact table (`fact_table.py`) is not expected to audit either control. Its
   seed covers only Mars, Venus and Mercury. A matched `counterfactual_divergence`
   premise would be `not_comparable` (R1: its timeline describes the enabling
   mechanism, not the historical claim), and an empty timeline is `not_comparable`
   (R2). So the criterion "reviewed against the fact table where it covers them" is
   expected to be vacuous for these two stories. The report must say so, and the
   owner's own review of the premise lists takes its place.

What would count against the stage (to be judged by the owner, not decided here):
a faithful story given `different: present` or counted contradicted premises that
are not the disputed-anecdote kind; an alternate-history story with no
counterfactual premise at all.

## Not decided

- Lower bounds for both stories (see above).
- A runner flag to read the owner-dates file; WI-SF-0131 still needs one.
- The nine hand checks listed in `composition_date_source_evaluation.md`, and the
  seven canary stories' own dates, are separate from these two controls.
