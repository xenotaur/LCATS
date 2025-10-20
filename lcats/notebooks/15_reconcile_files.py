#!/usr/bin/env python
# coding: utf-8

# # Reconcile Extractions
# 
# Compare two versions of the extracted mass_quantities directory.

# ## Imports

# In[ ]:


from __future__ import annotations

from dataclasses import dataclass, asdict
import datetime
import fnmatch
import json
import os
import pathlib
import random
import re
import sys

from pathlib import Path

from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from tqdm import tqdm


# Third-party modules

# In[ ]:


import dotenv
from openai import OpenAI
import tiktoken


# Switch to the parent directory so paths can resolve and we write to the right directories.

# In[ ]:


cwd = pathlib.Path.cwd().resolve()
project_root = cwd.parent if cwd.name == "notebooks" else cwd
scripts_dir = project_root / "scripts"
if scripts_dir.is_dir():
    if cwd != project_root:
        print(f"Changing working directory from {cwd} to {project_root}")
        os.chdir(project_root)  # Change to the project root directory.
print("Working directory:", pathlib.Path.cwd())


# Add imports from within the project (depends on prior cell)

# In[ ]:


from lcats import constants
from lcats import stories

from lcats import utils
from lcats.utils import names
from lcats.utils import values

from lcats.gettenberg import api
from lcats.gettenberg import cache
from lcats.gettenberg import metadata
from lcats.gettenberg import headers

from lcats.gatherers import downloaders
from lcats.gatherers.mass_quantities import storymap
from lcats.gatherers.mass_quantities import parser

from lcats.analysis import corpus_surveyor


# In[ ]:





# In[ ]:


from importlib import reload

RELOAD_MODULES = [
    api,
    cache,
    constants,
    corpus_surveyor,
    downloaders,
    headers,
    metadata,
    names,
    parser,
    stories,
    storymap,
    utils,
]
def reloader():
    for module in RELOAD_MODULES:
        print("Reloading", module)
        reload(module)
    print("Reloading complete.")


# ## Project Setup

# ### Path Setup

# In[ ]:


# Where the notebook is executing (absolute, resolved)
CURRENT_PATH = pathlib.Path.cwd().resolve()

# Project root = formerly parent of notebooks/, now just current dir
# PROJECT_ROOT = CURRENT_PATH.parent 
PROJECT_ROOT = CURRENT_PATH

# Local data/output inside the project
DEV_CORPUS = (PROJECT_ROOT / "data")
DEV_OUTPUT = (PROJECT_ROOT / "output")

# Sibling-level resources (one level up from project root)
GIT_CORPUS = (PROJECT_ROOT.parent / "corpora")
OPENIA_API_KEYS_ENV = (PROJECT_ROOT.parent / ".secrets" / "openai_api_keys.env")

def check_path(path: pathlib.Path, description: str) -> None:
    if path.exists():
        print(f"Found {description} at: {path}")
    else:
        print(f"Missing {description} from: {path}")

check_path(DEV_CORPUS, "DEV_CORPUS")
check_path(DEV_OUTPUT, "DEV_OUTPUT")
check_path(GIT_CORPUS, "GIT_CORPUS")
check_path(OPENIA_API_KEYS_ENV, "OPENIA_API_KEYS_ENV")


# In[ ]:


# Working corpora
# CORPORA_ROOT = project_root / "data"
# Checked-in corpora
CORPORA_ROOT = project_root / ".." / "corpora"
CORPORA_ROOT = CORPORA_ROOT.resolve()  # Resolve to absolute path.

print("Corpora root:", CORPORA_ROOT)
print("Corpora top-level directories:", end=" ")
os.listdir(CORPORA_ROOT)


# In[ ]:


json_stories = corpus_surveyor.find_corpus_stories(CORPORA_ROOT)
len(json_stories)
print(utils.sml(json_stories))
print("Type of path element:", type(json_stories[0]))


# ## Comparing Mass Quantities

# In[ ]:


CORPORA_MASS = CORPORA_ROOT / "mass_quantities"
corpora_mass_stories = corpus_surveyor.find_corpus_stories(CORPORA_MASS)

DATA_MASS = PROJECT_ROOT / "data" / "mass_quantities"
data_mass_stories = corpus_surveyor.find_corpus_stories(DATA_MASS)

len(corpora_mass_stories), len(data_mass_stories)


# In[ ]:


corpora_mass_stems = set([story.stem for story in corpora_mass_stories])
data_mass_stems = set([story.stem for story in data_mass_stories])
missing_in_data = corpora_mass_stems - data_mass_stems
missing_in_corpora = data_mass_stems - corpora_mass_stems

print("Missing in data:", len(missing_in_data))
print(" - ", sorted(missing_in_data)[:20])
print("Missing in corpora:", len(missing_in_corpora))
print(" - ", sorted(missing_in_corpora)[:20])


# In[ ]:


def load_story_json(path: pathlib.Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data

sample_story = corpora_mass_stories[0]
sample_json = load_story_json(sample_story)
sample_json


# In[ ]:


sample_json["metadata"]["url"]


# In[ ]:


def collate_story_data(collection: str, paths: List[pathlib.Path]) -> pd.DataFrame:
    records = []
    for path in tqdm(paths):
        data = load_story_json(path)
        url = data["metadata"]["url"]
        title = data["name"]
        author = data["author"]
        
        appears_in_key = f"appears_in_{collection}"
        collection_name_key = f"name_in_{collection}"
        collection_name = path.stem
        
        records.append({
            "url": url,
            "title": title,
            "author": author,
            appears_in_key: True,
            collection_name_key: collection_name,
        })
    df = pd.DataFrame.from_records(records)
    return df


# In[ ]:


corpora_df = collate_story_data("corpora", corpora_mass_stories)
corpora_df.head()


# In[ ]:


data_df = collate_story_data("data", data_mass_stories)
data_df.head()


# In[ ]:


print(corpora_df.columns)
print(data_df.columns)


# In[ ]:


def join_dataframes(
    corpora_df: pd.DataFrame,
    data_df: pd.DataFrame,
) -> pd.DataFrame:
    # Outer join on url; give shared columns (title/author) explicit suffixes
    joint_df = pd.merge(
        corpora_df,
        data_df,
        on="url",
        how="outer",
        suffixes=("_corpora", "_data"),
    )

    # Fill the presence flags; NaN -> False
    for col in ("appears_in_corpora", "appears_in_data"):
        if col not in joint_df.columns:
            # If one side didn’t exist, add it so downstream code is uniform
            joint_df[col] = False
        joint_df[col] = joint_df[col].fillna(False).astype(bool)

    # Fill the names; NaN -> None (pd.NA also fine if you prefer)
    for col in ("name_in_corpora", "name_in_data"):
        if col not in joint_df.columns:
            joint_df[col] = None
        joint_df[col] = joint_df[col].where(joint_df[col].notna(), None)

    # Derived flags
    joint_df["title"] = joint_df["title_data"].combine_first(joint_df["title_corpora"])
    joint_df["filename"] = joint_df["name_in_data"].combine_first(joint_df["name_in_corpora"])
    joint_df["appears_in_both"] = joint_df["appears_in_corpora"] & joint_df["appears_in_data"]

    # Simple exact matches (robust to NaNs by filling with sentinel)
    joint_df["names_match"]  = joint_df["name_in_corpora"].fillna("")  == joint_df["name_in_data"].fillna("")
    joint_df["titles_match"] = joint_df["title_corpora"].fillna("")    == joint_df["title_data"].fillna("")

    # Authors: exact list equality (keeps it strict)
    joint_df["author_match_strict"] = joint_df["author_corpora"].fillna(object()) == joint_df["author_data"].fillna(object())

    # (Optional) reorder columns for readability
    cols_order = [
        "url", "title", "filename",
        "appears_in_both", "names_match", "titles_match", "author_match_strict",
        "appears_in_corpora", "name_in_corpora", "title_corpora", "author_corpora",
        "appears_in_data",    "name_in_data",    "title_data",    "author_data",
    ]
    joint_df = joint_df[[c for c in cols_order if c in joint_df.columns]]
    joint_df.sort_values(by="title", ascending=True, inplace=True)

    return joint_df


# In[ ]:


joint_df = join_dataframes(corpora_df, data_df)
joint_df.head()


# In[ ]:


joint_df.to_csv("notebooks/output/stories_comparison.csv", index=False, encoding="utf-8")


# In[ ]:


joint_df.appears_in_both.value_counts()


# In[ ]:




