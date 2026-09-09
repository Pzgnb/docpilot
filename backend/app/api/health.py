from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import text

from app.db.base import SessionDependency


router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok"]
    database: Literal["ok"]
    qdrant: Literal["not_checked"]
    models: Literal["configured", "not_configured"]


@router.get("/api/health", response_model=HealthResponse)
def health(request: Request, session: SessionDependency) -> HealthResponse:
    session.execute(text("SELECT 1"))

    return HealthResponse(
        status="ok",
        database="ok",
        qdrant="not_checked",
        models=(
            "configured"
            if request.app.state.settings.model_configured
            else "not_configured"
        ),
    )
