"""Scene and Sequel analysis using LLMs."""

from lcats.analysis import llm_extractor
    

SCENE_SEQUEL_SYSTEM_PROMPT = """
You are a helpful assistant that breaks down stories into structured events.
Each event is labeled as "scene", "sequel", or "none" (if it doesn't fit exactly).
Follow these definitions:

- scene: a segment where a character with a goal attempts to achieve it, leading to success or disaster.
- sequel: a segment after a disaster or success, where a character reacts, processes emotions, considers options, and forms a new goal.

Your output MUST be valid JSON and only the JSON without any other text or comments.
"""

SCENE_SEQUEL_USER_PROMPT_TEMPLATE = """
I will give you a story in plain text.
1. Read the story carefully.
2. Identify major events or paragraphs that qualify as scenes or sequels (or 'none' if it doesn't clearly fit).
3. For each event, provide:
   - event_text: the text snippet or summary
   - event_type: 'scene' or 'sequel' or 'none'
   - reason: a short explanation of why you classified it that way
4. Return a JSON dictionary with one key named "events" - the output must be valid JSON and only the JSON.
Your output MUST be valid JSON and only the JSON without any other text or comments.

STORY:
\"\"\"{story_text}\"\"\"
"""

def make_scene_sequel_extractor(client):
    return llm_extractor.JSONPromptExtractor(
        client,
        system_prompt=SCENE_SEQUEL_SYSTEM_PROMPT,
        user_prompt_template=SCENE_SEQUEL_USER_PROMPT_TEMPLATE,
        output_key="events",
        default_model="gpt-4o",
        temperature=0.2,
        force_json=True,
    )
