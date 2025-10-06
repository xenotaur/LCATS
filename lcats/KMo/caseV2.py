#!/usr/bin/env python
# coding: utf-8

# Some attempts at indexing, retrieving, and adapting

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
import random
from openai import OpenAI
import tiktoken
from re import sub

#import nltk
#from sklearn.metrics.pairwise import cosine_similarity
#from sklearn.feature_extraction.text import CountVectorizer

import chromadb
from chromadb.utils import embedding_functions

verbose = True

# setting up memory with chromadb
CHROMA_DATA_PATH = "chroma_data/"
EMBED_MODEL = "all-MiniLM-L6-v2"
COLLECTION_NAME = "lcats_stories"
chroma_client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=EMBED_MODEL
)
chroma_memory = chroma_client.get_or_create_collection(
    name=COLLECTION_NAME,
    embedding_function=embedding_func,
    metadata={"hnsw:space": "cosine"},
)

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



# https://www.w3resource.com/python-exercises/string/python-data-type-string-exercise-97.php
# Define a function to convert a string to snake case
def snake_case(s):
    # Replace hyphens with spaces, then apply regular expression substitutions for title case conversion
    # and add an underscore between words, finally convert the result to lowercase
    return '_'.join(
        sub('([A-Z][a-z]+)', r' \1',
        sub('([A-Z]+)', r' \1',
        s.replace('-', ' '))).split()).lower()


def goal_action ():
    for name in gpt_4o_memory:
        print("Working on " + name)
        memory = gpt_4o_memory[name]
        if memory == None:
            continue
        for event in memory['extracted_output']:
            if event != None and event['event_type'] == 'scene' and event['scene_parts'] != None:
                goal = event['scene_parts']['goal']
                action = event['scene_parts']['action']
                print("Goal:   " + goal)
                print("Action: " + action)
                print("")
            
# Some sample situations to test the retrieval on. 
test1 = "I need to find an old friend I've lost contact with."
test2 = "I need to get a promotion instead of it going to my co-worker."
test3 = "I'm lost and need to find my home."
test4 = "I am worried I am going to fail a very important test in a class I am taking."
test5 = "I am dating two people who don't know about each other and I am worried about them discovering that."

def remind_me_with_goal (situation, number = 1, model_name = "gpt-3.5-turbo"):
    """
    """
    situation_parts = make_scene_parts_query(situation, model_name)
    goal = situation_parts['goal']  

    memory_pool = chroma_memory.query(query_texts=[goal], n_results=number)

    story_name = memory_pool['metadatas'][0][0]['name']

    if verbose:
        print("I am reminded of an event that happened in " + story_name)
        print("     The goal I used in the current situation is  " + goal)
    memory_distance = memory_pool['distances'][0]
    if verbose:
        print("     The memory has a distance of " + str(memory_distance))
        
    memory_id = memory_pool['ids'][0][0]
    memory_id_event_number = int(memory_id.split("_")[-1])

    memory_goal = memory_pool['documents'][0]
    
    if verbose:
        print("     The goal in the memory is "  + str(memory_goal))
   
        
    memory_scene = gpt_4o_memory[story_name]['extracted_output'][memory_id_event_number]
    memory_scene_parts = memory_scene['scene_parts']
    memory_event_text = memory_scene['event_text']

    if verbose:
        print("     " + memory_event_text)

    if verbose:
        print("     " + str(memory_scene_parts))
        
    if verbose:
        print("     The action in the story is "  + str(memory_scene_parts['action']))
   

    solution = adapt_with_llm(situation, memory_scene_parts, model_name)

    if verbose:
        print("\n\nAn adapted solution is to --> " + solution)
    
    return solution


def remind_me_with_troika (situation, number = 1, model_name = "gpt-3.5-turbo"):
    """
    """
    situation_parts = make_scene_parts_query(situation, model_name)
    situation_indexes = make_indexes_for_scene(situation_parts, model_name)
    query_indexes = ', '.join(situation_indexes['indexes'])

    memory_pool = chroma_memory.query(query_texts=[query_indexes], n_results=number)

    story_name = memory_pool['metadatas'][0][0]['name']

    if verbose:
        print("I am reminded of an event that happened in " + story_name)
        print("     The indexes I used in the current sitation were " + query_indexes)
    memory_distance = memory_pool['distances'][0]
    if verbose:
        print("     The memory has a distance of " + str(memory_distance))
        
    memory_id = memory_pool['ids'][0][0]
    memory_id_event_number = int(memory_id.split("_")[-1])

    memory_indexes = memory_pool['documents'][0]
    if verbose:
        print("     The indexes to the memory were " + str(memory_indexes))
   
        
    memory_scene = gpt_4o_memory[story_name]['extracted_output'][memory_id_event_number]
    memory_scene_parts = memory_scene['scene_parts']
    memory_event_text = memory_scene['event_text']

    if verbose:
        print("     " + memory_event_text)

    solution = adapt_with_llm(situation, memory_scene_parts, model_name)

    if verbose:
        print("\n\nAn adapted solution is to --> " + solution)
    
    return solution



def store_indexes_in_chromadb (story_name, extraction):
    """
    Stores the indexes for each scene into a chroma memory 

    Args:
        story_name (str):  The name of the story being put into memory
        extraction (dict):  The complete extraction for the story, including three part scenes and indexes
    """
    
    index = 0

    count = 0
    print("Storing indexes for " + story_name) 
    for event in extraction['extracted_output']:
        if 'indexes' in event:
            indexes_to_store = event['indexes']['indexes']
            indexes_string = ', '.join(indexes_to_store)

            print("Found indexes = " + indexes_string)
            chroma_memory.add(
                documents = [indexes_string],
                ids = [f'story_id_{snake_case(story_name)}_{count}'], 
                metadatas = [{'name':story_name}]
                )

        count = count + 1



def store_scene_goals_in_chromadb (story_name, extraction):
    """
    Stores the goal of each scene into a chroma memory 

    Args:
        story_name (str):  The name of the story being put into memory
        extraction (dict):  The complete extraction for the story, including three part scenes and indexes
    """
    
    index = 0
    count = 0
    print("Storing scenes for " + story_name) 
    for event in extraction['extracted_output']:
        if event['event_type'] == 'scene':
            goal_to_store = event['scene_parts']['goal']

            print("Found goal = " + goal_to_store)
            chroma_memory.add(
                documents = [goal_to_store],
                ids = [f'story_id_{snake_case(story_name)}_{count}'], 
                metadatas = [{'name':story_name}]
                )

        count = count + 1



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


    
def fetch_memory_extraction(
    story,
    model_name,
    output_dir,
    file_namer
    ):
    # Determine file path
    model_dir = os.path.join(output_dir, "extraction_extras", model_name)
    os.makedirs(model_dir, exist_ok=True)
    filename = file_namer(story.name) + "-extras.json"
    filepath = os.path.join(model_dir, filename)

    # If the file exists and we're not forcing recomputation, load and return
    print("Loading memory for " + story.name)
    
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return json.load(f)

    return None





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


def fetch_or_compute_story_extras(
    story,
    extraction,
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
    model_dir = os.path.join(output_dir, "extraction_extras", model_name)
    os.makedirs(model_dir, exist_ok=True)
    filename = file_namer(story.name) + "-extras.json"
    filepath = os.path.join(model_dir, filename)

    # If the file exists and we're not forcing recomputation, load and return
    if not force and os.path.exists(filepath):
        with open(filepath, "r") as f:
            return json.load(f)

    # Otherwise compute, serialize, save, and return
    result = calculate_extras(extraction, model_name=model_name)
    serializable_result = serializer(result)
    with open(filepath, "w") as f:
        json.dump(serializable_result, f, indent=2)
    return serializable_result



def calculate_extras(extraction, model_name="gpt-3.5-turbo"):
    # First, the goal/action/catatrophe
    # Second, the emotion/reason/anticipation/choice
    # Third, the indexes

    # SHALLOW COPY!!!!!!!!
    events = extraction['extracted_output']

    new_events = []
    for event in events:
        if event['event_type'] == 'scene':
            scene_parts = make_scene_parts({event['event_text'], event['reason']})
            indexes = make_indexes_for_scene(scene_parts, model_name)
            event['scene_parts'] = scene_parts
            event['indexes'] = indexes            
        if event['event_type'] == 'sequel':
            sequel_parts = make_sequel_parts({event['event_text'], event['reason']})
            event['sequel_parts'] = sequel_parts
        if event['event_type'] == 'none':
            continue

    return (events)

def make_scene_parts_query(situation: str, model_name="gpt-3.5-turbo") -> Dict:
    messages = "Take the following situation and determine the goal that the situation involves.  Use only the given situtation produce the goal.  Return the goal in a JSON structure."

    message_to_send = [{'role':'user', 'content': "'" + messages + ' ' + str(situation) + ' '}]   

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

    parsed_output['action'] = None
    parsed_output['catastrophe'] = None
    
    return parsed_output   


def make_scene_parts(extracted_scene: str, model_name="gpt-3.5-turbo") -> Dict:
    messages = "Take the following extracted scene which is made up of text and reason and produce a JSON structure consisting of 'goal', 'action', and 'catastrophe' which are from the scene.  Use only the story in the given scene to produce the goal, action, and catatrosphe.  If any one of the three parts is missing, simply indicate that with 'None'."

    message_to_send = [{'role':'user', 'content': "'" + messages + ' ' + str(extracted_scene) + ' '}]   #list(extracted_scene)[0] + ' ' + list(extracted_scene)[1] + "'"}]

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
        
    return parsed_output   



def make_sequel_parts(extracted_scene: str, model_name="gpt-3.5-turbo") -> Dict:
    messages = "Take the following extracted sequel which is made up of text and reason and produce a JSON structure consisting of 'emotional_response', 'logical_response', 'anticipation', and 'choice'.    If a particular element does not seem to exist, indicate this with 'None'."

    indexes = []

    message_to_send = [{'role':'user', 'content': "'" + messages + ' ' + list(extracted_scene)[0] + ' ' + list(extracted_scene)[1] + "'"}]

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
        
    return parsed_output   

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

def count_all_events(data, event_type='event'):
    count = 0
    for story in corpora.stories:
        extracted = data[story.name]
        if extracted is not None:
            events = []
            for event in extracted['extracted_output']:
                if event['event_type'] == event_type:
                    events.append(event)
                    
            count = count + len(events)
            
    return count

def get_scenes(events):
    scenes = []
    for event in events:
        if event['event_type'] == 'scene':
            scenes.append({event['event_text'], event['reason']})

    return scenes

def get_keywords(text):
    keywords = []
    words = nltk.word_tokenize(text)
    tagged = nltk.pos_tag(words)

    for word in tagged:
        if word[1].startswith("NN") or word[1].startswith("VB"):
            keywords.append(word[0])

    return keywords

# Function:   adapt_with_llm
# Input:      new situation, the old scene, and the model to use
# Output:     the adapted action with warnings for catastrophes
def adapt_with_llm(new_situation, old_scene, model_name="gpt-3.5-turbo"):
    message_to_send = [
        {
            "role": "system",
            "content": "You are a strict transformation assistant. Your task is to adapt to a new situation using only the information provided in a structured template. Do not add any information, advice, interpretation, reasoning, or suggestions that are not explicitly stated in the structure. Do not invent catastrophes, actions, or goals. Preserve the form and scope of the original structure, and transform the names and setting as appropriate to match the new situation.   Focus on adapting the action from the old structure to fit the new goal.  Do not use proper names from the old structure.  Your output must be a single paragraph not a JSON structure.   Explain your adaptations and why you made those."
        },
        {
            "role": "user",
            "content": "New situation: " + new_situation + ".\n\n Structure: " + str(old_scene) + ".\n\nAdapt the structure to the new situation using only the information in the structure.  Produce a new action that is based on the old action but changed to fit the new goal.   Present in the answer in paragraph form not as a JSON structure."
        }
    ]

    response = client.chat.completions.create(
        model=model_name,
        messages=message_to_send, 
        temperature=0.0,
    )

    raw_output = response.choices[0].message.content

    return raw_output




# Function:  runGPT
# Name    :  Kenny Moorman
# Input   :  string to give to ChatCompletion
# Output  :  the entire returned element in JSON
# Purpose :  Calls most recent way I am using to interface with OpenAI API
def runGPT(content):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": content} 
            ], 
        #        max_tokens=500,
        temperature=0.2
    )

    raw_output = response.choices[0].message.content

    return raw_output


def play_indexes (extracted_scene, model_name="gpt-3.5-turbo"):
    scene_parts = build_scenes(extracted_scene)

    message_to_send = [
        {
            "role": "system",
            "content": "You are an expert in memory and cognition. Your task is to help identify generalized memory indexes from scenes involving emotional or moral conflict. Generalized indexes are cues that can help someone recall a past event, especially emotionally or morally significant ones. These indexes should be abstract enough to apply across contexts but still relevant to the scene's underlying emotional or moral themes."
        },
        {
            "role": "user",
            "content": "You will be given a scene with three parts:\n- Goal: The purpose of the interaction.\n- Action: What happens in the moment.\n- Catastrophe: A key background event that explains the emotional stakes.\n\nYour task is to identify a set of generalized indexes — cues or concepts that could help someone remember the catastrophe. \n\nThese indexes should:\n- Be general enough to apply in other similar situations (avoid specific names or objects)\n- Reflect emotional, social, or moral themes\n- Refer to actions, feelings, relationships, or settings that can trigger reminding\n\nReturn a list of 5–8 short phrases or sentences, each representing a generalized index.\n\nExample Input:\nGoal: The doctor is trying to understand why the girl was upset.\nAction: The doctor seated her alongside his desk and asked, 'How do you feel now?'\nCatastrophe: The discovery that the girl used a friend's feelie permit.\n\nExample Output:\n- Why someone was upset\n- Someone using another person’s access or permission\n- Being questioned by an authority figure\n- Feeling guilty or ashamed\n- Doing something dishonest or against the rules\n- A conversation exploring emotional consequences\n- Being in a setting where one expects to be held accountable\nThe input is " + str(scene_parts)
        }
    ]

    response = client.chat.completions.create(
        model=model_name,
        messages=message_to_send, 
        temperature=0.2,
    )

    raw_output = response.choices[0].message.content
    
    return raw_output

def play_indexes(extracted_scene, model_name="gpt-3.5-turbo"):
    scene_parts = build_scenes(extracted_scene, model_name)
    message_to_send = [
        {
            "role": "system",
            "content": "You are an expert in memory and cognition. Your task is to identify generalized memory indexes from short scenes involving emotional or moral conflict. Generalized indexes are cues that can help someone recall a past event, especially emotionally or morally significant ones.\n\nThe indexes must:\n- Be general (not specific to people, objects, or places in the scene)\n- Be relevant to emotional, social, or moral aspects\n- Be expressed as short phrases (not full sentences)\n- Not begin with articles like 'a' or 'an'\n\nYou will receive a scene with three parts:\n- Goal: The purpose of the interaction.\n- Action: What happens in the moment.\n- Catastrophe: A key background event that explains the emotional stakes.\n\nReturn your answer in the following JSON format:\n{\n  \"indexes\": [\n    \"first index phrase\",\n    \"second index phrase\",\n    ...\n  ]\n}"
        },
        {
            "role": "user",
            "content": str(scene_parts)
        }
    ]

    response = client.chat.completions.create(
        model=model_name,
        messages=message_to_send, 
        temperature=0.2,
    )

    raw_output = response.choices[0].message.content

    return raw_output


def make_indexes_for_scene(extracted_three_part_scene, model_name="gpt-3.5-turbo"):
    message_to_send = [
        {
            "role": "system",
            "content": "You are an expert in memory and cognition. Your task is to identify generalized memory indexes from short scenes involving emotional or moral conflict. Generalized indexes are cues that can help someone recall a past event, especially emotionally or morally significant ones.\n\nThe indexes must:\n- Be general (not specific to people, objects, or places in the scene)\n- Be relevant to emotional, social, or moral aspects\n- Be expressed as short phrases (not full sentences)\n- Not begin with articles like 'a' or 'an'\n\nYou will receive a scene with three parts:\n- Goal: The purpose of the interaction.\n- Action: What happens in the moment.\n- Catastrophe: A key background event that explains the emotional stakes.\n\nReturn your answer in the following JSON format:\n{\n  \"indexes\": [\n    \"first index phrase\",\n    \"second index phrase\",\n    ...\n  ]\n}"
        },
        {
            "role": "user",
            "content": str(extracted_three_part_scene)
        }
    ]

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
        
    return parsed_output   




# Function:   best_match_cosine
# Name    :   Kenny Moorman
# Input   :   string of keywords, array of strings of keywords from all episodes, how many to return
# Output  :   array of top matches based on simple cosine similarity of counts
def best_match_cosine(keywordsTarget, memory, number):
    matches = []
    keywordsTargetString = " ".join(keywordsTarget)

    print(keywordsTargetString)
    
    keywordsArray = [submemory[0] for submemory in memory]
    for i, keywords in enumerate(keywordsArray):
        keywordsMatchString = " ".join(keywords)
        
        print("    " + keywordsMatchString)
        
        vectorizer = CountVectorizer().fit_transform([keywordsTargetString, keywordsMatchString])
        vectors = vectorizer.toarray()

        vec1 = vectors[0].reshape(1, -1)
        vec2 = vectors[1].reshape(1, -1)

        matches.append([i, cosine_similarity(vec1, vec2)[0][0]])

    return sorted(matches, key=lambda element: element[1], reverse=True)[0:(number)]

# Function:  build_memory
# Input:
# Output: 
def build_memory(names, stories, model_name="gpt-3.5-turbo"):
    print("Beginning memory build for " + str(len(stories)) + " stories.")

    memory = []
    
    for i, story in enumerate(stories):
        print("   " + names[i])
        indexes = build_all_scenes_indexes(story['extracted_output'], names[i])
        indexes_array = make_index_array(indexes)

        for index in indexes_array:
            memory.append(index)

    return memory
       


def make_index_array (indexes):
    name = indexes[0]
    scenes = indexes[1]
#
    index_array = []
#
    for scene in scenes:
        index_array.append([scene[1]['indexes'], scene[0], name])
#
    return index_array

def build_all_scenes_indexes (extracted_story: str, story_name, model_name="gpt-3.5-turbo") -> Dict:
    all_scenes = []

    for scene in get_scenes(extracted_story):
        all_scenes.append([scene, build_indexes(scene, model_name)])

    return [story_name, all_scenes]


    
def build_indexes(extracted_scene, model_name="gpt-3.5-turbo"):
    scene_parts = build_scenes(extracted_scene, model_name)
    message_to_send = [
        {
            "role": "system",
            "content": "You are an expert in memory and cognition. Your task is to identify generalized memory indexes from short scenes involving emotional or moral conflict. Generalized indexes are cues that can help someone recall a past event, especially emotionally or morally significant ones.\n\nThe indexes must:\n- Be general (not specific to people, objects, or places in the scene)\n- Be relevant to emotional, social, or moral aspects\n- Be expressed as short phrases (not full sentences)\n- Not begin with articles like 'a' or 'an'\n\nYou will receive a scene with three parts:\n- Goal: The purpose of the interaction.\n- Action: What happens in the moment.\n- Catastrophe: A key background event that explains the emotional stakes.\n\nReturn your answer in the following JSON format:\n{\n  \"indexes\": [\n    \"first index phrase\",\n    \"second index phrase\",\n    ...\n  ]\n}"
        },
        {
            "role": "user",
            "content": str(scene_parts)
        }
    ]

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
        
    #indexes.append(get_keywords(parsed_output['goal']))
        
    return parsed_output   



def KMMbuild_all_indexes(extracted_story_text: str, model_name="gpt-3.5-turbo", general=True) -> Dict:
    if general:
        messages = "Take the following extracted scene text and reason and produce a JSON structure consisting of 'goal', 'action', and 'catastrophe.   Make the elements of the JSON structure generic."
    else:
        messages = "Take the following extracted scene text and reason and produce a JSON structure consisting of 'goal', 'action', and 'catastrophe."

    indexes = []
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
        indexes.append(get_keywords(parsed_output['goal']))
        
    return indexes, scenes_parts

def build_test_set(number=10):
    stories = []
    names = []
    taken = []

    for i in range(0, number):
        index = random.randint(0, len(corpora.stories)-1)
        while index in taken:
            index = random.randint(0, len(corpora.stories)-1)

        stories.append(gpt_4o_memory[corpora.stories[index].name])
        names.append(corpora.stories[index].name)
        
    return names,stories


def index_all_and_write(
    corpora,
    extract_scenes_and_sequels,
    model_name="gpt-3.5-turbo",
    output_dir=DEV_OUTPUT,
    file_namer=extractors.title_to_filename,
    serializer=make_serializable):
    return


# Function:  index_one_and_write
# Input:
# Output:
def index_one_and_write(
        corpora, 
        extractions_data,
        number,
        calculate_extras, 
        model_name="gpt-3.5-turbo",
        output_dir=DEV_OUTPUT,
        file_namer=extractors.title_to_filename,
        serializer=make_serializable):

    result = None
    
    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Create a subdirectory for the model
    model_dir = os.path.join(output_dir, "extraction_extras", model_name)
    os.makedirs(model_dir, exist_ok=True)

    story_name = corpora.stories[number].name
    extraction = extractions_data[story_name]

    if extraction==None:
        return None
    
    filename = file_namer(story_name) + "-extras.json"
    filepath = os.path.join(model_dir, filename)

    # Skip already-processed files
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return json.load(f)

    try:
        print(f"Processing story: {story_name}")
 
        result = calculate_extras(extraction, model_name=model_name)

        serialized_result = serializer(extraction)   # due to the shallow copy
        with open(filepath, "w") as f:
            json.dump(serialized_result, f, indent=2)
    except Exception as e:
        print(f"Error processing {story.name}: {e}")
        print(result)
        return None

    print("Full scene/sequel/indexes extraction complete.")

    return extraction # which to return?

    
def collate_story_extractions(corpora, model_name, output_dir):
    """
    Collate the story extractions into a DataFrame.
    """
    extractions = {}
    statistics = []
    for story in corpora.stories:
        # Get metadata about the story
        story_text = story.body
        story_author = story.metadata['author']
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
                
        story_statistics = {
            "story_name": story.name,
            "story_author": "Other", 
            "characters": characters,
            "tokens": tokens,
            "parsed": int(parsed),
            "events": len(events),
            "scenes": len(scenes),
            "sequels": len(sequels),
            "nones": len(nones), 
            "paragraphs": number_paragraphs
        }

        if type(story_author)==list:
            story_statistics['story_author'] = "Other"
        else:
            story_statistics['story_author'] = story_author

        if story_statistics['story_author'] == "H. P. Lovecraft":
            story_statistics['story_author'] = "Lovecraft"

        if story_statistics['story_author'] == "Arthur Conan Doyle":
            story_statistics['story_author'] = "Doyle"

        statistics.append(story_statistics)
            
    return extractions, pd.DataFrame(statistics)


def collate_memory_extractions(corpora, model_name, output_dir):
    """
    Collate the memory extractions
    """
    extractions = {}

    for story in corpora.stories:
        # Get metadata about the story
        story_text = story.body
        story_author = story.metadata['author']
        characters = len(story_text)
        tokens = count_tokens(story_text, model_name)

        # Get the extraction for the story
        extraction = fetch_memory_extraction(
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
            
    return extractions

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
        "story_author": story.metadata['author'], 
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
        "story_author": story.metadata['author'], 
        "model": "gpt-4o",
        "tokens": gpt_4o_tokens,
        "events": len(gpt_4o_events),
        "scenes": len(gpt_4o_scenes),
        "sequels": len(gpt_4o_sequels),
        "nones": len(gpt_4o_nones), 
        "paragraphs": number_paragraphs
    })
    comparisons.append({
        "story_name": story.name,
        "story_author": story.metadata['author'], 
        "model": "gpt-3.5-turbo",
        "tokens": gpt_35_tokens,
        "events": len(gpt_35_events),
        "scenes": len(gpt_35_scenes),
        "sequels": len(gpt_35_sequels),
        "nones": len(gpt_35_nones),
        "paragraphs": number_paragraphs
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

gpt_4o_memory = collate_memory_extractions(
    corpora,
    model_name="gpt-3.5-turbo",   # need better way....
    output_dir=DEV_OUTPUT,
)

print("Loaded memory extractions:")
print(f" - memories : {len([m for m in gpt_4o_memory if gpt_4o_memory[m] is not None])}")

def compare_same_author(dataframe, author):
    author_df = dataframe[dataframe['story_author'] == author]

    print(f"  {len(author_df)} stories by {author}")

    print(author_df.describe())

    
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


def plot_box(df, x_col, y_col, hue_col=None):
    plt.figure(figsize=(10, 6))
    sns.boxplot(data=df, x=x_col, y=y_col)
    plt.xlabel(x_col)
    plt.ylabel(y_col)
#    plt.ylim(y_low, y_high)
#    if log:
#        plt.xscale('log')
    plt.title(f"{y_col} vs {x_col}")
    plt.legend(title=hue_col)
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



def testOne(number):
    return(index_one_and_write(
        corpora,
        gpt_4o_data, 
        number,
        calculate_extras,
        model_name="gpt-3.5-turbo",
        output_dir=DEV_OUTPUT,
        file_namer=extractors.title_to_filename,
        serializer=make_serializable))


def set_up_all_memory_indexes ():
    global gpt_4o_memory
    
    for index in range(0, len(corpora.stories)):
        # write to extras
        extraction = index_one_and_write(
            corpora,
            gpt_4o_data, 
            index,
            calculate_extras,
            model_name="gpt-3.5-turbo",
            output_dir=DEV_OUTPUT,
            file_namer=extractors.title_to_filename,
            serializer=make_serializable)

        if extraction == None:
            continue
        
        name = corpora.stories[index].name
        store_indexes_in_chromadb(name, extraction)

    gpt_4o_memory = collate_memory_extractions(
        corpora,
        model_name="gpt-3.5-turbo",   # need better way....
        output_dir=DEV_OUTPUT,
    )

    print("Reloaded memory extractions:")
    print(f" - memories : {len([m for m in gpt_4o_memory if gpt_4o_memory[m] is not None])}")


def set_up_all_memory_goals ():
    global gpt_4o_memory
    
    for index in range(0, len(corpora.stories)):
        extraction = index_one_and_write(
            corpora,
            gpt_4o_data, 
            index,
            calculate_extras,
            model_name="gpt-3.5-turbo",
            output_dir=DEV_OUTPUT,
            file_namer=extractors.title_to_filename,
            serializer=make_serializable)

        if extraction == None:
            continue
        
        name = corpora.stories[index].name
        store_scene_goals_in_chromadb(name, extraction)

    gpt_4o_memory = collate_memory_extractions(
        corpora,
        model_name="gpt-3.5-turbo",   # need better way....
        output_dir=DEV_OUTPUT,
    )

    print("Reloaded memory extractions:")
    print(f" - memories : {len([m for m in gpt_4o_memory if gpt_4o_memory[m] is not None])}")

    
def set_up_memory_indexes (number):
    global gpt_4o_memory
    
    taken = []
    for i in range(0, number):
        index = random.randint(0, len(corpora.stories)-1)
        while index in taken:
            index = random.randint(0, len(corpora.stories)-1)

        taken.append(index)

        # write to extras
        extraction = index_one_and_write(
            corpora,
            gpt_4o_data, 
            index,
            calculate_extras,
            model_name="gpt-3.5-turbo",
            output_dir=DEV_OUTPUT,
            file_namer=extractors.title_to_filename,
            serializer=make_serializable)

        if extraction == None:
            continue
        
        name = corpora.stories[index].name
        store_indexes_in_chromadb(name, extraction)

    gpt_4o_memory = collate_memory_extractions(
        corpora,
        model_name="gpt-3.5-turbo",   # need better way....
        output_dir=DEV_OUTPUT,
    )

    print("Reloaded memory extractions:")
    print(f" - memories : {len([m for m in gpt_4o_memory if gpt_4o_memory[m] is not None])}")

        
