import os

from app.infrastructure.config.settings import Settings


class TestSettings:
    def test_loads_openai_model_alias_from_env_file(self, monkeypatch) -> None:
        monkeypatch.delenv("OPENAI_MODEL", raising=False)
        monkeypatch.delenv("LLM_MODEL", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        settings = Settings.from_env()

        assert settings.openai_api_key
        assert settings.llm_model == "gpt-4o"

    def test_prefers_explicit_environment_over_env_file(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENAI_MODEL", "gpt-5.4")

        settings = Settings.from_env()

        assert settings.llm_model == "gpt-5.4"