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
import ast

# Third-party modules
import time

# Add imports from within the project

# Add the parent directory to the path so we can import modules from the parent directory.

module_path = os.path.abspath(os.path.join('..'))
if module_path not in sys.path:
    sys.path.append(module_path)

from lcats import stories
from lcats import utils
from lcats.utils import genre
from lcats.gettenberg import api



# ### Path Setup




# If the following code is run from lcats/notebooks in VSCode and the data is in lcats/data ...
CURRENT_PATH = os.path.abspath(os.curdir)  # This is where the notebook is executing.
PROJECT_ROOT = os.path.dirname("/home/kmoorman/LCATS-new/LCATS/lcats/")   # This should be the root of the project.
DEV_CORPUS = os.path.abspath(os.path.join(PROJECT_ROOT, 'data'))  # Local copy of the data.
GIT_CORPUS = os.path.abspath(os.path.join(PROJECT_ROOT, '../corpora'))  # Data in the git repo.

def check_path(path, description):
    if os.path.exists(path):
        print(f"Found {description} at: {path}")
    else:
        print(f"Missing {description} from: {path}")

check_path(DEV_CORPUS, "DEV_CORPUS")
check_path(GIT_CORPUS, "GIT_CORPUS")

# If run from within a notebook, the corpora root is two paths up from the notebook's location.
#CORPORA_ROOT = GIT_CORPUS  # Checked-in corpora
CORPORA_ROOT = DEV_CORPUS  # Command line working corpora

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








sfStories = find_all_stories_for_genre(corpora.stories, "SF")
horrorStories = find_all_stories_for_genre(corpora.stories, "Horror")
mysteryStories = find_all_stories_for_genre(corpora.stories, "Mystery")
romanceStories = find_all_stories_for_genre(corpora.stories, "Romance")
westernStories = find_all_stories_for_genre(corpora.stories, "Western")
