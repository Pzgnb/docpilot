from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(max_length=200)
    description: str = Field(default="", max_length=2000)

    @field_validator("name")
    @classmethod
    def trim_and_require_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("知识库名称不能为空")
        return name


class KnowledgeBaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str
    document_count: int
    created_at: datetime
    updated_at: datetime
