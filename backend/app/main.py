from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.config import Settings, get_settings
from app.db.base import Base, Database


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        database = Database(resolved_settings.database_url)
        application.state.database = database
        Base.metadata.create_all(database.engine)
        try:
            yield
        finally:
            database.engine.dispose()

    application = FastAPI(title="DocPilot API", version="0.1.0", lifespan=lifespan)
    application.state.settings = resolved_settings
    application.include_router(health_router)
    return application


app = create_app()
