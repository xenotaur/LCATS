#!/usr/bin/env python
from openai import OpenAI
import os
import dotenv

# If the following code is run from lcats/notebooks in VSCode and the data is in lcats/data ...
CURRENT_PATH = os.path.abspath(os.curdir)  # This is where the notebook is executing.
PROJECT_ROOT = os.path.dirname(CURRENT_PATH)   # This should be the root of the project.
DEV_CORPUS = os.path.abspath(os.path.join(PROJECT_ROOT, 'data'))  # Local copy of the data.
DEV_OUTPUT = os.path.abspath(os.path.join(PROJECT_ROOT, 'output'))  # Local copy of the data.
GIT_CORPUS = os.path.abspath(os.path.join(PROJECT_ROOT, '../corpora'))  # Data in the git repo.
OPENIA_API_KEYS_ENV = os.path.abspath(os.path.join(PROJECT_ROOT, '../.secrets/openai_api_keys.env'))  # Local OpenAI API key.


dotenv.load_dotenv(OPENIA_API_KEYS_ENV)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
print(OPENAI_API_KEY)


client = OpenAI()
print(f"Loaded OpenAI client: {client} with version: {client._version}")

# If run from within a notebook, the corpora root is two paths up from the notebook's location.

def test_open_ai(title: str, author: str, model_name="gpt-4o") -> dict:
    messages = "Give me just the year (nothing else) that " + title + " by " + author + " was first published."

    message_to_send = [{'role':'user', 'content': "'" + messages + "'"}]

    response = client.chat.completions.create(
        model=model_name,
        messages=message_to_send, 
        temperature=0.2,
    )

    raw_output = response.choices[0].message.content

    return raw_output
    

    

