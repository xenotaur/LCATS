#!/usr/bin/env python
# coding: utf-8

# # Scene Extraction from Long Narratives with LLMs
# 
# Originally from ChatGPT, this notebook explores how to extract narrative scenes from
# long stories using chunked input and OpenAI's GPT models.

# ## Imports

# In[ ]:


from datetime import date
import hashlib
import json
import os
import sys

from typing import List, Dict

import numpy as np
import pandas as pd


# Third-party modules

# In[ ]:


import dotenv
from openai import OpenAI
import tiktoken


# Add imports from within the project

# In[ ]:


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

# In[ ]:


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


# ## OpenAI Client

# Get the OpenAI API key.

# In[ ]:


dotenv.load_dotenv(OPENIA_API_KEYS_ENV)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
print(OPENAI_API_KEY)


# Verify that we can get a client.

# In[ ]:


client = OpenAI()
print(f"Loaded OpenAI client: {client} with version: {client._version}")


# Verify the API is working. This week. And that you have credits.

# In[ ]:


response = client.responses.create(
    model="gpt-4o",
    input="Write a one-sentence bedtime story about a starship captain visiting a planet."
)

print(f"Story generated on: {date.today()}:")
utils.pprint(response.output_text)


# ## Story Corpora

# In[ ]:


# Reload the modules to ensure we have the latest code, if doing active development.
if False: 
    from importlib import reload
    reload(stories)
    reload(utils)


# In[ ]:


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


# ## Text Chunking Utilities

# In[ ]:


def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))


# In[ ]:


token_counts = []
for story in corpora.stories:
    token_count = count_tokens(story.body)
    token_counts.append({
        'name': story.name,
        'body_length': len(story.body),
        'token_count': token_count
    })
sorted_token_counts = sorted(token_counts, key=lambda x: x['token_count'], reverse=True)
token_counts_df = pd.DataFrame(sorted_token_counts)
print("Token counts for all stories:")
print("tokens\tlength\tname")
print("------\t------\t----")
for index, row in token_counts_df.iterrows():
    print(f"{row['token_count']}\t{row['body_length']}\t{row['name']}")

token_counts_df.describe()


# In[ ]:


def chunk_text(text: str, max_tokens: int = 800, overlap: int = 100) -> List[Dict]:
    import tiktoken
    enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        chunk = words[start:start+max_tokens]
        chunk_text = " ".join(chunk)
        chunks.append({
            "chunk_index": len(chunks),
            "start_word": start,
            "end_word": start+len(chunk),
            "text": chunk_text
        })
        start += max_tokens - overlap
    return chunks


# ## 3. Prompt Builder and LLM Call

# In[ ]:


def build_prompt(chunk: str) -> List[Dict]:
    return [{
        "role": "system", 
        "content": "You are a literary analyst trained to identify narrative scenes."
    }, {
        "role": "user", 
        "content": f"Analyze the following text and identify narrative scenes or interstitial elements. For each scene, describe the time, place, characters, and type (dramatic, sequel, interstitial). Return output in JSON with a top-level key 'events':\n\n{chunk}"
    }]

def call_openai_api(messages: List[Dict], model="gpt-3.5-turbo") -> str:
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=0.2
    )
    return response.choices[0].message["content"]


# ## 4. Parse LLM Output

# In[ ]:


def try_parse_json(output: str):
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        start = output.find("{")
        end = output.rfind("}") + 1
        try:
            return json.loads(output[start:end])
        except:
            return None


# ## 5. Full Scene Extraction Pipeline

# In[ ]:


def extract_scenes_from_text(text: str) -> List[Dict]:
    chunks = chunk_text(text)
    all_scenes = []
    for chunk in chunks:
        messages = build_prompt(chunk["text"])
        response = call_openai_api(messages)
        parsed = try_parse_json(response)
        if parsed and "events" in parsed:
            for event in parsed["events"]:
                event["chunk_index"] = chunk["chunk_index"]
                all_scenes.append(event)
    return all_scenes


# ## 6. Run Extraction on a Sample Story

# In[ ]:


sample_text = """
Once upon a time in a village nestled in the mountains, a girl named Lila dreamed of touching the stars...
"""

scenes = extract_scenes_from_text(sample_text)

import pandas as pd
pd.DataFrame(scenes)

