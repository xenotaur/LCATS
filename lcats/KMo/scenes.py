#!/usr/bin/env python
# coding: utf-8

# # Reboot of LCATS Story Analysis

# ## Imports




from datetime import date
import json
import os
import sys
import pandas as pd
import tiktoken

# Third-party modules

import dotenv
from openai import OpenAI


# Add imports from within the project

# Add the parent directory to the path so we can import modules from the parent directory.
module_path = os.path.abspath(os.path.join('..'))
if module_path not in sys.path:
    sys.path.append(module_path)

from lcats import stories
from lcats import utils
from lcats.datasets import torchdata
from lcats.gatherers import extractors


# ## Project Setup

# ### Path Setup




# If the following code is run from lcats/notebooks in VSCode and the data is in lcats/data ...
CURRENT_PATH = os.path.abspath(os.curdir)  # This is where the notebook is executing.
PROJECT_ROOT = os.path.dirname(CURRENT_PATH)   # This should be the root of the project.
DEV_CORPUS = os.path.abspath(os.path.join(PROJECT_ROOT, 'data'))  # Local copy of the data.
DEV_OUTPUT = os.path.abspath(os.path.join(PROJECT_ROOT, 'output'))  # Local copy of the data.
GIT_CORPUS = os.path.abspath(os.path.join(PROJECT_ROOT, '../corpora'))  # Data in the git repo.
OPENAI_API_KEYS_ENV = os.path.abspath(os.path.join(PROJECT_ROOT, '../.secrets/openai_api_keys.env'))  # Local OpenAI API key.

def check_path(path, description):
    if os.path.exists(path):
        print(f"Found {description} at: {path}")
    else:
        print(f"Missing {description} from: {path}")

check_path(DEV_CORPUS, "DEV_CORPUS")
check_path(DEV_OUTPUT, "DEV_OUTPUT")
check_path(GIT_CORPUS, "GIT_CORPUS")
check_path(OPENAI_API_KEYS_ENV, "OPENIA_API_KEYS_ENV")
dotenv.load_dotenv(OPENAI_API_KEYS_ENV)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
print(OPENAI_API_KEY)

client = OpenAI()
print(f"Loaded OpenAI client: {client} with version: {client._version}")

response = client.responses.create(
    model="gpt-4o",
    input="Write a one-sentence bedtime story about a starship captain visiting a planet."
)

print(f"Story generated on: {date.today()}:")
utils.pprint(response.output_text)

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





example_story = corpora.stories[0]
print(f"Story type: {type(example_story)} with a body of {len(example_story.body)} characters.")


# ## Scene and Sequel Extraction

# Code suggested by ChatGPT




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

def build_scene_sequel_prompt(story_text: str) -> list:
    """
    Build the chat messages for the OpenAI ChatCompletion call.
    """
    return [
        {"role": "system", "content": SCENE_SEQUEL_SYSTEM_PROMPT},
        {"role": "user", "content": SCENE_SEQUEL_USER_PROMPT_TEMPLATE.format(story_text=story_text)}
    ]






def extract_scenes_and_sequels(story_text: str, model_name="gpt-3.5-turbo"):
    global foo_ro, foo_ro2

    messages = build_scene_sequel_prompt(story_text)

    foo_ro2 = messages
    
    # Provide your API key, then:
    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=0.2,  # slightly creative but mostly deterministic
    )

    
    # The assistant response is in response.choices[0].message["content"]
    raw_output = response.choices[0].message.content

    foo_ro = raw_output
    
    # Attempt to parse the JSON
    try:
        parsed_output = utils.extract_json(raw_output)
        parsing_error = None

    except json.JSONDecodeError as exc:
        # The LLM might have returned invalid JSON or additional text around JSON
        # In that case, you can attempt to strip out the JSON portion or re-prompt
        parsed_output = None
        parsing_error = str(exc)

    # Expecting something like: { "events": [ ... ] }
    if isinstance(parsed_output, dict) and "events" in parsed_output:
        extracted_output = parsed_output["events"]
        extraction_error = None
    else:
        # If we didn't get the expected structure, handle fallback
        extracted_output = None
        extraction_error = "Expected 'events' key in JSON response."

    return {
        "story_text": story_text,
        "model_name": model_name,
        "messages": messages,
        "response": response,
        "raw_output": raw_output,
        "parsed_output": parsed_output,
        "extracted_output": extracted_output,
        "parsing_error": parsing_error,
        "extraction_error": extraction_error,
    }

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

def extract_one_and_write(corpora, number, extractor, model_name, output_dir, file_namer, serializer):
    result = None
    
    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Create a subdirectory for the model
    model_dir = os.path.join(output_dir, "scene_extraction", model_name)
    os.makedirs(model_dir, exist_ok=True)

    story = corpora.stories[number]
    
    filename = file_namer(story.name) + "-scenes.json"
    filepath = os.path.join(model_dir, filename)

    # Skip already-processed files
    if os.path.exists(filepath):
        print(f"Skipping already processed story: {story.name}")
        return

    try:
        print(f"Processing story: {story.name}")
        token_count = count_tokens(story.body, model_name)
        
        result = extractor(story.body, model_name=model_name)
        serialized_result = serializer(result)
        with open(filepath, "w") as f:
            json.dump(serialized_result, f, indent=2)
    except Exception as e:
        print(f"Error processing {story.name}: {e}")
        print(result)

    print("Scene extraction complete.")

    return result

def testOne(number):
    return(extract_one_and_write(
        corpora,
        number,
        extract_scenes_and_sequels,
        model_name="gpt-4o",
        output_dir=DEV_OUTPUT,
        file_namer=extractors.title_to_filename,
        serializer=make_serializable))

def testTwo(number):
    return(extract_one_and_write(
        corpora,
        number,
        extract_scenes_and_sequels,
        model_name="gpt-3.5-turbo",
        output_dir=DEV_OUTPUT,
        file_namer=extractors.title_to_filename,
        serializer=make_serializable))

def testName(i, name):
    if name in corpora.stories[i].name:
        print(name + " found at " + str(i))


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

gpt_4o_data = []

def collate_story_extractions(corpora, model_name, output_dir):
    """
    Collate the story extractions into a DataFrame.
    """
    extractions = {}
    statistics = []
    for story in corpora.stories:
        extraction = fetch_story_extraction(
            story,
            model_name=model_name,
            output_dir=output_dir,
            file_namer=extractors.title_to_filename,
        )
        extractions[story.name] = extraction
        if extraction is None:
            # print(f"Missing extraction for story: {story.name}")
            parsed = False
            events = []
            scenes = []
            sequels = []
            nones = []
        else:
            # print(f"Processing extraction for story: {story.name}")
            parsed = True
            events = extraction['parsed_output']['events']
            scenes = [e for e in events if e['event_type'] == 'scene']
            sequels = [e for e in events if e['event_type'] == 'sequel']
            nones = [e for e in events if e['event_type'] == 'none']
        statistics.append({
            "story_name": story.name,
            "characters": len(story.body),
            "parsed": int(parsed),
            "events": len(events),
            "scenes": len(scenes),
            "sequels": len(sequels),
            "nones": len(nones)
        })
    return extractions, pd.DataFrame(statistics)

#for i in range(0,1900):
#    testTwo(i)

def findByName (name):
    for i in range(0, 1901):
        if corpora.stories[i].name == name:
            print(name + " found at " + str(i))

            
    
#example_prompt = build_scene_sequel_prompt(example_story.body)
#example_prompt


#result_gpt_35_turbo = extract_scenes_and_sequels(example_story.body)
#len(result_gpt_35_turbo["extracted_output"]), result_gpt_35_turbo["extracted_output"][:5]

#result_gpt_4o = extract_scenes_and_sequels(
#    corpora.stories[0].body, model_name="gpt-4o")

#len(result_gpt_4o["extracted_output"]), result_gpt_4o["extracted_output"][:5]
#type(corpora.stories[0])

#extract_all_and_write(
#    corpora,
#    extract_scenes_and_sequels,
#    model_name="gpt-4o",
#    output_dir=DEV_OUTPUT,
#    file_namer=extractors.title_to_filename,
#    serializer=make_serializable)

#extract_all_and_write(
#    corpora,
#    extract_scenes_and_sequels,
#    model_name="gpt-3.5-turbo",
#    output_dir=DEV_OUTPUT,
#    file_namer=extractors.title_to_filename,
#    serializer=make_serializable)

#example_story = corpora.stories[0]
#example_extraction = fetch_story_extraction(
#    example_story,
#    model_name="gpt-4o",
#    output_dir=DEV_OUTPUT,
#    file_namer=extractors.title_to_filename,
#)
#len(example_extraction['parsed_output']['events'])

#gpt_4o_data, gpt_4o_df = collate_story_extractions(
#    corpora,
#    model_name="gpt-4o",
#    output_dir=DEV_OUTPUT,
#)
#print(gpt_4o_df.describe())
#gpt_4o_df.sum()

#gpt_35_data, gpt_35_df = collate_story_extractions(
#    corpora,
#    model_name="gpt-3.5-turbo",
#    output_dir=DEV_OUTPUT,
#)
#print(gpt_35_df.describe())
#gpt_35_df.sum()

#for story in corpora.stories:
#    gpt_4o_extraction = gpt_4o_data[story.name]
#    gpt_35_extraction = gpt_35_data[story.name]
#    if gpt_4o_extraction is None or gpt_35_extraction is None:
#        continue
#    gpt_4o_events = gpt_4o_extraction['parsed_output']['events']
#    gpt_35_events = gpt_35_extraction['parsed_output']['events']
#    gpt_4o_scenes = [e for e in gpt_4o_events if e['event_type'] == 'scene']
#    gpt_35_scenes = [e for e in gpt_35_events if e['event_type'] == 'scene']
#    gpt_4o_sequels = [e for e in gpt_4o_events if e['event_type'] == 'sequel']
#    gpt_35_sequels = [e for e in gpt_35_events if e['event_type'] == 'sequel']
#    gpt_4o_nones = [e for e in gpt_4o_events if e['event_type'] == 'none']
#    gpt_35_nones = [e for e in gpt_35_events if e['event_type'] == 'none']
#    print(f"Story: {story.name}")
#    print(f" - characters: {len(story.body)}")
#    print(f" - events: {len(gpt_4o_events)} (gpt-4o) vs {len(gpt_35_events)} (gpt-3.5-turbo)")
#    print(f" - scenes: {len(gpt_4o_scenes)} (gpt-4o) vs {len(gpt_35_scenes)} (gpt-3.5-turbo)")
#    print(f" - sequels: {len(gpt_4o_sequels)} (gpt-4o) vs {len(gpt_35_sequels)} (gpt-3.5-turbo)")
#    print(f" - nones: {len(gpt_4o_nones)} (gpt-4o) vs {len(gpt_35_nones)} (gpt-3.5-turbo)")

#common_4o = gpt_4o_df[gpt_35_df["parsed"] == 1]
#common_35 = gpt_35_df[gpt_35_df["parsed"] == 1]
#print("Common stories with valid extractions:")
#print(f" - gpt-4o: {len(common_4o)}")
#print(common_4o.describe())
#print(f" - gpt-3.5-turbo: {len(common_35)}")
#print(common_35.describe())

#gpt_4o_data[example_story.name]['parsed_output']['events'][:5]

#gpt_35_data[example_story.name]['parsed_output']['events'][:5]


#print("Trying 3 *********************************")
#for i in range(0,1893):
#    testTwo(i)

#print("Trying 4 *********************************")
#for i in range(0,1893):
#    testOne(i)




foo_ro = "Unset"
foo_ro2 = "Unset"



