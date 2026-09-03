import pytest
from pydantic import BaseModel

from app.common.errors import StructuredOutputError
from app.llm.client import StructuredLLMClient
from app.llm.providers import MockProvider


class ResponsePayload(BaseModel):
    status: str
    summary: str
    evidence_ids: list[str]


def test_structured_mock_output():
    client = StructuredLLMClient(MockProvider(), max_retries=0)
    result = client.invoke(system_prompt="test", user_prompt="test", response_model=ResponsePayload)
    assert result.status == "MOCK_SUCCESS"


def test_invalid_output_is_blocked():
    class InvalidProvider:
        def complete(self, *, system_prompt: str, user_prompt: str) -> str:
            return "not-json"

    client = StructuredLLMClient(InvalidProvider(), max_retries=1)
    with pytest.raises(StructuredOutputError):
        client.invoke(system_prompt="test", user_prompt="test", response_model=ResponsePayload)
