"""Generic JSON-focused LLM extractor."""

import json
from typing import Any, Callable, Dict, Optional, Tuple

from lcats import utils


class JSONPromptExtractor:
    """
    Generic JSON-focused LLM extractor with optional text indexing, result alignment,
    and result validation/auditing.

    Parameters
    ----------
    client : OpenAI-like client
    system_prompt : str
    user_prompt_template : str
        May reference either `{indexed_story_text}` or `{story_text}`.
        This extractor will always provide BOTH keys; when indexing is enabled,
        both will point to the indexed text. When indexing is disabled, both
        will point to the raw story text.
    output_key : str
        Key in the returned JSON object to extract (e.g., "segments").
    default_model : str
    temperature : float
    force_json : bool
        If True, pass response_format={"type": "json_object"} when supported.
    text_indexer : Optional[Callable[[str], Tuple[str, Any]]]
        If provided, called as (indexed_text, index_meta) = text_indexer(story_text).
    result_aligner : Optional[Callable[[Dict[str, Any], str, Any], Dict[str, Any]]]
        If provided, called to post-process the parsed JSON and fill canonical offsets.
    result_validator : Optional[Callable[[Dict[str, Any], str, Any], Dict[str, Any]]]
        If provided, runs AFTER alignment and attaches a 'validation_report' to the result.
    """

    def __init__(
        self,
        client: Any,
        *,
        system_prompt: str,
        user_prompt_template: str,
        output_key: str = "segments",
        default_model: str = "gpt-4o",
        temperature: float = 0.2,
        force_json: bool = True,
        text_indexer: Optional[Callable[[str], Tuple[str, Any]]] = None,
        result_aligner: Optional[Callable[[
            Dict[str, Any], str, Any], Dict[str, Any]]] = None,
        result_validator: Optional[Callable[[
            Dict[str, Any], str, Any], Dict[str, Any]]] = None,  # << NEW
    ):
        self.client = client
        self.system_prompt = system_prompt
        self.user_prompt_template = user_prompt_template
        self.output_key = output_key
        self.default_model = default_model
        self.temperature = temperature
        self.force_json = force_json
        self.text_indexer = text_indexer
        self.result_aligner = result_aligner
        self.result_validator = result_validator  # << NEW

        # Debug/inspection hooks
        self.last_messages: Optional[list] = None
        self.last_response: Any = None
        self.last_raw_output: Optional[str] = None
        self.last_index_meta: Any = None
        self.last_validation_report: Optional[Dict[str, Any]] = None  # << NEW

    # ---------- helpers ----------

    def _prepare_user_content(self, story_text: str) -> Tuple[str, Any]:
        """
        Returns (content_text, index_meta):
          - content_text is what we place into the user prompt.
          - index_meta is indexing metadata (or None) for possible alignment.
        """
        if self.text_indexer:
            indexed_text, index_meta = self.text_indexer(story_text)
            self.last_index_meta = index_meta
            content = self.user_prompt_template.format(
                indexed_story_text=indexed_text,
                story_text=indexed_text,
            )
            return content, index_meta
        else:
            self.last_index_meta = None
            content = self.user_prompt_template.format(
                indexed_story_text=story_text,
                story_text=story_text,
            )
            return content, None

    def build_messages(self, story_text: str) -> list[Dict[str, str]]:
        content, _ = self._prepare_user_content(story_text)
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": content},
        ]

    # ---------- API ----------

    def __call__(self, story_text: str, *, model_name: Optional[str] = None) -> Dict[str, Any]:
        return self.extract(story_text, model_name=model_name)

    def extract(self, story_text: str, *, model_name: Optional[str] = None) -> Dict[str, Any]:
        model = model_name or self.default_model

        # Build messages (with optional indexing)
        user_content, index_meta = self._prepare_user_content(story_text)
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_content},
        ]
        self.last_messages = messages

        # Call model
        kwargs = dict(model=model, messages=messages,
                      temperature=self.temperature)
        if self.force_json:
            kwargs["response_format"] = {"type": "json_object"}
        response = self.client.chat.completions.create(**kwargs)

        raw_output = response.choices[0].message.content if response.choices else ""
        self.last_response = response
        self.last_raw_output = raw_output

        # Parse
        parsing_error = None
        try:
            parsed = utils.extract_json(raw_output)
        except json.JSONDecodeError as exc:
            parsed = None
            parsing_error = str(exc)

        extraction_error = None
        alignment_error = None
        validation_error = None
        validation_report = None
        extracted = None

        if isinstance(parsed, dict) and self.output_key in parsed:
            # Optional alignment
            if self.result_aligner and index_meta is not None:
                try:
                    parsed = self.result_aligner(
                        parsed, story_text, index_meta)
                except Exception as exc:
                    alignment_error = f"alignment failed: {exc!r}"

            # Optional validation/auditing  << NEW
            if self.result_validator and index_meta is not None:
                try:
                    validation_report = self.result_validator(
                        parsed, story_text, index_meta)
                except Exception as exc:
                    validation_error = f"validation failed: {exc!r}"
            self.last_validation_report = validation_report

            extracted = parsed.get(self.output_key) if isinstance(
                parsed, dict) else None
            if extracted is None:
                extraction_error = f"Expected '{self.output_key}' key in JSON response."
        else:
            extraction_error = f"Expected '{self.output_key}' key in JSON response."

        return {
            "story_text": story_text,
            "model_name": model,
            "messages": messages,
            "response": response,  # non-serializable; strip with make_serializable()
            "raw_output": raw_output,
            "parsed_output": parsed,
            "extracted_output": extracted,
            "parsing_error": parsing_error,
            "extraction_error": extraction_error,
            "alignment_error": alignment_error,
            "index_meta": index_meta,
            "validation_report": validation_report,     # << NEW
            "validation_error": validation_error,       # << NEW
        }
