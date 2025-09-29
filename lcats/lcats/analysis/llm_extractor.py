"""Generic JSON-focused LLM extractor."""

import json
from typing import Any, Dict

from lcats import utils


class JSONPromptExtractor:
    """
    Generic JSON-focused LLM extractor.

    - Accepts arbitrary system/user prompt templates.
    - Forces JSON output (optionally) via OpenAI response_format when supported.
    - Returns a dict matching your downstream expectations.
    - Callable: __call__(story_text, model_name=...) -> result dict
    """

    def __init__(
        self,
        client,
        *,
        system_prompt: str,
        user_prompt_template: str,
        output_key: str = "events",
        default_model: str = "gpt-4o",
        temperature: float = 0.2,
        force_json: bool = True,
    ):
        self.client = client
        self.system_prompt = system_prompt
        self.user_prompt_template = user_prompt_template
        self.output_key = output_key
        self.default_model = default_model
        self.temperature = temperature
        self.force_json = force_json

        # Debug hooks (last call)
        self.last_messages = None
        self.last_response = None
        self.last_raw_output = None

    # ---------- public API ----------

    def build_messages(self, story_text: str) -> list[Dict[str, str]]:
        """Build the messages list for the chat completion.
        
        Args:
            story_text (str): The story text to include in the user prompt.
        Returns:
            list: The list of messages for the chat completion.
        """
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self.user_prompt_template.format(story_text=story_text)},
        ]

    def __call__(self, story_text: str, *, model_name: str | None = None) -> Dict[str, Any]:
        """Convenience method to call extract with optional model override."""
        return self.extract(story_text, model_name=model_name)

    def extract(self, story_text: str, *, model_name: str | None = None) -> Dict[str, Any]:
        """Run the LLM and parse the JSON into the expected structure.
        
        Args:
            story_text (str): The story text to analyze.
            model_name (str, optional): The model name to use. Defaults to None, which
                                        uses the default model.
        Returns:
            dict: A dictionary containing the extraction results and metadata.
        """
        model = model_name or self.default_model
        messages = self.build_messages(story_text)

        # Save for debugging/inspection
        self.last_messages = messages

        # Prepare kwargs; some OpenAI SDKs accept response_format for strict JSON.
        create_kwargs = dict(
            model=model,
            messages=messages,
            temperature=self.temperature,
        )
        if self.force_json:
            # If the SDK supports this, it will enforce JSON object responses.
            create_kwargs["response_format"] = {"type": "json_object"}

        response = self.client.chat.completions.create(**create_kwargs)

        # Extract content
        raw_output = response.choices[0].message.content if response.choices else ""
        self.last_response = response
        self.last_raw_output = raw_output

        # Parse JSON (tolerant extractor you already have)
        parsing_error = None
        try:
            parsed = utils.extract_json(raw_output)
        except json.JSONDecodeError as exc:
            parsed = None
            parsing_error = str(exc)

        if isinstance(parsed, dict) and self.output_key in parsed:
            extracted = parsed[self.output_key]
            extraction_error = None
        else:
            extracted = None
            extraction_error = f"Expected '{self.output_key}' key in JSON response."

        return {
            "story_text": story_text,
            "model_name": model,
            "messages": messages,
            "response": response,          # may be non-serializable
            "raw_output": raw_output,
            "parsed_output": parsed,
            "extracted_output": extracted,
            "parsing_error": parsing_error,
            "extraction_error": extraction_error,
        }
