from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    bailian_api_key: str = Field(default="", validation_alias="BAILIAN_API_KEY")
    bailian_base_url: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        validation_alias="BAILIAN_BASE_URL",
    )
    bailian_workspace_id: str = Field(
        default="", validation_alias="BAILIAN_WORKSPACE_ID"
    )
    chat_model: str = Field(default="qwen-plus", validation_alias="CHAT_MODEL")
    embedding_model: str = Field(
        default="text-embedding-v4", validation_alias="EMBEDDING_MODEL"
    )
    rerank_model: str = Field(
        default="qwen3-rerank", validation_alias="RERANK_MODEL"
    )
    database_url: str = Field(
        default="sqlite:///./data/docpilot.db", validation_alias="DATABASE_URL"
    )
    qdrant_url: str = Field(
        default="http://127.0.0.1:6333", validation_alias="QDRANT_URL"
    )

    @property
    def model_configured(self) -> bool:
        return bool(self.bailian_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
