#!/usr/bin/env python
# coding: utf-8

# # Reboot of LCATS Story Analysis

from dataclasses import dataclass
from datetime import date
from typing import List, Dict, Callable, Optional
import json
import os
import re
import sys
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import dotenv
from openai import OpenAI
import tiktoken

# Add the parent directory to the path so we can import modules from the parent directory.
module_path = os.path.abspath(os.path.join('..'))
if module_path not in sys.path:
    sys.path.append(module_path)

from lcats import chunking
from lcats import extraction
from lcats import stories
from lcats import utils
from lcats.datasets import torchdata
from lcats.gatherers import extractors


# If the following code is run from lcats/notebooks in VSCode and the data is in lcats/data ...
CURRENT_PATH = os.path.abspath(os.curdir)  # This is where the notebook is executing.
PROJECT_ROOT = os.path.dirname(CURRENT_PATH)   # This should be the root of the project.
DEV_CORPUS = os.path.abspath(os.path.join(PROJECT_ROOT, 'data'))  # Local copy of the data.
DEV_OUTPUT = os.path.abspath(os.path.join(PROJECT_ROOT, 'output'))  # Local copy of the data.
GIT_CORPUS = os.path.abspath(os.path.join(PROJECT_ROOT, '../corpora'))  # Data in the git repo.
OPENIA_API_KEYS_ENV = os.path.abspath(os.path.join(PROJECT_ROOT, '../.secrets/openai_api_keys.env'))  # Local OpenAI API key.

def check_path(path, description):
    if os.path.exists(path):
        print(f"Found {description} at: {path}")
    else:
        print(f"Missing {description} from: {path}")

check_path(DEV_CORPUS, "DEV_CORPUS")
check_path(DEV_OUTPUT, "DEV_OUTPUT")
check_path(GIT_CORPUS, "GIT_CORPUS")
check_path(OPENIA_API_KEYS_ENV, "OPENIA_API_KEYS_ENV")


dotenv.load_dotenv(OPENIA_API_KEYS_ENV)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
print(OPENAI_API_KEY)


client = OpenAI()
print(f"Loaded OpenAI client: {client} with version: {client._version}")

# If run from within a notebook, the corpora root is two paths up from the notebook's location.
CORPORA_ROOT = GIT_CORPUS  # Checked-in corpora
# CORPORA_ROOT = DEV_CORPUS  # Command line working corpora

# Now load the corpora
corpora = stories.Corpora(CORPORA_ROOT)

print("Loaded corpora:")
print(f" - root: {corpora.corpora_root}")
print(f" - corpora: {len(corpora.corpora)}")
print(f" - stories: {len(corpora.stories)}")
print()
print(f"Example story: corpora.stories[0]:")
print(corpora.stories[0])


# In[ ]:


example_story = corpora.stories[0]
print(f"Story type: {type(example_story)} with a body of {len(example_story.body)} characters.")




def make_serializable(result, nonserializable_key="response"):
    """
    Remove a non-serializable key from the result dictionary.

    Args:
        result (dict): The dictionary to clean.
        nonserializable_key (str): The key to remove if present.

    Returns:
        dict: A shallow copy of the dictionary with the specified key removed.
    """
    result = dict(result)  # shallow copy to avoid mutating original
    result.pop(nonserializable_key, None)
    return result

def extract_all_and_write(corpora, extractor, model_name, output_dir, file_namer, serializer):
    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Create a subdirectory for the model
    model_dir = os.path.join(output_dir, "scene_extraction", model_name)
    os.makedirs(model_dir, exist_ok=True)

    for story in corpora.stories:
        filename = file_namer(story.name) + "-scenes.json"
        filepath = os.path.join(model_dir, filename)

        # Skip already-processed files
        if os.path.exists(filepath):
            print(f"Skipping already processed story: {story.name}")
            continue

        try:
            print(f"Processing story: {story.name}")
            result = extractor(story.body, model_name=model_name)
            serialized_result = serializer(result)
            with open(filepath, "w") as f:
                json.dump(serialized_result, f, indent=2)
        except Exception as e:
            print(f"Error processing {story.name}: {e}")

    print("Scene extraction complete.")





def fetch_story_extraction(
    story,
    model_name,
    output_dir,
    file_namer
    ):
    # Determine file path
    model_dir = os.path.join(output_dir, "scene_extraction", model_name)
    os.makedirs(model_dir, exist_ok=True)
    filename = file_namer(story.name) + "-scenes.json"
    filepath = os.path.join(model_dir, filename)

    # If the file exists and we're not forcing recomputation, load and return
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return json.load(f)
    return None

def fetch_or_compute_story_extraction(
    story,
    extractor,
    model_name,
    output_dir,
    file_namer,
    serializer,
    force=False
):
    """
    Fetch the scene/sequel extraction for a story, loading from disk if available,
    or computing and saving it otherwise.

    Parameters:
        story: A Story object with a .name and .body attribute.
        extractor: Function that extracts structured data from story.body.
        model_name: Name of the model used for the extraction (e.g., 'gpt-4o').
        output_dir: Root directory where extractions are stored.
        file_namer: Function to turn a story name into a safe filename.
        serializer: Function that removes or transforms non-serializable objects in the result.
        force: If True, reprocess the story even if a saved result exists.

    Returns:
        The structured extraction result (as loaded from JSON).
    """

    # Determine file path
    model_dir = os.path.join(output_dir, "scene_extraction", model_name)
    os.makedirs(model_dir, exist_ok=True)
    filename = file_namer(story.name) + "-scenes.json"
    filepath = os.path.join(model_dir, filename)

    # If the file exists and we're not forcing recomputation, load and return
    if not force and os.path.exists(filepath):
        with open(filepath, "r") as f:
            return json.load(f)

    # Otherwise compute, serialize, save, and return
    result = extractor(story.body, model_name=model_name)
    serializable_result = serializer(result)
    with open(filepath, "w") as f:
        json.dump(serializable_result, f, indent=2)
    return serializable_result


example_story = corpora.stories[0]
example_extraction = fetch_story_extraction(
    example_story,
    model_name="gpt-4o",
    output_dir=DEV_OUTPUT,
    file_namer=extractors.title_to_filename,
)
len(example_extraction['parsed_output']['events'])

def count_paragraphs(text):
    count = 0

    for possible_paragraph in text.split("\n\n"):
        if len(possible_paragraph.strip()) == 0:
            continue
        count = count + 1

    return (count)

def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))

def get_scenes(events):
    scenes = []
    for event in events:
        if event['event_type'] == 'scene':
            scenes.append({event['event_text'], event['reason']})

    return scenes

def build_indexes(extracted_story_text: str, model_name="gpt-3.5-turbo") -> Dict:
    messages = "Take the following extracted scene text and reason and produce a JSON structure consisting of 'goal', 'action', and 'catastrophe.   Make the elements of the JSON structure generic."
    
    scenes_parts = []
    for scene in get_scenes(extracted_story_text):
        message_to_send = [{'role':'user', 'content': "'" + messages + ' ' + list(scene)[0] + ' ' + list(scene)[1] + "'"}]

        response = client.chat.completions.create(
            model=model_name,
            messages=message_to_send, 
            temperature=0.2,
        )

        raw_output = response.choices[0].message.content

        try:
            parsed_output = utils.extract_json(raw_output)
            parsing_error = None
        except json.JSONDecodeError as exc:
            parsed_output = None
            parsing_error = str(exc)

        scenes_parts.append(parsed_output)

    return scenes_parts

def collate_story_extractions(corpora, model_name, output_dir):
    """
    Collate the story extractions into a DataFrame.
    """
    extractions = {}
    statistics = []
    for story in corpora.stories:
        # Get metadata about the story
        story_year = story.metadata['year']
        if story_year == "Not found" or story_year == "Unknown" or story_year == "Multiple authors":
            story_year = -1
        else:
            story_year = int(story_year)
            
        story_text = story.body
        characters = len(story_text)
        tokens = count_tokens(story_text, model_name)

        # Get the extraction for the story
        extraction = fetch_story_extraction(
            story,
            model_name=model_name,
            output_dir=output_dir,
            file_namer=extractors.title_to_filename,
        )

        number_paragraphs = count_paragraphs(story_text)
        
        extractions[story.name] = extraction
        if extraction is None:
            # print(f"Missing extraction for story: {story.name}")
            parsed = False
            events = []
            scenes = []
            sequels = []
            nones = []
        else:
            print(f"Processing extraction for story: {story.name}")
            parsed = True
            events = extraction['parsed_output']['events']

            GoodParse = True
            for i in range(0, len(events)):
                if 'event_type' not in list(events[i].keys()):
                    GoodParse = False
                            
            if GoodParse:
                scenes = [e for e in events if e['event_type'] == 'scene']
                sequels = [e for e in events if e['event_type'] == 'sequel']
                nones = [e for e in events if e['event_type'] == 'none']
            else:
                print("     Problem with missing event type")
                extractions[story.name] = None
                parsed = False
                events = []
                scenes = []
                sequels = []
                nones = []
                

        # Append the statistics for this story
        statistics.append({
            "story_name": story.name,
            "characters": characters,
            "tokens": tokens,
            "parsed": int(parsed),
            "events": len(events),
            "scenes": len(scenes),
            "sequels": len(sequels),
            "nones": len(nones), 
            "paragraphs": number_paragraphs,
            "year": story_year
        })
    return extractions, pd.DataFrame(statistics)

gpt_4o_data, gpt_4o_df = collate_story_extractions(
    corpora,
    model_name="gpt-4o",
    output_dir=DEV_OUTPUT,
)
print(gpt_4o_df.describe())
gpt_4o_df.sum()

gpt_35_data, gpt_35_df = collate_story_extractions(
    corpora,
    model_name="gpt-3.5-turbo",
    output_dir=DEV_OUTPUT,
)
print(gpt_35_df.describe())
gpt_35_df.sum()

difference = []
comparisons = []
for story in corpora.stories:
    gpt_4o_extraction = gpt_4o_data[story.name]
    gpt_35_extraction = gpt_35_data[story.name]
    if gpt_4o_extraction is None or gpt_35_extraction is None:
        continue
    gpt_4o_tokens = gpt_4o_df[gpt_4o_df["story_name"] == story.name]['tokens'].values[0]
    gpt_35_tokens = gpt_35_df[gpt_35_df["story_name"] == story.name]['tokens'].values[0]
    gpt_4o_events = gpt_4o_extraction['parsed_output']['events']
    gpt_35_events = gpt_35_extraction['parsed_output']['events']
    gpt_4o_scenes = [e for e in gpt_4o_events if e['event_type'] == 'scene']
    gpt_35_scenes = [e for e in gpt_35_events if e['event_type'] == 'scene']
    gpt_4o_sequels = [e for e in gpt_4o_events if e['event_type'] == 'sequel']
    gpt_35_sequels = [e for e in gpt_35_events if e['event_type'] == 'sequel']
    gpt_4o_nones = [e for e in gpt_4o_events if e['event_type'] == 'none']
    gpt_35_nones = [e for e in gpt_35_events if e['event_type'] == 'none']
    year = gpt_4o_df[gpt_4o_df["story_name"] == story.name]['year'].values[0]
        
    number_paragraphs = count_paragraphs(story.body)
    
    print(f"Story: {story.name}")
    print(f" - paragraphs: {number_paragraphs}")
    print(f" - characters: {len(story.body)}")
    print(f" - tokens: {gpt_4o_tokens} (gpt-4o) vs {gpt_35_tokens} (gpt-3.5-turbo)")
    print(f" - events: {len(gpt_4o_events)} (gpt-4o) vs {len(gpt_35_events)} (gpt-3.5-turbo)")
    print(f" - scenes: {len(gpt_4o_scenes)} (gpt-4o) vs {len(gpt_35_scenes)} (gpt-3.5-turbo)")
    print(f" - sequels: {len(gpt_4o_sequels)} (gpt-4o) vs {len(gpt_35_sequels)} (gpt-3.5-turbo)")
    print(f" - nones: {len(gpt_4o_nones)} (gpt-4o) vs {len(gpt_35_nones)} (gpt-3.5-turbo)")


    difference.append({
        "story_name": story.name,
        "model": "",
        "tokens": gpt_4o_tokens,
        "avg_tokens": (gpt_4o_tokens+gpt_35_tokens)/2, 
        "diff_tokens": gpt_4o_tokens-gpt_35_tokens, 
        "events": len(gpt_4o_events)-len(gpt_35_events),
        "scenes": len(gpt_4o_scenes)-len(gpt_35_scenes),
        "sequels": len(gpt_4o_sequels)-len(gpt_35_sequels),
        "nones": len(gpt_4o_nones)-len(gpt_35_nones), 
        "paragraphs": number_paragraphs
    })
    
    comparisons.append({
        "story_name": story.name,
        "model": "gpt-4o",
        "tokens": gpt_4o_tokens,
        "events": len(gpt_4o_events),
        "scenes": len(gpt_4o_scenes),
        "sequels": len(gpt_4o_sequels),
        "nones": len(gpt_4o_nones), 
        "paragraphs": number_paragraphs,
        "year": year
    })
    comparisons.append({
        "story_name": story.name,
        "model": "gpt-3.5-turbo",
        "tokens": gpt_35_tokens,
        "events": len(gpt_35_events),
        "scenes": len(gpt_35_scenes),
        "sequels": len(gpt_35_sequels),
        "nones": len(gpt_35_nones),
        "paragraphs": number_paragraphs,
        "year": year
    })


comparison_df = pd.DataFrame(comparisons)
difference_df = pd.DataFrame(difference)
difference_df['x_axis'] = range(len(difference_df))


print(comparison_df.columns)
print(comparison_df.describe())
comparison_df.head()


common_4o = gpt_4o_df[gpt_35_df["parsed"] == 1]
common_35 = gpt_35_df[gpt_35_df["parsed"] == 1]
print("Common stories with valid extractions:")
print(f" - gpt-4o: {len(common_4o)}")
print(common_4o.describe())
print(f" - gpt-3.5-turbo: {len(common_35)}")
print(common_35.describe())

def plot_columns_vs(df, x_col, y_col, y_low = 0, y_high = 300, log=False, hue_col=None, legend=""):
    plt.figure(figsize=(10, 6))
    sns.scatterplot(data=df, x=x_col, y=y_col, hue=hue_col)
    plt.xlabel(x_col)
    plt.ylabel(y_col)
    plt.ylim(y_low, y_high)
    if log:
        plt.xscale('log')
    plt.title(f"{y_col} vs {x_col}")
    plt.legend(title=hue_col)
    if len(legend) > 0:
        plt.legend(title = "GPT 4 events - GPT 3 events")
    plt.grid(True)
    plt.show()

def showPlots():
    plot_columns_vs(comparison_df, 'tokens', 'events', hue_col='model')
    plot_columns_vs(comparison_df, 'tokens', 'scenes', hue_col='model')
    plot_columns_vs(comparison_df, 'tokens', 'sequels', hue_col='model')
    plot_columns_vs(comparison_df, 'tokens', 'nones', hue_col='model')
    plot_columns_vs(comparison_df, 'paragraphs', 'events', hue_col='model')


def analyzeExtractions (model="gpt-3.5-turbo", showMissing=True):
    count = 0

    for story in corpora.stories:
        if model=="gpt-4o":
            if gpt_4o_data[story.name] is None:
                if showMissing:
                    print(story.name)
                continue
            else:
                count = count + 1
        if model=="gpt-3.5-turbo":
            if gpt_35_data[story.name] is None:
                if showMissing:
                    print(story.name)
                continue
            else:
                count = count + 1

    return count



# KMM Want to stop here BUT keep the work A.F. did for use later?  
foo()

# Max tokens divided by min scenes gives us a rough estimate of how many tokens are needed per scene.
estimated_tokens_per_scene = float(comparison_df['tokens'].max() / comparison_df['scenes'].min())
estimated_tokens_per_scene


example_story = corpora.stories[0]
story_text = example_story.body
chunks = chunking.chunk_story(story_text, max_tokens=6000, overlap_tokens=0, model_name="gpt-3.5-turbo")

print(f"Chunked story into {len(chunks)} parts.")
for index, chunk in enumerate(chunks):
    print(f"Chunk {index} ({len(chunk.text)} chars):")
    print(chunk.text[:100] + "...")
    print()


example_story = corpora.stories[0]
example_text = example_story.body

example_chunks = chunking.chunk_story(example_text, max_tokens=6000, overlap_tokens=200, model_name="gpt-3.5-turbo")
chunking.display_chunks(example_chunks)


# ### Extracting Scenes - LASTREVIEW

# In[ ]:


@dataclass
class SceneSpan:
    chunk_index: int
    relative_start: int
    relative_end: int
    scene_type: str
    text: str
    offset: int  # character offset in original story

    def absolute_start(self) -> int:
        return self.offset + self.relative_start

    def absolute_end(self) -> int:
        return self.offset + self.relative_end

SCENE_SEQUEL_SYSTEM_PROMPT = """
You are a helpful assistant that breaks down stories into structured narrative events.

Each event must be labeled as:
- "scene": a segment where a character pursues a goal, leading to success or failure.
- "sequel": a segment where a character reacts to the outcome, reflects, and formulates a new plan.
- "none": a segment that does not clearly fit into either category (e.g., exposition or transition).

You MUST output a list of events as a JSON dictionary with one key: "events".

Each event must include:
- "type": one of "scene", "sequel", or "none"
- "reason": a brief explanation of why you classified it this way
- "text": the exact event text, copied from the story
- "start_char": the starting character offset of the event in the original story
- "end_char": the ending character offset (exclusive)

Do NOT include any additional explanation or formatting.
Only return valid JSON.
"""

SCENE_SEQUEL_USER_PROMPT_TEMPLATE = """
I will give you a story in plain text.

Please identify contiguous narrative segments that represent:
- scenes (goal-driven attempts)
- sequels (reflections after outcomes)
- or neither ("none" for other material)

For each segment, return a dictionary with:
- "type": "scene", "sequel", or "none"
- "reason": a brief explanation of why you classified it this way
- "text": the exact span of text from the story
- "start_char": starting character index of this span in the story
- "end_char": ending character index (exclusive)

Return a single JSON object with a key named "events" and a list of these entries.

The output MUST be valid JSON and include ONLY the JSON, no explanation or comments.

STORY:
\"\"\"{story_text}\"\"\"
"""

def build_scene_sequel_prompt(story_text: str) -> list:
    return [
        {"role": "system", "content": SCENE_SEQUEL_SYSTEM_PROMPT},
        {"role": "user", "content": SCENE_SEQUEL_USER_PROMPT_TEMPLATE.format(story_text=story_text)}
    ]


def extract_scenes_and_sequels(story_text: str, model_name="gpt-3.5-turbo") -> Dict:
    messages = build_scene_sequel_prompt(story_text)

    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=0.2,
    )

    raw_output = response.choices[0].message.content

    try:
        parsed_output = utils.extract_json(raw_output)
        parsing_error = None
    except json.JSONDecodeError as exc:
        parsed_output = None
        parsing_error = str(exc)

    scene_spans: List[SceneSpan] = []
    extraction_error = None

    if isinstance(parsed_output, dict) and "events" in parsed_output:
        for i, event in enumerate(parsed_output["events"]):
            scene_text = event.get("text", "").strip()
            scene_type = event.get("type", "scene")

            # Match scene_text in story_text to find offsets
            match = re.search(re.escape(scene_text), story_text)
            if match:
                start_char = match.start()
                end_char = match.end()
            else:
                start_char = None
                end_char = None

            scene_spans.append(SceneSpan(
                chunk_index=0,  # Actual index will be set later by tail extraction logic
                relative_start=0,  # Will be calculated by offset adjustment later
                relative_end=0,
                scene_type=scene_type,
                text=scene_text,
                offset=start_char if start_char is not None else 0  # fallback
            ))

            # Patch relative positions if match succeeded
            if match:
                scene_spans[-1].relative_start = 0  # initially 0, will be corrected in stitching
                scene_spans[-1].relative_end = end_char - start_char

    else:
        scene_spans = []
        extraction_error = "Expected 'events' key in JSON response."

    return {
        "story_text": story_text,
        "model_name": model_name,
        "messages": messages,
        "response": response,
        "raw_output": raw_output,
        "parsed_output": parsed_output,
        "extracted_output": scene_spans,
        "parsing_error": parsing_error,
        "extraction_error": extraction_error,
    }


def span_is_complete(span: Dict) -> bool:
    """
    Simple heuristic to determine if a scene span is complete.
    """
    text = span.get("text", "").strip()
    return text.endswith(".") and not text.endswith("...") and len(text) > 20

def get_span_from_raw(
    raw: Dict,
    chunk_index: int,
    chunk_input_text: str,
    carryover_len: int,
    chunk_offset: int
) -> Optional[SceneSpan]:
    """
    Convert a raw dict (LLM output) into a SceneSpan object.
    Uses fallback matching if start_char and end_char are missing.
    """
    scene_text = raw.get("text", "").strip()
    scene_type = raw.get("type", "scene")

    start_char = raw.get("start_char")
    end_char = raw.get("end_char")

    if start_char is None or end_char is None:
        match = re.search(re.escape(scene_text), chunk_input_text)
        if not match:
            return None
        start_char = match.start()
        end_char = match.end()

    adjusted_start = max(0, start_char - carryover_len)
    adjusted_end = max(0, end_char - carryover_len)
    print(f"Processing span: {scene_text} (start: {start_char}, end: {end_char}) "
          f"-> adjusted start: {adjusted_start}, adjusted end: {adjusted_end}")
    if adjusted_end <= 0:
        print(f"Skipping span entirely in carryover: {scene_text}")
        return None  # entirely in carryover, skip

    return SceneSpan(
        chunk_index=chunk_index,
        relative_start=adjusted_start,
        relative_end=adjusted_end,
        scene_type=scene_type,
        text=chunk_input_text[start_char:end_char],
        offset=chunk_offset
    )

def extract_carryover_text(
    raw_span: Dict,
    chunk_input_text: str
) -> str:
    """
    Extract tail of the final scene span for prepending to the next chunk.
    Falls back on re-matching if no indices are given.
    """
    last_text = raw_span.get("text", "")
    start = raw_span.get("start_char")
    end = raw_span.get("end_char")

    if start is not None and end is not None:
        return chunk_input_text[start:end]

    match = re.search(re.escape(last_text), chunk_input_text)
    return chunk_input_text[match.start():match.end()] if match else ""


def extract_scene_spans_with_tail(
    chunks: List[Chunk],
    model_name: str,
    extract_fn: Callable[[str, str], Dict]
) -> List[SceneSpan]:
    stitched_spans: List[SceneSpan] = []
    carryover_text = ""

    for i, chunk in enumerate(chunks):
        print(f"Processing chunk {i + 1}/{len(chunks)}: {len(chunks[i].text)} chars")
        chunk_input_text = carryover_text + chunk.text
        carryover_len = len(carryover_text)

        # Call the model extractor
        result = extract_fn(chunk_input_text, model_name=model_name)
        raw_spans = result.get("extracted_output", [])
        print(f"Extracted {len(raw_spans)} spans from chunk {i + 1}")

        # Try to convert all spans to SceneSpan
        for raw in raw_spans:
            span = get_span_from_raw(
                raw,
                chunk_index=i,
                chunk_input_text=chunk_input_text,
                carryover_len=carryover_len,
                chunk_offset=chunk.start_char
            )
            if span:
                stitched_spans.append(span)

        # Setup carryover if final span is incomplete
        if raw_spans and not span_is_complete(raw_spans[-1]):
            carryover_text = extract_carryover_text(raw_spans[-1], chunk_input_text)
        else:
            carryover_text = ""

    return stitched_spans


example_chunk = example_chunks[0]
example_text = example_chunk.text
example_prompt = build_scene_sequel_prompt(example_text)
example_result = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=example_prompt,
    temperature=0.2,
)
example_raw_output = example_result.choices[0].message.content
example_parsed_output = utils.extract_json(example_raw_output)
example_spans = example_parsed_output["events"]


# In[ ]:


len(example_spans)


# In[ ]:


example_spans[1]


# In[ ]:


def summarize(text, length=72):
    """
    Summarize the text to a specified length.
    """
    if len(text) <= length:
        return text
    prefix = length // 2
    return text[:prefix] + "..." + text[-(length - prefix):]


for i, span in enumerate(example_spans):
    # print(span)
    print(f"Span {i} type: {span.get('type')}, text: {summarize(span.get('text', ''))}")
    start_char = span.get("start_char")
    end_char = span.get("end_char")
    if start_char is not None and end_char is not None:
        span_text = example_text[start_char:end_char]
        print(f" - start: {start_char}, end: {end_char}, text: {summarize(span_text)}...")


# In[ ]:


example_chunk = example_chunks[0]
extraction = extract_scenes_and_sequels(
    example_chunk.text, model_name="gpt-3.5-turbo")
extraction['extracted_output'][:5]


# In[ ]:


extract_scene_spans_with_tail(
    example_chunks,
    model_name="gpt-3.5-turbo",
    extract_fn=extract_scenes_and_sequels
)


# In[ ]:


len(chunks), chunks[0][:100], chunks[-1][:100]


# In[ ]:


for index, chunk in enumerate(chunks):
    print(f"Chunk {index} ({len(chunk)} chars):")
    print(chunk[:100] + "...")
    print()


# In[ ]:




