#!/usr/bin/env python
# coding: utf-8

# # Reboot of LCATS RAG Baseline Prototype
# The scope of this prototype is not to build our full system, but to use our corpora as the document database for a classical RAG system.
# 
# TODOs:
# 
# * Get the corpora pulled over from 07_project_reboot.ipynb - DONE
# * Feed it into a vector database - IN PROCESS
# * Do a basic vector database pull - TODO
# * Test it out! - TODO
# 
# THOUGHTS:
# 
# * Can we create a corpora of stories which have the names changed as a way of avoiding the LLM memorization problem?

# ## Imports

# In[ ]:


from datetime import date
import json
import os
import sys
import pandas as pd


# Third-party modules

# In[ ]:


import dotenv
from openai import OpenAI


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


# ## RAG Baseline Prototype
# TODOs:
# 
# * Feed it into a vector database - IN PROCESS
# 

# 

# In[ ]:




