from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
    settings = Settings(
        _env_file=None,
        BAILIAN_API_KEY="",
        DATABASE_URL=f"sqlite:///{tmp_path / 'test.db'}",
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client
