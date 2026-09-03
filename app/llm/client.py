import json
import logging
from time import sleep
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.common.errors import StructuredOutputError
from app.llm.providers import LLMProvider

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)


class StructuredLLMClient:
    def __init__(self, provider: LLMProvider, *, max_retries: int = 2, max_output_chars: int = 8000) -> None:
        self.provider = provider
        self.max_retries = max_retries
        self.max_output_chars = max_output_chars

    def invoke(self, *, system_prompt: str, user_prompt: str, response_model: type[T]) -> T:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                raw = self.provider.complete(system_prompt=system_prompt, user_prompt=user_prompt)
                if len(raw) > self.max_output_chars:
                    raise StructuredOutputError("LLM output exceeded maximum length")
                payload = json.loads(raw)
                return response_model.model_validate(payload)
            except (json.JSONDecodeError, ValidationError, StructuredOutputError) as exc:
                last_error = exc
                logger.warning("structured_output_retry attempt=%s error_type=%s", attempt + 1, type(exc).__name__)
                if attempt < self.max_retries:
                    sleep(min(0.05 * (2**attempt), 0.2))
        raise StructuredOutputError("LLM structured output validation failed") from last_error

