from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    llm_provider: str = "mock"
    llm_model: str = "mock-model"
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_timeout_seconds: float = Field(default=30.0, gt=0)
    llm_max_retries: int = Field(default=2, ge=0, le=5)
    max_output_chars: int = Field(default=8000, ge=100, le=100000)
    rag_top_k: int = Field(default=3, ge=1, le=10)
    knowledge_dir: Path = Path("data/knowledge")
    vector_index_path: Path = Path("data/index/vector_index.json")
    source_data_dir: Path = Path("data/source")
    model_artifact_path: Path = Path("artifacts/models/champion.joblib")
    model_metadata_path: Path = Path("artifacts/reports/model_metadata.json")
    workflow_version: str = "0.1.0-draft"
    model_version: str = "mock-untrained"
    prompt_version: str = "0.1.0-draft"


@lru_cache
def get_settings() -> Settings:
    return Settings()
