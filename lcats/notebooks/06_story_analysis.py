#!/usr/bin/env python
# coding: utf-8

# # Story Analysis Notebook

# ## Inports

# In[1]:


import os
import re


# ## Story Access API

# In[ ]:


import os
import json

class StoryCorpora:
    def __init__(self, corpora_root):
        self._corpora_root = corpora_root
        self._corpora = None
        self._stories = None

    @property
    def corpora_root(self):
        return self._corpora_root
    
    @property
    def corpora(self):
        if self._corpora is None:
            self._corpora = self.get_corpora()
        return self._corpora
    
    @property
    def stories(self):
        if self._stories is None:
            self._stories = self.get_stories()
        return self._stories

    def get_stories(self):
        stories = []
        for corpus in self.corpora.values():
            for story in corpus:
                stories.append(story)
        return stories

    def get_corpora(self):
        corpora = {}
        for root, dirs, files in os.walk(self.corpora_root):
            for dir_name in dirs:
                corpora[dir_name] = []
                dir_path = os.path.join(root, dir_name)
                for file_name in os.listdir(dir_path):
                    if file_name.endswith('.json'):
                        file_path = os.path.join(dir_path, file_name)
                        with open(file_path, 'r') as file:
                            story = json.load(file)
                            corpora[dir_name].append(story)
        return corpora

# Example usage:
# corpora = StoryCorpora("../corpora")
# stories = corpora.get_stories()
# print(stories)


# In[22]:


# If run from within a notebook, the corpora root is two paths up from the notebook's location.
CORPORA_ROOT = os.path.abspath("../../corpora")  # Checked-in corpora
# CORPORA_ROOT = os.path.abspath("../data")  # Command line working corpora
corpora = StoryCorpora(CORPORA_ROOT)
corpora.corpora.keys()


# In[23]:


corpora.stories


# In[6]:


os.getcwd()


# ## LASTCODE

# In[ ]:





# In[ ]:


import os
import re

def find_matching_files(path, matcher):
    """
    Recursively finds all files in the given directory that match the provided regex or tag.

    Parameters:
        path (str): Path to the root directory.
        matcher (str or re.Pattern): A string or compiled regular expression to match filenames.

    Returns:
        list: A list of file paths that match the given matcher.
    """
    matching_files = []
    
    # If matcher is a string, compile it into a regex pattern
    if isinstance(matcher, str):
        matcher = re.compile(matcher)

    for root, _, files in os.walk(path):
        for file in files:
            if matcher.search(file):
                matching_files.append(os.path.join(root, file))
    
    return matching_files


# In[ ]:




