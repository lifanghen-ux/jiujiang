from app.config import Settings, get_settings
from app.llm.client import StructuredLLMClient
from app.llm.providers import MockProvider, OpenAICompatibleProvider


def build_llm_client(settings: Settings | None = None) -> StructuredLLMClient:
    settings = settings or get_settings()
    provider_name = settings.llm_provider.strip().lower()
    if provider_name == "mock":
        provider = MockProvider()
    elif provider_name in {"deepseek", "openai", "openai-compatible"}:
        provider = OpenAICompatibleProvider(
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            base_url=settings.llm_base_url,
            timeout_seconds=settings.llm_timeout_seconds,
        )
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")
    return StructuredLLMClient(
        provider,
        max_retries=settings.llm_max_retries,
        max_output_chars=settings.max_output_chars,
    )
