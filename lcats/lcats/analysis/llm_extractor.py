"""Generic JSON-focused LLM extractor."""

import json

from typing import Any, Callable, Dict, List, Optional, Tuple

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
        result_aligner: Optional[
            Callable[[Dict[str, Any], str, Any], Dict[str, Any]]
        ] = None,
        result_validator: Optional[
            Callable[[Dict[str, Any], str, Any], Dict[str, Any]]
        ] = None,  # << NEW
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
        self.last_messages: Optional[List[Dict[str, str]]] = None
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
        self.last_index_meta = None
        content = self.user_prompt_template.format(
            indexed_story_text=story_text,
            story_text=story_text,
        )
        return content, None

    def build_messages(self, story_text: str) -> List[Dict[str, str]]:
        """Public: build messages without invoking the client."""
        content, _ = self._prepare_user_content(story_text)
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": content},
        ]

    # ---------- error normalization ----------

    def _extract_error_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Try to parse a JSON object embedded in an exception string."""
        try:
            # Heuristic: find the first '{' and parse from there.
            start = text.find("{")
            if start >= 0:
                return json.loads(text[start:])
        except Exception:
            return None
        return None

    def _classify_api_error(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Classify OpenAI-like errors into actionable categories.

        Args:
            payload: Dict with best-effort fields (status, code, type, message, raw).

        Returns:
            Dict with normalized fields including flags for job control.
        """
        status = payload.get("status")
        code = (payload.get("code") or "").lower()
        # etype = (payload.get("type") or "").lower()  # not used in this function.
        message = (payload.get("message") or "").lower()

        category = "unknown"
        can_retry = False
        needs_smaller_request = False
        should_abort_batch = False
        suggested_action = "inspect_and_decide"

        # Quota/billing — abort batch
        if "insufficient_quota" in code or "quota" in message or status == 402:
            category = "quota_exceeded"
            should_abort_batch = True
            suggested_action = "stop_job_fix_billing"

        # Rate limit — retryable
        elif "rate_limit_exceeded" in code or "rate limit" in message or status == 429:
            category = "rate_limit"
            can_retry = True
            suggested_action = "retry_with_backoff"

            # Tokens-per-minute variant — often requires chunking OR pacing
            if "tokens per min" in message or "tpm" in message:
                category = "tpm_limit"
                needs_smaller_request = True
                suggested_action = "chunk_or_queue"

        # Context length — input too large for model window
        elif "context_length_exceeded" in code or "maximum context length" in message:
            category = "context_length"
            needs_smaller_request = True
            suggested_action = "shorten_input"

        # Auth/credentials — abort batch
        elif status == 401 or "api key" in message or "authentication" in message:
            category = "auth"
            should_abort_batch = True
            suggested_action = "fix_credentials"

        # Server/overload — retryable
        elif status in (500, 502, 503, 504) or "overloaded" in message:
            category = "server"
            can_retry = True
            suggested_action = "retry_with_backoff"

        return {
            **payload,
            "category": category,
            "can_retry": can_retry,
            "needs_smaller_request": needs_smaller_request,
            "should_abort_batch": should_abort_batch,
            "suggested_action": suggested_action,
        }

    def _normalize_api_error(self, exc: Exception) -> Dict[str, Any]:
        """Turn an arbitrary client exception into a normalized api_error dict.

        Args:
            exc: Exception from the client.

        Returns:
            A normalized error dict.
        """
        # Best-effort defaults
        status = getattr(exc, "status_code", None) or getattr(exc, "http_status", None)
        code = getattr(exc, "code", None)
        etype = getattr(exc, "type", None)
        message = getattr(exc, "message", None) or str(exc)

        raw = getattr(exc, "response", None)
        if raw and hasattr(raw, "json"):
            try:
                raw = raw.json()
            except Exception:
                raw = str(raw)

        # Try to extract {"error": {...}} block from message if present.
        embedded = self._extract_error_json(str(exc))
        if isinstance(embedded, dict):
            err = embedded.get("error") or embedded
            code = err.get("code") or code
            etype = err.get("type") or etype
            message = err.get("message") or message

        payload = {
            "status": status,
            "code": code,
            "type": etype,
            "message": message,
            "raw": embedded or raw or str(exc),
        }
        return self._classify_api_error(payload)

    # ---------- API ----------

    def __call__(
        self, story_text: str, *, model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        return self.extract(story_text, model_name=model_name)

    def extract(
        self, story_text: str, *, model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Run the prompt, parse JSON, optionally align and validate.

        Args:
            story_text: Full input text.
            model_name: Optional override for model.

        Returns:
            A result dict including `api_error` on failure. On success, fields like
            `raw_output`, `parsed_output`, and `extracted_output` are populated.
        """
        model = model_name or self.default_model

        # Build messages (with optional indexing)
        user_content, index_meta = self._prepare_user_content(story_text)
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_content},
        ]
        self.last_messages = messages

        # Call model (now guarded)
        api_error: Optional[Dict[str, Any]] = None
        response = None
        raw_output = ""

        try:
            kwargs = dict(model=model, messages=messages, temperature=self.temperature)
            if self.force_json:
                kwargs["response_format"] = {"type": "json_object"}
            response = self.client.chat.completions.create(**kwargs)
            self.last_response = response

            # Defensive read of response
            choices = getattr(response, "choices", None) or []
            if choices and getattr(choices[0], "message", None):
                raw_output = choices[0].message.content or ""
            else:
                # Treat as an API error-like condition
                api_error = {
                    "status": getattr(response, "status_code", None),
                    "code": "empty_response",
                    "type": "client_or_server",
                    "message": "No choices/content returned by API.",
                    "raw": str(getattr(response, "__dict__", response)),
                    "category": "unknown",
                    "can_retry": True,
                    "needs_smaller_request": False,
                    "should_abort_batch": False,
                    "suggested_action": "retry_with_backoff",
                }

        except Exception as exc:
            api_error = self._normalize_api_error(exc)
            # Early return with surfaced error; keep structure consistent.
            return {
                "story_text": story_text,
                "model_name": model,
                "messages": messages,
                "response": response,
                "response_id": getattr(response, "id", None) if response else None,
                "usage": getattr(response, "usage", None) if response else None,
                "raw_output": "",
                "parsed_output": None,
                "extracted_output": None,
                "parsing_error": None,
                "extraction_error": "api_error",
                "alignment_error": None,
                "index_meta": index_meta,
                "validation_report": None,
                "validation_error": None,
                "api_error": api_error,  # << surfaced, actionable
            }

        self.last_raw_output = raw_output

        # Parse (only if we got raw_output and no api_error)
        parsing_error = None
        try:
            parsed = utils.extract_json(raw_output) if raw_output else None
        except json.JSONDecodeError as exc:
            parsed = None
            parsing_error = str(exc)

        extraction_error = None
        alignment_error = None
        validation_error = None
        validation_report = None
        extracted = None

        if api_error:
            extraction_error = "api_error"
        elif isinstance(parsed, dict) and self.output_key in parsed:
            # Optional alignment
            if self.result_aligner and index_meta is not None:
                try:
                    parsed = self.result_aligner(parsed, story_text, index_meta)
                except Exception as exc:
                    alignment_error = f"alignment failed: {exc!r}"

            # Optional validation/auditing
            if self.result_validator and index_meta is not None:
                try:
                    validation_report = self.result_validator(
                        parsed, story_text, index_meta
                    )
                except Exception as exc:
                    validation_error = f"validation failed: {exc!r}"
            self.last_validation_report = validation_report

            extracted = (
                parsed.get(self.output_key) if isinstance(parsed, dict) else None
            )
            if extracted is None:
                extraction_error = f"Expected '{self.output_key}' key in JSON response."
        else:
            if parsing_error:
                extraction_error = "parsing_error"
            else:
                extraction_error = f"Expected '{self.output_key}' key in JSON response."

        # Pull out optional metadata when available
        response_id = getattr(response, "id", None)
        usage = getattr(response, "usage", None)

        return {
            "story_text": story_text,
            "model_name": model,
            "messages": messages,
            "response": response,  # non-serializable; strip with make_serializable()
            "response_id": response_id,
            "usage": usage,
            "raw_output": raw_output,
            "parsed_output": parsed,
            "extracted_output": extracted,
            "parsing_error": parsing_error,
            "extraction_error": extraction_error,
            "alignment_error": alignment_error,
            "index_meta": index_meta,
            "validation_report": validation_report,
            "validation_error": validation_error,
            "api_error": api_error,  # None on success; dict on failure/empty
        }
