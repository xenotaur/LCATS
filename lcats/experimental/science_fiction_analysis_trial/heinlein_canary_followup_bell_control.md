# Follow-up to the Heinlein canary rerun: why the Bell control passed in only one of three trials

Work item: WI-SF-0119 (investigation). Source artifacts: the persisted WI-SF-0116 results under
`results/worldcon_spike/heinlein_canary_v2/local/` and its report `heinlein_canary_report_v2.md`.
Everything below comes from files already on disk. No model was called, and the manifest, rubric,
prompts and persisted results were not edited.

## Summary

- The three flag-on Bell trials sent the Heinlein stage **identical inputs**: the same stage
  fingerprint inputs (temperature, token cap, system prompt, tool schema and payload hash) and the same
  three evidence records in the same order. The answers still differed, so **run-to-run variation at
  identical inputs is supported** as the immediate source of the difference between trial 1 and
  trials 2 and 3. Its mechanism is unknown.
- Trial 1 answered `different`, `essential` and `causal` as `absent`. Trials 2 and 3 answered all five
  criteria `present`. In trials 2 and 3, the evidence cited for `different`, `essential` and `causal`
  is mainly the record in which the children realize the bell does not exist, and in my reading it
  does not describe a changed condition, an essential one, or a conflict.
- Across all six persisted Bell Heinlein responses, the three from the first canary and the three from
  this rerun, five set every criterion to `present` in the raw model text and one (v2 trial 1) did not.
  The first canary's responses never became verdicts: trial 1 was fenced text that did not parse
  (verdict `None`), and trials 2 and 3 were discarded for mismatched keys (verdict `indeterminate`), so
  this is a count of raw text only. The two canaries ran under
  different prompt versions and different evidence sets, so they are context, not repeats. In raw
  text, the Bell control's absent answers are the rarer outcome so far.
- The manifest's rationale for the control rests on "extrapolates no scientific or technological
  condition", but none of the five encoded Heinlein condition texts requires the difference to be
  scientific or technological. That mismatch is a reading of the texts, not a finding about the model.
- Explanations that need a live run are labelled hypotheses below. Section 6 proposes four additional
  control stories and one probe, each control with an expectation and cited text written before any run, and section 7 defines the live-run
  design a later item would need.

## 1. What differs between trial 1 and trials 2 and 3

Evidence IDs are shortened to their last six characters. They stand for the same three records in
every trial:

| Short ID | Raw ID | Evidence type | Text (shortened) |
|---|---|---|---|
| `315749` | e2 | character reaction | "Now we are there! In reality the bell does not exist; it is only a fancy that people have taken into their heads!" |
| `84d727` | e3 | reader-facing contrast | everybody was unanimous that the bell was heard, except one who said it was too small and fine to be heard at that distance |
| `3cd279` | e1 | scientific or technical explanation | "he said that the sound proceeded from a very large owl, in a hollow tree; a sort of learned owl..." |

| Criterion | Trial 1 | Trial 2 | Trial 3 |
|---|---|---|---|
| different | absent (0.90): "does not introduce any new invention or condition differing from present day" | present (0.95), cites `315749`: "Bell is imaginary, a new condition distinct from reality" | present (0.80), cites `315749`: "Bell is imaginary, a novel condition distinct from reality" |
| essential | absent (0.95): "Cannot be essential because conditions are not different" | present (0.94), cites `315749`: "Imaginary bell drives plot and character actions" | present (0.85), cites `315749`, `84d727`: "drives the plot and is central to narrative events" |
| human | present (0.80), cites `315749` | present (0.93), cites `315749` | present (0.75), cites `315749` |
| causal | absent (0.95): "No new condition causes or affects the human problem" | present (0.92), cites `315749`: "The bell's nonexistence causes confusion and conflict among characters" | present (0.70), cites `315749`: "The realization that the bell is imaginary causes plot shift and conflict" |
| plausible | present (0.70), cites `3cd279`, counterevidence `315749` | present (0.85), cites `3cd279` | present (0.60), cites `3cd279` |
| Output tokens | 1792 | 1339 | 1343 |
| Call path | tool call | tool call | text fallback |

Trial 1 reads "different" as an invention or condition that differs from the present day and finds
none. Trials 2 and 3 take the bell's non-existence as the new condition, and then derive `essential`
and `causal` from it. The dependency rules (`essential` and `causal` need `different`) are satisfied in
every trial, so the validator did not intervene.

## 2. Were the three Bell evidence sets identical in content and order?

Method (section 9 has the script and its output):

1. Hash the evidence-stage `tool_result` of each trial. The three hashes are the same
   (`16dfe3d86b89`), as are the evidence-stage input and output token counts (3743 and 1934).
2. Compare the evidence records in each trial's sidecar by ID, in stored order, and hash their quote
   text. All three trials hold the same three records in the same order (`315749`, `84d727`, `3cd279`),
   and the quote hash is the same (`6abe83a4f826`).
3. Compare the Heinlein stage fingerprint inputs. The payload hash (`149c071e2019`) and the input token
   count (4636) are the same in all three trials. The payload hash covers what the runner sent to the
   model for this stage, so the story and evidence it carried were the same.

**Result: identical in content and order.** A fourth candidate (`e4`, "I must and will find the bell,
even if I am obliged to go to the end of the world.") was quarantined in each trial with the reason
"quote could not be located in prepared story", so it never reached the Heinlein stage.

Because the payload hash is identical while the Knight and Suvin outcomes differ between trials (the
Knight stage failed in trials 1 and 2 and succeeded in trial 3; Suvin used the text fallback in
trial 2), those stages do not feed the Heinlein payload.

## 3. Does the cited evidence bear on the criteria?

These are my readings of the quoted text and the owner may disagree.

- `315749` (the children realize "the bell does not exist; it is only a fancy") supports `human` in
  all trials: the quote is about people's beliefs. For `different` and `causal` in trials 2 and 3 it
  shows a belief being corrected, not a changed condition or a conflict, so the support is thin.
- `essential` in trial 3 also cites `84d727`, a record about whether the bell could be heard at a
  distance. It does not on its face show that a new condition is essential to the plot.
- `plausible` cites `3cd279`, the owl explanation, in every trial. Whether a "learned owl that
  continually knocks its head against the branches" is a naturalistic explanation is itself a question
  the rubric text leaves to the reader.
- No record in the evidence set describes an invention, a technology or a changed social condition.
  The set contains three records from a story that the manifest labels fantasy.

## 4. Candidate explanations, tested against the artifacts only

| Explanation | Status | Basis |
|---|---|---|
| Different evidence in different trials | **Contradicted** as the source of the difference between trials | Evidence set and Heinlein payload hash identical (section 2). |
| Tool-call versus text-fallback path | **Contradicted** | Trial 1 (tool call) did not qualify, trial 2 (tool call) qualified, trial 3 (text fallback) qualified. |
| Different prompt or schema between trials | **Contradicted** for the between-trial difference | System prompt and tool schema hashes identical. |
| Upstream Knight or Suvin outcomes | **Contradicted** | Identical payload hash despite different Knight and Suvin outcomes. |
| Run-to-run variation at identical inputs | **Supported** | Same inputs, different outputs, with the runner's fingerprint recording temperature 0.0. **Mechanism unknown, a hypothesis that needs a live run:** server-side nondeterminism, load from the other session that shared the Ollama server, or sampling settings the runner does not persist. The request was not persisted, so what the server received is not observable (see WI-SF-0120). |
| Rubric wording admits a literal reading under which "the bell is imaginary" is a "different" condition | **Supported as a reading of the text, hypothesis for the effect on the model** | The `different` slot says the conditions "must be different from here-and-now in some respect; the difference may lie only in an invention made in the course of the story". None of the five slot texts requires the difference to be scientific or technological. Whether the model's answers follow from that wording needs a live run. |
| The prompt does not exclude fantasy or imaginary conditions | **Hypothesis that needs a live run** | The prompt excludes decorative technology, a different setting that changes nothing, and a problem that would arise unchanged today. It says nothing about fantasy, belief or imagined objects. Changing the prompt is out of scope here. |
| The evidence set (three records, none describing a changed condition) invites the "imaginary bell" reading | **Hypothesis that needs a live run** | Same evidence in every trial, so it cannot explain the difference between trials, but it may explain why the typical answer is `present`. |
| The shared server's other client or machine sleep disturbed a trial | **Not observable from these artifacts** | The Bell story in trial 3 took 914 s because of a machine sleep (see `heinlein_canary_report_v2.md`), but the Heinlein answers of trials 2 and 3 are near-identical (same statuses, nearly the same support, token counts 1339 and 1343), so there is no sign the sleep changed the answer. |

## 5. Context from the first canary, and the manifest expectation

- The three first-canary Bell Heinlein responses (prompt version v1, different evidence IDs, wrong key
  names) also set `different`, `essential`, `human`, `causal` and `plausible` to `present`. Trials 2 and
  3 of that canary are identical to each other. Together with this rerun, five of six Bell responses
  say all five conditions are present in the raw model text. None of the first-canary responses
  produced a verdict: trial 1 was fenced JSON text that did not parse (verdict `None`), and trials 2 and 3
  were discarded for mismatched keys (verdict `indeterminate`). The prompt, the evidence and the key
  names also differ, so this is context and not six repeats.
- The manifest records the Bell expectation as `does_not_qualify` or `indeterminate`, with the
  rationale that the story "extrapolates no scientific or technological condition and its problem is
  not created by one". The five encoded condition texts say nothing about scientific or technological
  extrapolation, so the expectation depends on a reading the prompt does not state. The expectation is
  an operational check and not a gold label. This item does not change it. The owner decided that
  Bell stays listed as a negative control for this finding. Whether a fairy-tale or imagined condition
  should count as "different" under Heinlein's rubric is a rubric-interpretation question left open for
  a later work item.
- Vonnegut qualified in all three trials, and Bell qualified in two of three, so the detector has not
  yet shown that it separates the two stories. One negative control cannot say more.

## 6. Proposed additional controls (expectations written before any run)

All expectations are operational checks, not gold labels. The stories come from
`worldcon_spike_manifest.json`, so no new corpus selection is needed. The corpora were read from the
main checkout's `corpora/` directory. Offsets below are 0-based character offsets into the `body`
field of each `story.json`, and each citation gives the passage's opening words so it can be found
without the offset. Line breaks inside a passage are shown as spaces. All eleven citations were checked
programmatically against the corpus files.

**Source of each expectation.** Each expectation cites story text, as the work item asks. A passage
can show that a condition exists in a story, but it cannot prove what verdict the model should return,
so some judgement remains with the author of the expectation. The owner reviewed these rows in the
WI-SF-0119 execution session and decided as follows: rows 1 and 2 accepted as stated, row 3 accepted
with the per-criterion form below, row 4 kept with the weaker expectation below, and Cthulhu added as
a probe. The citations and the owner's decisions are the source. They are not owner-supplied verdicts
for the models to be scored against, and the owner confirms each expectation again before it is locked
into a manifest.

| # | Story | Role | Expected result | Cited text |
|---|---|---|---|---|
| 1 | `chesterton/blue_cross` (mystery) | negative | verdict `does_not_qualify` or `indeterminate` | Offset 7, "Between the silver ribbon of morning and the green glittering ribbon of sea, the boat touched Harwich", an ordinary Edwardian arrival; offset 46112, "Do not bow to me, mon ami", the arrest at the end. A keyword scan of the body (invent, machine, robot, future, scien, electric, telephone, rocket, planet, atom, ray and similar) found no hit that describes a changed condition. The one in-story invention is a thief's portable pillar-box used as a trap, which a model could count as a "different" condition. |
| 2 | `london/brown_wolf` (western) | negative | verdict `does_not_qualify` or `indeterminate` | Offset 0, "She had delayed, because of the dew-wet grass", a California orchard; offset 31604, "Wolf’s trot broke into a run", the ending. The same keyword scan found one hit, a simile ("alien as a traveller from another planet"). The owner notes that London also wrote science fiction, and that this reads as one of his Klondike stories, which is consistent with a negative. |
| 3 | `mass_quantities/a_case_of_sunburn__fontenay` (science fiction) | positive | `different`, `essential`, `human` and `causal` each not `absent` (the form the Vonnegut expectation already uses); the verdict itself is not constrained | Offset 576, "The sun was settling over the iron-red wastes", a settled Mars with groundcars and marsuits; offset 4488, "capture The Egg"; offset 34676, "the Earth’s magnetic field, not that of Mars, that interferes with the blue mist", the mechanism; offset 35307, "severe burns over most of their bodies", the effect on Marscorp's troops. |
| 4 | `mass_quantities/a_bad_day_for_sales__leiber` (science fiction) | positive, weaker | `different` and `human` each not `absent`; no constraint on the verdict or on `essential` and `causal` | Offset 117, "The big bright doors of the office building parted", a robot vendor on Times Square; offset 8789, "the silver-green bud bloomed above Manhattan", the blast; offset 12931, "Robie helped me", the lost girl and the robot's last scene. The war ("the Hot Truce") and the blast, not the robot, are what the story turns on, and the robot is largely a satirical backdrop, so `essential` and `causal` are not expected. |

Why each row is informative:

1. A realist story with no imagined condition. If the model marks `different` present here, the problem
   is not specific to fairy tales.
2. A second realist story from a different genre, so a pass on one is not an accident.
3. A positive whose human problem depends on the new conditions in a way the model must trace. The
   expectation avoids the `plausible` criterion on purpose: whether a story that posits a habitable Mars
   written before space probes should be judged plausible against what was known at the time or what is
   known now is an open question for the owner, to be discussed separately (see section 8).
4. A second positive with a different kind of difference (a machine), kept weaker because the label rests
   on the manifest role `clear_sf_positive` and not on a reading that the robot drives the plot.

`anderson/bell` stays as the existing fairy-tale control and `mass_quantities/2_b_r_0_2_b__vonnegut`
as the existing positive. `lovecraft/the_call_of_cthulhu` (manifest role `supernatural_contrast`) is
added as a **probe, not a control**: it tests the imagined-versus-scientific question that Bell raises,
and its expected verdict is itself contested, so it carries no expectation and its results are
reported as counts only.

## 7. Live-run design a later item would need (not run here)

- Every control story, new and existing, and the Cthulhu probe, gets at least three flag-on trials under
  identical settings: same model digest, temperature, max tokens, manifest and flags.
- Trial k of every story runs back to back, so all stories share the server conditions of round k.
- The comparison is the count of verdicts per story across trials, never a single run.
- Run on a private Ollama server (WI-SF-0121) and persist the request (WI-SF-0120), so the run does not
  repeat the shared-server and unobservable-request limits of this canary.
- Cost: the v2 trials took about 155 to 300 s per story, excluding the trial 3 Bell story that overlapped
  a machine sleep, so the seven-story, three-trial design (two existing stories, four new controls and the
  probe) is of the order of 21 story-runs of a few minutes each. This is an estimate from the v2 latencies, not a measurement of the new stories.

This design is defined here because the repository's other paired-run rule (WI-LLM-0059) covers
baseline versus modified prompt comparisons and does not say how control stories are paired.

## 8. Limits

- Three responses cannot establish a cause. The statuses above are labelled supported, contradicted or
  hypothesis, and any hypothesis needs a live run.
- The "bearing" judgements in section 3 are my readings and are not validated by the owner. The
  controls' expectations cite story text and record the owner's decisions on inclusion and form, but the
  owner confirms each expectation again before it is locked.
- Open question for the owner, to be discussed separately: how the `plausible` condition should treat
  stories written before later knowledge (for example a habitable Mars). The Sunburn expectation avoids
  `plausible` until that is decided.
- The keyword scans in section 6 are a mechanical check for obvious changed conditions, not a reading of
  the whole story.
- Nothing here claims the detector is accurate or validated.
- The editable install of the package in this environment points to a different checkout, so the rubric
  text was read from this repository's source with `PYTHONPATH=src`.
- The persisted result files contain absolute local paths, as noted in the v2 report.

## 9. Method and reproduction

Run from the `lcats/` project root, with no dependencies beyond the Python standard library:

```python
import hashlib, json

ROOT = "experimental/science_fiction_analysis_trial/results/worldcon_spike"
V2 = f"{ROOT}/heinlein_canary_v2/local"
V1 = f"{ROOT}/heinlein_canary/local"
BELL = "anderson__bell-bdac5ef3c713"


def load(path):
    with open(path) as handle:
        return json.load(handle)


def digest(value):
    text = json.dumps(value, sort_keys=True)
    return hashlib.sha256(text.encode()).hexdigest()[:12]


print("== Heinlein stage fingerprint inputs, Bell, v2 trials 1-3")
for trial in (1, 2, 3):
    data = load(f"{V2}/trial-{trial}/{BELL}/sf_heinlein.json")
    inputs = data["fingerprint"]["inputs"]
    keys = ("temperature", "max_tokens", "system_prompt_sha256", "tool_schema_sha256", "payload_sha256")
    print(trial, {key: str(inputs[key])[:12] for key in keys})

print("== Evidence tool result hash, evidence record order, and record text hash")
for trial in (1, 2, 3):
    side = load(f"{V2}/trial-{trial}/{BELL}/science-fiction-sidecar.json")["data"]
    records = side["evidence_sets"][0]["records"]
    evidence = load(f"{V2}/trial-{trial}/{BELL}/sf_evidence.json")["data"]
    print(trial, digest(evidence["tool_result"]), [r["evidence_id"][-6:] for r in records],
          digest([r["quote"] for r in records]))

print("== Heinlein answers per trial (criterion, status, support, counter, confidence)")
for trial in (1, 2, 3):
    data = load(f"{V2}/trial-{trial}/{BELL}/sf_heinlein.json")["data"]
    print("trial", trial, "tokens", data["input_tokens"], data["output_tokens"])
    for item in data["tool_result"]["heinlein_criteria"]:
        support = [i[-6:] for i in item["supporting_evidence_ids"]]
        counter = [i[-6:] for i in item["counterevidence_ids"]]
        print(" ", item["criterion_id"], item["status"], support, counter, item["confidence"])
```

Output as of this commit:

```text
== Heinlein stage fingerprint inputs, Bell, v2 trials 1-3
1 {'temperature': '0.0', 'max_tokens': '8192', 'system_prompt_sha256': '6abb7d9228a8', 'tool_schema_sha256': '22ffe160a440', 'payload_sha256': '149c071e2019'}
2 {'temperature': '0.0', 'max_tokens': '8192', 'system_prompt_sha256': '6abb7d9228a8', 'tool_schema_sha256': '22ffe160a440', 'payload_sha256': '149c071e2019'}
3 {'temperature': '0.0', 'max_tokens': '8192', 'system_prompt_sha256': '6abb7d9228a8', 'tool_schema_sha256': '22ffe160a440', 'payload_sha256': '149c071e2019'}
== Evidence tool result hash, evidence record order, and record text hash
1 16dfe3d86b89 ['315749', '84d727', '3cd279'] 6abe83a4f826
2 16dfe3d86b89 ['315749', '84d727', '3cd279'] 6abe83a4f826
3 16dfe3d86b89 ['315749', '84d727', '3cd279'] 6abe83a4f826
== Heinlein answers per trial (criterion, status, support, counter, confidence)
trial 1 tokens 4636 1792
  different absent [] [] 0.9
  essential absent [] [] 0.95
  human present ['315749'] [] 0.8
  causal absent [] [] 0.95
  plausible present ['3cd279'] ['315749'] 0.7
trial 2 tokens 4636 1339
  different present ['315749'] [] 0.95
  essential present ['315749'] [] 0.94
  human present ['315749'] [] 0.93
  causal present ['315749'] [] 0.92
  plausible present ['3cd279'] [] 0.85
trial 3 tokens 4636 1343
  different present ['315749'] [] 0.8
  essential present ['315749', '84d727'] [] 0.85
  human present ['315749'] [] 0.75
  causal present ['315749'] [] 0.7
  plausible present ['3cd279'] [] 0.6
```

The first-canary comparison in section 5 was read from the persisted files under
`results/worldcon_spike/heinlein_canary/local/trial-N/_raw/*/anderson__bell*/sf_heinlein.json`: trial 1
is fenced JSON text with `decision` values all `present`, and trials 2 and 3 are tool results with
`decision_state` all `present` and equal to each other.
