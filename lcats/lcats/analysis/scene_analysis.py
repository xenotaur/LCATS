"""Scene and Sequel analysis using LLMs."""

import re
from typing import Any, Dict, List, Optional


from lcats import utils
from lcats.analysis import llm_extractor
from lcats.analysis import text_segmenter


SCENE_SEQUEL_SYSTEM_PROMPT = """
You are a narrative segmentation assistant. Your job is to segment a story
into COARSE-GRAINED, contiguous narrative segments (“scenes” at the level
of time/place), then label each segment.

### Segment Types
- dramatic_scene: a narrative scene where a focal character with a Goal takes
  Action, encounters Conflict, and reaches a Disaster or Success (GACD).
- dramatic_sequel: a narrative scene (typically after a dramatic_scene) where
  a focal character experiences Emotion, reasons about Options, Anticipates
  outcomes, and Chooses a new goal (ERAC).
- narrative_scene: a narrative scene unified by time/place (and often
  character/action) but lacking clear GACD/ERAC structure.
- other: text that is not a narrative scene (e.g., front/back matter,
  epigraphs, meta-commentary, tables of contents, etc.).

### Granularity Rules (VERY IMPORTANT)
1) Coarse segmentation only. Prefer FEWER, LARGER segments over many small ones.
2) Split primarily on MEANINGFUL changes in TIME and/or PLACE (or explicit
   scene-break markers like “***”, chapter headers, clear time jumps).
3) Do NOT split simply because a paragraph or a couple of sentences shift topic.
   If time/place is stable, keep them in the same segment.
4) Merge tiny candidate segments (< ~3 sentences or ~100 characters) into
   adjacent segments unless there is an explicit time/place change.
5) Dialogue ping-pong alone is not a boundary; treat as one scene unless
   time/place changes.
6) A dramatic_sequel typically follows a dramatic_scene in the SAME time/place,
   unless the text clearly relocates the character in time/place.
7) If unsure between dramatic_scene vs dramatic_sequel, base the decision on
   the **dominant function** of the segment (see Decision Rubric). Only if
   neither GACD nor ERAC is sufficiently evidenced, choose narrative_scene.

### Decision Rubric (apply in this order)
A) **GACD test (dramatic_scene)**:
   - Evidence threshold: at least 3 of {Goal, Action, Conflict, Outcome} present,
     with **Conflict** strongly indicated; Outcome may be Disaster, Success,
     or clear interim result **within** the segment.
   - "Action" here means an on-stage attempt to achieve the Goal that meets
     resistance. Purely logistical/administrative actions (asking directions,
     bandaging, scheduling, riding a train) are NOT sufficient unless they are
     the means by which the Goal is pursued and meet resistance on-stage.

B) **ERAC test (dramatic_sequel)**:
   - Evidence threshold: at least **2 of {Emotion, Reason, Anticipation, Choice}**
     are clearly present; **AND** there is no on-stage Conflict/Outcome within
     the segment.
   - Typical cues: “dazed / shaken / weak”, “recalled…”, medical attention,
     **deliberation** (“too far to go”, “I determined/decided/resolved”), planning,
     consulting authorities (doctor/police) as **choice** rather than conflict.

C) If neither threshold is met:
   - Label **narrative_scene** when time/place unity is clear.
   - Otherwise label **other**.

### Consistency Constraints
- If you label **dramatic_scene**:
  - checks.gacd.has_action == true
  - checks.gacd.has_conflict == true
  - checks.gacd.outcome != "None"
- If you label **dramatic_sequel**:
  - At least two of {checks.erac.has_emotion, has_reason, has_anticipation, has_choice} are true.
  - checks.gacd.has_conflict == false
  - checks.gacd.outcome in {"None", "Unclear"}

### Common Confusions to Avoid
- **Sequel vs Narrative**: If the segment shows recovery/reaction + thinking
  through options + a clear decision/commitment, label **dramatic_sequel**,
  not narrative_scene.
- **Action vs Logistics**: Asking a porter, getting treated, choosing to report,
  or traveling are **logistical** steps; unless they meet resistance that creates
  **Conflict** in the moment, they are **not** GACD "Action".
- **Morning-after** recovery with planning is a frequent **dramatic_sequel**.

### Coverage & Ordering Rules
- Ensure coverage across the entire STORY. If later paragraphs are narrative
  but do not fit GACD/ERAC, label them as narrative_scene (or other); do not
  omit segments.
- Segments must be in ascending order, contiguous within their own boundaries,
  and non-overlapping. “Other” is acceptable for non-narrative material.

### Output Requirements (JSON ONLY)
Return exactly one JSON object: { "segments": [ ... ] }

For each segment include:
- segment_id: integer index starting at 1.
- segment_type: "dramatic_scene" | "dramatic_sequel" | "narrative_scene" | "other".

# --- Robust location selectors (PRIMARY) ---
- start_par_id: integer paragraph id where the segment begins (inclusive).
- end_par_id: integer paragraph id where the segment ends (inclusive).
- start_exact: the FIRST ≤120 characters of the segment, COPIED VERBATIM from the STORY text.
- end_exact: the LAST ≤120 characters of the segment, COPIED VERBATIM from the STORY text.
- start_prefix: ≤60 characters immediately BEFORE start_exact in the STORY ("" if none).
- end_suffix: ≤60 characters immediately AFTER end_exact in the STORY ("" if none).

Rules for anchors:
- Copy characters EXACTLY as they appear in the STORY (whitespace/punctuation included).
- Do NOT include paragraph id markers like [P0001] in start_exact/end_exact/prefix/suffix.

# --- Advisory offsets (OPTIONAL) ---
- start_char: 0-based start index into the STORY string (Python slicing) or null if unsure.
- end_char: 0-based end index (exclusive) into the STORY or null if unsure.

# --- Descriptive fields ---
- summary: ≤200 characters summarizing the segment (not the full text).
- cohesion: brief notes identifying the unifying TIME/PLACE/CHARACTERS.
- gacd: for dramatic_scene only, else null:
  { "goal": "...", "action": "...", "conflict": "...", "outcome": "Disaster|Success|Unclear" }.
- erac: for dramatic_sequel only, else null:
  { "emotion": "...", "reason": "...", "anticipation": "...", "choice": "..." }.
- reason: 1–3 sentences justifying the label and boundary (refer to time/place continuity
  and **Decision Rubric** evidence).
- confidence: float in [0,1].
"""

SCENE_SEQUEL_USER_PROMPT_TEMPLATE = """
You will receive a STORY with paragraph ids embedded as markers like [P0001].
Use paragraph ids for boundaries and supply robust text anchors as described.

Procedure you MUST follow (internally):
1) Skim the STORY to identify major time/place blocks and explicit scene-breaks.
2) Propose initial boundaries at meaningful time/place changes or explicit markers.
3) Merge adjacent tiny spans (< ~3 sentences or ~100 chars) unless there is a real time/place shift.
4) Apply the **Decision Rubric** from the system prompt to classify each final segment:
   - dramatic_scene → GACD threshold (≥3; conflict strongly indicated; outcome within segment).
   - dramatic_sequel → ERAC threshold (≥2; no on-stage conflict/outcome; recovery/plan/choice cues).
   - narrative_scene → time/place unity without meeting either threshold.
   - other → non-narrative material.
5) Ensure later paragraphs are not omitted; if unsure, prefer narrative_scene over omission.
6) Produce ONLY the JSON described in the system prompt, using the exact keys and schema.
7) Enforce **Consistency Constraints** between label and checks fields.

Return ONLY JSON with this shape:
{{
  "segments": [
    {{
      "segment_id": 1,
      "segment_type": "dramatic_scene" | "dramatic_sequel" | "narrative_scene" | "other",
      "start_par_id": 1,
      "end_par_id": 3,
      "start_exact": "<first ≤120 chars of this segment, verbatim from STORY>",
      "end_exact": "<last ≤120 chars of this segment, verbatim from STORY>",
      "start_prefix": "<≤60 chars before start_exact or \"\">",
      "end_suffix": "<≤60 chars after end_exact or \"\">",
      "start_char": null,
      "end_char": null,
      "summary": "<≤200-char summary>",
      "cohesion": {{
        "time": "<unifying time (stated or implied)>",
        "place": "<unifying place (stated or implied)>",
        "characters": ["<main character(s)>"]
      }},
      "gacd": {{
        "goal": "...",
        "action": "...",
        "conflict": "...",
        "outcome": "Disaster|Success|Unclear"
      }} | null,
      "erac": {{
        "emotion": "...",
        "reason": "...",
        "anticipation": "...",
        "choice": "..."
      }} | null,
      "reason": "<why these boundaries/label per Decision Rubric>",
      "confidence": 0.0
    }}
  ]
}}

STORY (with paragraph ids; DO NOT include [P####] markers in anchors):
\"\"\"{indexed_story_text}\"\"\"
"""


def make_segment_extractor(client: Any) -> llm_extractor.JSONPromptExtractor:
    """Create a JSONPromptExtractor configured for scene/sequel extraction.

    Args:
        client: OpenAI-like client (supports chat.completions.create).

    Returns:
        Configured JSONPromptExtractor that returns a dict under key "segments".
    """
    return llm_extractor.JSONPromptExtractor(
        client,
        system_prompt=SCENE_SEQUEL_SYSTEM_PROMPT,
        user_prompt_template=SCENE_SEQUEL_USER_PROMPT_TEMPLATE,
        output_key="segments",
        default_model="gpt-4o",
        temperature=0.2,
        force_json=True,
        text_indexer=text_segmenter.paragraph_text_indexer,
        result_aligner=text_segmenter.segments_result_aligner,
        result_validator=text_segmenter.segments_auditor,
    )


def display_segments(story_text, extracted_scenes):
    """
    Pretty-print segment results produced by the updated extractor.

    - Uses start_char/end_char when valid.
    - If missing/invalid, derives a best-effort span from start_exact/end_exact.
    - Uses utils.sm for compact previews.
    - Normalizes preview text:
        * collapse runs of spaces to a single space
        * single newlines -> spaces
        * 2+ newlines -> single newline
    """

    def _normalize_preview(s: str) -> str:
        if not s:
            return ""
        # unify newlines
        s = s.replace("\r\n", "\n").replace("\r", "\n")
        # mark paragraph breaks (2+ newlines)
        s = re.sub(r"\n{2,}", "\u2029", s)
        # single newlines -> spaces
        s = s.replace("\n", " ")
        # collapse spaces/tabs
        s = re.sub(r"[ \t\u00A0]+", " ", s).strip()
        # restore paragraph breaks to single newline
        s = s.replace("\u2029", "\n")
        return s

    def _sm_norm(s: str, limit: int) -> str:
        return utils.sm(_normalize_preview(s or ""), limit=limit)

    n_text = len(story_text)

    for i, seg in enumerate(extracted_scenes):
        segment_id = seg.get("segment_id", "unknown")
        segment_type = seg.get("segment_type", "unknown")
        confidence = seg.get("confidence", -1.0)
        reason = seg.get("reason", "unknown")
        summary = seg.get("summary", "")

        cohesion = seg.get("cohesion", {}) or {}
        gacd = seg.get("gacd", None)
        erac = seg.get("erac", None)

        # Anchors & paragraph ids (new fields)
        start_par_id = seg.get("start_par_id", None)
        end_par_id = seg.get("end_par_id", None)
        start_exact = seg.get("start_exact", "") or ""
        end_exact = seg.get("end_exact", "") or ""
        start_prefix = seg.get("start_prefix", "") or ""
        end_suffix = seg.get("end_suffix", "") or ""

        # Offsets (may be missing/invalid)
        start_char = seg.get("start_char", None)
        end_char = seg.get("end_char", None)

        def _valid_span(a, b):
            return isinstance(a, int) and isinstance(b, int) and 0 <= a < b <= n_text

        span_note = ""
        if not _valid_span(start_char, end_char):
            # Derive from anchors if possible (raw text; no normalization here)
            s_idx = story_text.find(start_exact) if start_exact else -1
            if s_idx != -1:
                e_pos = story_text.find(end_exact, s_idx) if end_exact else -1
                if e_pos != -1:
                    start_char = s_idx
                    end_char = e_pos + len(end_exact)
                    if _valid_span(start_char, end_char):
                        span_note = " (derived from anchors)"
                    else:
                        start_char = end_char = None
                else:
                    # fallback: partial window from start_exact
                    if start_exact:
                        start_char = s_idx
                        end_char = min(n_text, s_idx + max(len(start_exact), 120))
                        if _valid_span(start_char, end_char):
                            span_note = " (partial span from start_exact)"
                        else:
                            start_char = end_char = None

        length_str = (
            f"{end_char - start_char} chars"
            if _valid_span(start_char, end_char)
            else "unknown"
        )

        print(f"Segment {i}: Type {segment_type} (Confidence: {confidence})")
        print(f" - Segmentation Rationale: {_sm_norm(reason, 200)}")
        print(f" - Summary: {_sm_norm(summary, 200)}")
        print(
            f" - Segment ID: {segment_id}, Chars: [{start_char}:{end_char}] {span_note}, Length: {length_str}"
        )

        # Paragraph & anchors (normalized+sm for readability)
        print(f" - Paragraphs: start_par_id={start_par_id}, end_par_id={end_par_id}")
        print(
            " - Anchors:"
            f"\n     start_prefix='{_sm_norm(start_prefix, 80)}'"
            f"\n     start_exact ='{_sm_norm(start_exact, 120)}'"
            f"\n     end_exact   ='{_sm_norm(end_exact, 120)}'"
            f"\n     end_suffix  ='{_sm_norm(end_suffix, 80)}'"
        )

        # Cohesion pretty-print
        time_ = cohesion.get("time", "")
        place = cohesion.get("place", "")
        chars = cohesion.get("characters", [])
        # Normalize the string fields for display
        print(
            f" - Cohesion: time='{_sm_norm(time_, 120)}', place='{_sm_norm(place, 120)}', characters={chars}"
        )

        if gacd:
            # Normalize each field of GACD for display
            g_goal = _sm_norm((gacd or {}).get("goal", ""), 140)
            g_act = _sm_norm((gacd or {}).get("action", ""), 140)
            g_con = _sm_norm((gacd or {}).get("conflict", ""), 140)
            g_out = (gacd or {}).get("outcome", "")
            print(
                f" - GACD: goal='{g_goal}', action='{g_act}', conflict='{g_con}', outcome='{g_out}'"
            )
        if erac:
            e_emo = _sm_norm((erac or {}).get("emotion", ""), 140)
            e_rea = _sm_norm((erac or {}).get("reason", ""), 140)
            e_ant = _sm_norm((erac or {}).get("anticipation", ""), 140)
            e_cho = _sm_norm((erac or {}).get("choice", ""), 140)
            print(
                f" - ERAC: emotion='{e_emo}', reason='{e_rea}', anticipation='{e_ant}', choice='{e_cho}'"
            )

        # Optional: show a normalized + sm preview slice if we have a valid span
        if _valid_span(start_char, end_char):
            snippet = story_text[start_char:end_char]
            print(f" - Preview: {_normalize_preview(snippet)[:200]}")

        print()


SCENE_SEMANTICS_SYSTEM_PROMPT = """
You are a careful analyst of narrative segments. Your task is to read ONE
contiguous segment of a story (only the text provided) and classify it into
exactly one of:

- dramatic_scene: A narrative scene with Goal–Action–Conflict–Outcome (GACD).
  A focal character pursues a goal, acts, meets resistance, and the segment
  itself reaches an outcome (Disaster or Success).

- dramatic_sequel: A narrative scene (typically after a dramatic scene),
  showing Emotion–Reason–Anticipation–Choice (ERAC). The focal character reacts,
  thinks through options, anticipates outcomes, and makes a choice/new goal.

- narrative_scene: A narrative scene unified by time/place (and often
  characters/action) but lacking clear GACD/ERAC structure.

- other: Non-narrative or framing material (paratext, front/back matter, etc.)
  or text that is not a coherent time/place scene.

IMPORTANT:
- Use ONLY the provided segment text. Ignore any external labels or metadata.
- Quote or paraphrase SHORT evidence (≤ 160 chars each). Prefer quotes when
  possible; paraphrase only if exact phrasing is too long.

DECISION RUBRIC (apply in this order)
A) GACD → dramatic_scene
   • Threshold: at least 3 of {{Goal, Action, Conflict, Outcome}} present,
     with Conflict clearly on-stage; an Outcome occurs **within this segment**.
   • "Action" means an on-stage attempt to achieve the Goal that meets
     resistance. Purely logistical/administrative steps (asking a porter,
     bandaging, scheduling, riding a train) are NOT sufficient unless they are
     the means to the Goal and meet resistance on-stage.

B) ERAC → dramatic_sequel
   • Threshold: at least 2 of {{Emotion, Reason, Anticipation, Choice}} present,
     AND no on-stage Conflict/Outcome inside the segment.
   • Typical cues: recovery or instability (dazed/weak), recalling events,
     deliberation about options/costs/risks (“too far to go”), and a decision
     or commitment (“I determined/decided…”).

C) If neither threshold is met:
   • Label narrative_scene if time/place unity is clear.
   • Otherwise label other.

CONSISTENCY CONSTRAINTS (must hold)
- If label == dramatic_scene:
  • checks.gacd.has_action == true
  • checks.gacd.has_conflict == true
  • checks.gacd.outcome in {{ "Disaster", "Success", "Unclear" }} (not "None")
  • At least one GACD evidence quote present.
- If label == dramatic_sequel:
  • At least two of {{checks.erac.has_emotion, has_reason, has_anticipation,
    has_choice}} are true.
  • checks.gacd.has_conflict == false
  • checks.gacd.outcome in {{ "None", "Unclear" }}
  • At least one ERAC evidence quote present.

COMMON CONFUSIONS TO AVOID
- Sequel vs Narrative: Recovery + deliberation + decision/commitment is
  dramatic_sequel, not narrative_scene.
- Action vs Logistics: Asking directions, medical care, or routine travel is
  **logistical** unless it meets resistance that creates conflict in the moment.
- "Morning-after" recovery with planning typically indicates dramatic_sequel.

OUTPUT POLICY
- Return ONLY valid JSON (no prose outside JSON). Keep evidence fields ≤ 160
  chars each. Do not fabricate conflict/outcome if none occurs on-stage.
"""

SCENE_SEMANTICS_USER_PROMPT_TEMPLATE = """
Read the SEGMENT text below and return a JSON object under key "judgment"
with your classification and checks. Base your decision strictly on the text.
Apply the Decision Rubric and enforce the Consistency Constraints.

Return ONLY JSON with this shape:
{{
  "judgment": {{
    "label": "dramatic_scene" | "dramatic_sequel" | "narrative_scene" | "other",
    "reason": "<2–4 sentences explaining the label; cite concrete cues>",
    "confidence": 0.0,
    "checks": {{
      "time_place_unity": true | false,
      "gacd": {{
        "has_goal": true | false,
        "has_action": true | false,
        "has_conflict": true | false,
        "outcome": "Disaster" | "Success" | "Unclear" | "None"
      }},
      "erac": {{
        "has_emotion": true | false,
        "has_reason": true | false,
        "has_anticipation": true | false,
        "has_choice": true | false
      }}
    }},
    "evidence": {{
      "time": "<if stated or implied, else \"\">",
      "place": "<if stated or implied, else \"\">",
      "characters": ["<main character(s)>"],
      "quotes": {{
        "goal": "<≤160 chars or \"\">",
        "action": "<≤160 chars or \"\">",
        "conflict": "<≤160 chars or \"\">",
        "outcome": "<≤160 chars or \"\">",
        "emotion": "<≤160 chars or \"\">",
        "reason": "<≤160 chars or \"\">",
        "anticipation": "<≤160 chars or \"\">",
        "choice": "<≤160 chars or \"\">"
      }}
    }}
  }}
}}

SEGMENT:
\"\"\"{story_text}\"\"\"
"""


def make_semantics_extractor(client: Any) -> llm_extractor.JSONPromptExtractor:
    """Create a JSONPromptExtractor configured for per-segment semantics.

    Args:
        client: OpenAI-like client (supports chat.completions.create).

    Returns:
        Configured JSONPromptExtractor that returns a dict under key "judgment".
    """
    return llm_extractor.JSONPromptExtractor(
        client=client,
        system_prompt=SCENE_SEMANTICS_SYSTEM_PROMPT,
        user_prompt_template=SCENE_SEMANTICS_USER_PROMPT_TEMPLATE,
        output_key="judgment",
        default_model="gpt-4o",
        temperature=0.2,
        force_json=True,
        text_indexer=None,  # segment-level: no indexing
        result_aligner=None,  # segment-level: no alignment
        result_validator=None,  # optional: add later if desired
    )


def evaluate_segment_semantics(
    extractor: llm_extractor.JSONPromptExtractor,
    segment_text: str,
    model_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Evaluate one segment's semantics.

    Args:
        extractor: Instance returned by make_scene_semantics_extractor.
        segment_text: The raw text of a single segment.
        model_name: Optional model override.

    Returns:
        The extractor result dict. The semantic judgment is in
        result['extracted_output'].
    """
    return extractor(segment_text, model_name=model_name)


def annotate_segments_with_semantics(
    story_text: str,
    segments: List[Dict[str, Any]],
    extractor: llm_extractor.JSONPromptExtractor,
    model_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Attach semantic judgments to each segment dict.

    Args:
        story_text: Full canonical story text (used to slice segments).
        segments: List of segment dicts with 'start_char'/'end_char'.
        extractor: Instance from make_scene_semantics_extractor.
        model_name: Optional model override.

    Returns:
        The same list with each segment augmented by a 'semantic' field:
        segment['semantic'] = extracted judgment dict (or None on failure).

    Raises:
        ValueError: If a segment has invalid or missing offsets.
    """
    n = len(story_text)
    out: List[Dict[str, Any]] = []

    for seg in segments:
        s = seg.get("start_char")
        e = seg.get("end_char")
        if not (isinstance(s, int) and isinstance(e, int) and 0 <= s < e <= n):
            raise ValueError(
                f"Segment {seg.get('segment_id', '?')} has invalid offsets: {s}, {e}"
            )
        text = story_text[s:e]
        result = extractor(text, model_name=model_name)
        seg_copy = dict(seg)
        seg_copy["segment_text"] = text
        seg_copy["segment_eval"] = result.get("extracted_output")
        out.append(seg_copy)

    return out


def display_annotated_segments(annotated_segments: List[Dict[str, Any]]) -> None:
    """Pretty-print a list of segments with attached semantic judgments."""
    for segment in annotated_segments:
        display_annotated_segment(segment)


def display_annotated_segment(segment: Dict[str, Any]) -> None:
    """Pretty-print one segment with attached semantic judgment."""
    segment_type = segment.get("segment_type", "unknown")
    confidence = segment.get("confidence", -1.0)
    evaluation = segment.get("segment_eval", {})
    if evaluation:
        audited_type = evaluation.get("label", "unknown")
        audited_confidence = evaluation.get("confidence", -1.0)
    else:
        audited_type = "N/A"
        audited_confidence = -1.0
    if segment_type == audited_type:
        print(
            f"Segment ID: {segment.get('segment_id', '?')}, "
            f"Type: {segment_type}, Confidence: {confidence}"
        )
    else:
        print(
            f"Segment ID: {segment.get('segment_id', '?')}, "
            f"Type: MISMATCH - extracted type DOES NOT match audited type!"
        )
    print(f" - Summary: {utils.sm(segment.get('summary', ''), limit=100)}")

    print(f" - Segment Type: {segment_type}, Confidence: {confidence}")
    print(f"   - Reason: {utils.sm(segment.get('reason', ''), limit=100)}")
    if segment.get("cohesion"):
        print(f"   - Cohesion: {segment.get('cohesion', {})}")
    if segment.get("gacd"):
        print(f"   - GACD: {segment.get('gacd')}")
    if segment.get("erac"):
        print(f"   - ERAC: {segment.get('erac')}")

    if evaluation:
        reason = evaluation.get("reason", "")
        print(f" - Audited Type: {audited_type}, Confidence: {audited_confidence}")
        print(f"   - Reason: {reason}")
        checks = evaluation.get("checks", {})
        print(f"   - Checks: {checks}")
        evidence = evaluation.get("evidence", {})
        print(f"   - Evidence: {evidence}")
    segment_text = segment.get("segment_text", "")
    preview = utils.sm(normalize_preview(segment_text), limit=100)
    print(f" - Text Preview: {preview}")
    print()


def normalize_preview(s: str) -> str:
    """Normalize a segment preview for display."""
    if not s:
        return ""
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"\n{2,}", "\u2029", s)  # mark paragraph breaks
    s = s.replace("\n", " ")  # single newlines -> spaces
    s = re.sub(r"[ \t\u00A0]+", " ", s).strip()
    return s.replace("\u2029", "\n")


ALLOWED_SCENE_TYPES = ["dramatic_scene", "dramatic_sequel", "narrative_scene", "other"]


def normalize_label(label: str) -> str:
    """Re-label unknown scene types to "unknown".

    We are deliberately strict here to avoid typos and unexpected values.

    Args:
        label: Raw label (e.g., 'Dramatic Scene', 'dramatic_scene').

    Returns:
        One of: 'dramatic_scene', 'dramatic_sequel', 'narrative_scene',
        'other', 'unknown'.
    """
    return label if label in ALLOWED_SCENE_TYPES else "unknown"


def summarize_type_agreement(story_data: Dict[str, Any]) -> Dict[str, Any]:
    """Summarize agreement/disagreement counts across segments.

    Args:
        story_data: A story payload (typically output of `attach_type_agreement`).

    Returns:
        Dict with counts and percentages:
        {
          "segments_total": int,
          "agreements": int,
          "disagreements": int,
          "agreement_pct": float,   # 0.0..100.0
          "by_extractor": {type: count, ...},
          "by_auditor": {type: count, ...}
        }
    """
    segments = story_data.get("segments") or []
    if not isinstance(segments, list):
        segments = []

    by_extractor = {
        "dramatic_scene": 0,
        "dramatic_sequel": 0,
        "narrative_scene": 0,
        "other": 0,
        "unknown": 0,
    }
    by_auditor = {
        "dramatic_scene": 0,
        "dramatic_sequel": 0,
        "narrative_scene": 0,
        "other": 0,
        "unknown": 0,
    }

    agreements = 0
    total = 0

    for seg in segments:
        # Ensure we’re using normalized values even if attach_type_agreement
        # hasn’t been run yet.
        whole = normalize_label(seg.get("whole_story_type") or seg.get("segment_type"))
        per_scene = normalize_label(
            seg.get("per_scene_type") or (seg.get("segment_eval") or {}).get("label")
        )

        by_extractor[whole] = by_extractor.get(whole, 0) + 1
        by_auditor[per_scene] = by_auditor.get(per_scene, 0) + 1

        total += 1
        if whole == per_scene:
            agreements += 1

    disagreements = max(0, total - agreements)
    agreement_rate = (agreements / total) if total else 0.0

    return {
        "segments_total": total,
        "agreements": agreements,
        "disagreements": disagreements,
        "agreement_rate": agreement_rate,
        "by_extractor": by_extractor,
        "by_auditor": by_auditor,
    }
