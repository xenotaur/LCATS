# Knight and Suvin Source Definitions

Status: source dossier for experiment-local prompt work. This file is not yet
an adopted rubric and must not be treated as authority for production
annotation.

## Source Classification

### Primary source available: Suvin

The attached PDF is an excerpt headed `Science Fiction and the Novum (1977)`.
It is treated here as a primary-source excerpt of Darko Suvin's chapter:

> My axiomatic premise in this chapter is that SF is distinguished by the
> narrative dominance or hegemony of a fictional “novum” (novelty, innovation)
> validated by cognitive logic.

Source: `1-suvin-dbah-contents_final-97-122.pdf`, printed p. 67, PDF p. 1.

Suvin describes a novum as:

> A novum or cognitive innovation is a totalizing phenomenon or relationship
> deviating from the author's and implied reader's norm of reality.

He explains “totalizing” as involving a change to the whole universe of the
tale or to crucially important aspects of it, so that the novum can provide an
analytical grasp of the whole tale.

Source: `1-suvin-dbah-contents_final-97-122.pdf`, printed p. 68, PDF p. 2.

Suvin also states that the novum is validated by the post-Baconian scientific
method, and that the relevant cognition may be a methodically developed
mental experiment following accepted scientific or cognitive logic. He allows
that the cognition may be imaginary, rather than requiring present-day
scientific buildability.

Source: `1-suvin-dbah-contents_final-97-122.pdf`, printed pp. 69-71, PDF pp.
3-5.

Suvin distinguishes SF from supernatural fantasy by arguing that the novelty
must not simply reject cognitive logic in favor of an occult or arbitrary
logic.

Source: `1-suvin-dbah-contents_final-97-122.pdf`, printed pp. 72-74, PDF pp.
6-8.

### Secondary source only: Knight

The attached Robillard essay is a secondary discussion. It reports that Knight
said a story is perceived as science fiction when it contains the “right mix”
of:

> science, technology and invention; the future and the remote past, including
> all time travel stories; extrapolation; scientific method; other places, such
> as planets and dimensions, and the visitors from them; and catastrophes,
> natural or manmade.

Source: Douglas Robillard, “Uncertain Futures: Damon Knight's Science Fiction,”
in *Voices for the Future*, vol. 3 (1984), as reproduced in the attached
`enotes.com-Golden Age of Short Science Fiction Criticism Uncertain Futures
Damon Knights Science Fiction - Doug.pdf`, PDF p. 10. Robillard's note 18
points to Damon Knight, “What Is Science Fiction?” in *Turning Points: Essays
on the Art of Science Fiction*, ed. Damon Knight (1977), p. 63; the Knight
essay itself is not included in the attachment.

The attached dissertation reproduces a related list as six numbered items,
with “science, technology and invention” combined as item 1. Source: Vivian
Elaine Jackson, *New Technology in Education as Viewed through the Utopic and
Dystopic Worlds of Science Fiction*, attached PDF, PDF p. 96 and dissertation
page numbering around p. 103.

The attached *A Sound of Thunder* presentation separates science from
technology and invention, giving seven displayed elements. It also attributes
the rule “at least three” to Knight, with two as borderline and one or none as
not science fiction. Source: attached `studylib.net-A Sound of Thunder Ray
Bradbury Presentation.pdf`, PDF pp. 3-4. This is an educational secondary
source and does not establish that the threshold is Knight's own wording.

### Research lead, not source authority: ChatGPT export

`ChatGPT-Essay Availability Online-20260921-1752.pdf` records prior research
and links the Knight list to the 1977 *Turning Points* citation. It is useful
as a provenance trail and search aid, but model-generated analysis is not a
primary source and its claims must be checked against Knight's essay.

## Provisional Prompt-Safe Definitions

These are conservative paraphrases for experiment-local prompt design. They
are not a frozen scholarly rubric and must be revised if the original Knight
essay or a better approved edition is obtained.

### Knight feature inventory

The secondary materials support the following seven-way operational split,
while the exact primary wording remains unresolved:

1. **Science:** scientific facts, theories, discoveries, natural processes, or
   speculative sciences materially represented.
2. **Technology/invention:** a device, technique, engineered system, or
   invention materially affects the setting, problem, action, or outcome.
3. **Future/remote past/time travel:** a speculative future or remote past, or
   temporal displacement.
4. **Extrapolation:** consequences developed from an identifiable scientific,
   technological, social, or historical premise.
5. **Scientific method:** observation, hypothesis, testing, measurement,
   evidential revision, or systematic inference materially drives understanding
   or action.
6. **Other places/visitors:** other planets, dimensions, substantially
   nonordinary cosmic environments, or visitors from them.
7. **Catastrophe:** a natural, technological, cosmic, biological, or
   human-caused large-scale disaster that is actual, impending, remembered, or
   causally central.

Do not attribute the seven-way split, a three-feature threshold, or any
probability to Knight as settled primary-source fact until the original essay
is checked. The current LCATS contract correctly represents seven independent
criteria but keeps source status pending in
`src/lcats/analysis/science_fiction/rubric/definitions.py`.

### Suvin novum dimensions

For the experiment, retain three independent dimensions that reflect the
primary excerpt without turning them into an additive score:

- **Novelty:** a totalizing phenomenon or relationship that deviates from the
  author's and implied reader's norm of reality and changes the whole tale or a
  crucially important aspect of it.
- **Cognitive validation:** the novelty is developed through scientific or
  cognitive logic, including a coherent imaginary cognition or mental
  experiment; present-day buildability is not required by the excerpt.
- **Narrative hegemony:** the novum is dominant or determining enough to govern
  the narrative logic, rather than being an incidental object or event.

The experiment may record estrangement evidence separately. It must not treat
character surprise as a necessary condition unless an approved design change
adds that requirement.

## Implications for Prompt Revision

- Knight examples must be labeled provisional until the primary essay is
  obtained; they should demonstrate evidence sufficiency and category
  boundaries, not add theoretical claims.
- Suvin examples can be grounded in the quoted primary excerpt, but should
  preserve the distinction between novelty, cognitive validation, and
  narrative hegemony.
- The current `knight-seven-v1` and `suvin-novum-v1` identifiers should not be
  represented as source-resolved merely because prompts contain paraphrases.
- Any revised prompt version should preserve the existing Python-derived
  Knight interval and Suvin conjunction. The model should supply decisions and
  evidence references; it should not calculate derived results.

## Source Gap

Before treating Knight wording as frozen, obtain and verify the relevant pages
of the original essay, preferably the cited 1977 *Turning Points* version or
an approved edition of *In Search of Wonder*. Record the edition, page range,
and exact quotation here, then update the rubric source status in code.
