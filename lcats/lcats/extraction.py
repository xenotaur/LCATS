"""Extract structured data from stories using LLMs and prompt templates."""

from dataclasses import dataclass
from typing import Dict, List, Optional

import json

from lcats import utils


@dataclass
class ExtractionTemplate:
    """A pair of prompt templates for system and user roles that interpolates the story text."""

    name: str
    system_template: str
    user_template: str

    def build_prompt(self, story_text: str) -> List[Dict[str, str]]:
        """Create the prompt messages for the LLM with the given story text."""
        return [
            {"role": "system", "content": self.system_template},
            {
                "role": "user",
                "content": self.user_template.format(story_text=story_text),
            },
        ]


@dataclass
class ExtractionResult:  # pylint: disable=too-many-instance-attributes
    """Result of structured extraction from a story using an LLM and a prompt template."""

    story_text: str
    model_name: str
    template: ExtractionTemplate
    messages: List[Dict[str, str]]
    response: Optional[object]  # raw OpenAI response object
    raw_output: Optional[str]  # raw text output from the LLM
    parsed_output: Optional[Dict]
    parsing_error: Optional[str]
    extraction_error: Optional[str]
    extracted_output: Optional[List[Dict]]  # structured output from the LLM

    def summary(self) -> str:
        """Return a summary of the extraction result."""
        output = []
        output.append(f"Model: {self.model_name}")
        output.append(f"Template: {self.template.name}")
        output.append(
            f"Events extracted: {len(self.extracted_output) if self.extracted_output else 0}"
        )
        if self.parsing_error:
            output.append(f"Parsing error: {self.parsing_error}")
        if self.extraction_error:
            output.append(f"Extraction error: {self.extraction_error}")
        return "\n".join(output)


def extract_from_story(
    story_text: str,
    template: ExtractionTemplate,
    client,
    model_name: str = "gpt-3.5-turbo",
    temperature: float = 0.2,
) -> ExtractionResult:
    """Perform structured extraction from a story using an LLM and a prompt template."""
    messages = template.build_prompt(story_text)
    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=temperature,
    )
    raw_output = response.choices[0].message.content

    try:
        parsed_output = utils.extract_json(raw_output)
        parsing_error = None
    except (json.JSONDecodeError, ValueError) as exc:
        parsed_output = None
        parsing_error = str(exc)

    if not parsed_output:
        extracted_output = None
        extraction_error = (
            f"No parsed JSON found in raw output (length: {len(raw_output)} chars)"
        )
    elif isinstance(parsed_output, dict) and "events" in parsed_output:
        extracted_output = parsed_output["events"]
        extraction_error = None
    else:
        extracted_output = None
        extraction_error = f"Parsed output missing 'events' key. Found keys: {list(parsed_output.keys())}"

    return ExtractionResult(
        story_text=story_text,
        model_name=model_name,
        template=template,
        messages=messages,
        response=response,
        raw_output=raw_output,
        parsed_output=parsed_output,
        parsing_error=parsing_error,
        extraction_error=extraction_error,
        extracted_output=extracted_output,
    )
