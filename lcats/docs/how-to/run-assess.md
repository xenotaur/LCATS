# How to run `lcats assess`

`lcats assess` is the LLM-powered curation layer that sits on top of the
detector pipeline. It calls the Claude API with a structured tool schema,
runs pre-flight QA via `run_preflight`, and returns an `AssessmentResult`
with verdict, genre detection, and quality annotations.

## Modes

| Mode | Command | When to use |
|---|---|---|
| Detect | `lcats assess <files> --format human` | Unknown/mixed corpus — model identifies genre independently |
| Lens | `lcats assess <files> --genre horror --format human` | Curation run — model detects genre then evaluates the claimed genre |

Both modes always return `detected_genre` and `detected_genre_confidence`.
Lens mode additionally returns `genre_verdict` in `[confirmed, disputed, wrong]`
(detect mode sets it to `detected`).

## Manual prompt validation

Before running a full corpus assessment with new or modified system prompts,
spot-check on 2–3 representative stories per mode:

```bash
# Detect mode — pick one story you know well
lcats assess data/path/to/story.json --format human

# Lens mode — same story with its expected genre
lcats assess data/path/to/story.json --genre "science fiction" --format human
```

**What to verify:**

- `detected_genre` matches your expectation for the story.
- `detected_genre_confidence` is high (≥0.8) for clear cases and lower for
  genuinely borderline ones.
- `genre_verdict` in lens mode is `confirmed` for a clear match, `disputed`
  for a borderline match, `wrong` for a clear mismatch.
- `verdict` (`include`/`exclude`/`review`) aligns with your curation judgment.
  In lens mode: `disputed` should produce `review`, not `include`.
- `summary` accurately describes the story in one or two sentences.
- `issues` lists any pre-flight QA findings you would also flag by hand.

A good spot-check set includes: one story that clearly belongs to the target
genre, one that belongs to a different target genre, and one that is
borderline or mixed. If the model misclassifies the clear case or returns
implausible confidence scores, the system prompt needs adjustment before a
bulk run.

## Dry run

Use `--dry-run` to verify file discovery and pre-flight QA without making
API calls:

```bash
lcats assess data/ --dry-run                     # detect mode
lcats assess data/ --genre western --dry-run     # lens mode
```

## See also

- [`docs/reference/cli-commands.md`](../reference/cli-commands.md) for the
  full `lcats assess` flag reference (`--model`, `--max-body-chars`,
  `--format`, `--output`).
- [Preparing a corpora release](../reference/prepare-corpora-release.md)'s
  "Optional next step" section for `lcats assess` in the release workflow.
