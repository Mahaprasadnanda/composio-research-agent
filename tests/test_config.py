"""Tests for configuration management and security safeguards."""

import pytest

from research_agent.config import (
    ConfigurationError,
    Settings,
    check_missing_credentials,
    load_settings,
    mask_secret,
)


def test_mask_secret_none_or_empty():
    assert mask_secret(None) == "[NOT SET]"
    assert mask_secret("") == "[NOT SET]"
    assert mask_secret("   ") == "[NOT SET]"


def test_mask_secret_short_string():
    assert mask_secret("abc") == "***REDACTED***"
    assert mask_secret("12345") == "***REDACTED***"


def test_mask_secret_standard_key():
    masked = mask_secret("gsk_1234567890abcdef")
    assert masked.startswith("gsk")
    assert masked.endswith("ef")
    assert "1234567890" not in masked
    assert "..." in masked


def test_settings_repr_never_leaks_secrets():
    settings = Settings(
        groq_api_key="gsk_secret_groq_token_value_here",
        composio_api_key="cmp_secret_composio_token_value_here",
        groq_model="openai/gpt-oss-120b",
    )
    repr_str = repr(settings)
    str_str = str(settings)

    # Must not contain raw secret values
    assert "gsk_secret_groq_token_value_here" not in repr_str
    assert "cmp_secret_composio_token_value_here" not in repr_str
    assert "gsk_secret_groq_token_value_here" not in str_str
    assert "cmp_secret_composio_token_value_here" not in str_str

    # Must contain masked indicators
    assert "..." in repr_str
    assert settings.groq_model in repr_str


def test_check_missing_credentials_detects_absent():
    empty_env = {}
    missing = check_missing_credentials(empty_env)
    assert len(missing) == 2
    assert any("GROQ_API_KEY" in err for err in missing)
    assert any("COMPOSIO_API_KEY" in err for err in missing)


def test_check_missing_credentials_detects_placeholders():
    placeholder_env = {
        "GROQ_API_KEY": "your_groq_api_key_here",
        "COMPOSIO_API_KEY": "placeholder",
    }
    missing = check_missing_credentials(placeholder_env)
    assert len(missing) == 2
    assert any("GROQ_API_KEY" in err for err in missing)
    assert any("COMPOSIO_API_KEY" in err for err in missing)


def test_check_missing_credentials_accepts_valid():
    valid_env = {
        "GROQ_API_KEY": "gsk_test_key_12345",
        "COMPOSIO_API_KEY": "cmp_test_key_67890",
    }
    missing = check_missing_credentials(valid_env)
    assert missing == []


def test_load_settings_missing_credentials_raises_configuration_error(monkeypatch, tmp_path):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("COMPOSIO_API_KEY", raising=False)
    monkeypatch.setattr("research_agent.config.PROJECT_ROOT", tmp_path)

    with pytest.raises(ConfigurationError) as exc_info:
        load_settings(env_file=None)

    error_message = str(exc_info.value)
    assert "GROQ_API_KEY" in error_message
    assert "COMPOSIO_API_KEY" in error_message
    assert "Action required" in error_message


def test_load_settings_success(monkeypatch, tmp_path):
    monkeypatch.setattr("research_agent.config.PROJECT_ROOT", tmp_path)
    monkeypatch.setenv("GROQ_API_KEY", "gsk_valid_mock_key_abc123")
    monkeypatch.setenv("COMPOSIO_API_KEY", "cmp_valid_mock_key_xyz789")
    monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-120b")

    settings = load_settings(env_file=None)
    assert settings.groq_api_key == "gsk_valid_mock_key_abc123"
    assert settings.composio_api_key == "cmp_valid_mock_key_xyz789"
    assert settings.groq_model == "openai/gpt-oss-120b"


def test_load_settings_default_model(monkeypatch, tmp_path):
    from research_agent.config import DEFAULT_GROQ_MODEL

    monkeypatch.setattr("research_agent.config.PROJECT_ROOT", tmp_path)
    monkeypatch.setenv("GROQ_API_KEY", "gsk_valid_mock_key_abc123")
    monkeypatch.setenv("COMPOSIO_API_KEY", "cmp_valid_mock_key_xyz789")
    monkeypatch.delenv("GROQ_MODEL", raising=False)

    settings = load_settings(env_file=None)
    assert settings.groq_model == "openai/gpt-oss-120b"
    assert settings.groq_model == DEFAULT_GROQ_MODEL


def test_load_settings_custom_model_override(monkeypatch, tmp_path):
    monkeypatch.setattr("research_agent.config.PROJECT_ROOT", tmp_path)
    monkeypatch.setenv("GROQ_API_KEY", "gsk_valid_mock_key_abc123")
    monkeypatch.setenv("COMPOSIO_API_KEY", "cmp_valid_mock_key_xyz789")
    monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-20b")

    settings = load_settings(env_file=None)
    assert settings.groq_model == "openai/gpt-oss-20b"

