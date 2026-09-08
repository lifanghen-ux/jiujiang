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


def test_retry_receives_schema_and_validation_feedback():
    class RepairingProvider:
        def __init__(self) -> None:
            self.prompts: list[str] = []

        def complete(self, *, system_prompt: str, user_prompt: str) -> str:
            self.prompts.append(user_prompt)
            if len(self.prompts) == 1:
                return '{"status": 1}'
            return '{"status":"OK","summary":"fixed","evidence_ids":[]}'

    provider = RepairingProvider()
    client = StructuredLLMClient(provider, max_retries=1)
    result = client.invoke(system_prompt="test", user_prompt="payload", response_model=ResponsePayload)

    assert result.status == "OK"
    assert "JSON Schema" in provider.prompts[0]
    assert "上一次输出未通过校验" in provider.prompts[1]
