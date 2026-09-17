from bot import config


def test_get_env_returns_default_when_unset(monkeypatch):
    monkeypatch.delenv("SOME_UNSET_VAR", raising=False)
    assert config.get_env("SOME_UNSET_VAR", "fallback") == "fallback"


def test_get_env_returns_default_when_empty_string(monkeypatch):
    monkeypatch.setenv("SOME_EMPTY_VAR", "")
    assert config.get_env("SOME_EMPTY_VAR", "fallback") == "fallback"


def test_get_env_returns_value_when_set(monkeypatch):
    monkeypatch.setenv("SOME_VAR", "actual-value")
    assert config.get_env("SOME_VAR", "fallback") == "actual-value"


def test_int_env_parses_valid_integer(monkeypatch):
    monkeypatch.setenv("SOME_INT_VAR", "42")
    assert config._int_env("SOME_INT_VAR", 0) == 42


def test_int_env_falls_back_on_invalid_value(monkeypatch):
    monkeypatch.setenv("SOME_INT_VAR", "not-a-number")
    assert config._int_env("SOME_INT_VAR", 7) == 7


def test_int_env_falls_back_when_unset(monkeypatch):
    monkeypatch.delenv("SOME_INT_VAR", raising=False)
    assert config._int_env("SOME_INT_VAR", 7) == 7


def test_is_logged_in_false_without_ai_backend_config(monkeypatch):
    monkeypatch.setattr(config, "API_KEY", "")
    monkeypatch.setattr(config, "BASE_URL", "")
    monkeypatch.setattr(config, "MODEL", "")
    assert config.is_logged_in() is False


def test_is_logged_in_false_for_unknown_platform(monkeypatch):
    monkeypatch.setattr(config, "API_KEY", "key")
    monkeypatch.setattr(config, "BASE_URL", "https://example.com")
    monkeypatch.setattr(config, "MODEL", "gpt-4o-mini")
    monkeypatch.setattr(config, "PLATFORM", "")
    assert config.is_logged_in() is False
