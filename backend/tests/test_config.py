from app.core.config import Settings


def test_settings_allows_local_start_without_bailian_key(monkeypatch):
    monkeypatch.delenv("BAILIAN_API_KEY", raising=False)

    settings = Settings(_env_file=None)

    assert settings.model_configured is False
    assert settings.chat_model == "qwen-plus"
    assert settings.embedding_model == "text-embedding-v4"


def test_settings_reports_models_configured_when_key_is_present():
    settings = Settings(_env_file=None, BAILIAN_API_KEY="sk-test-placeholder")

    assert settings.model_configured is True
