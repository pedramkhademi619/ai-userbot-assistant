from bot import memory


def test_cache_response_roundtrip():
    memory.cache_response("Hello there", "Hi!")
    assert memory.get_cached_response("  Hello There  ") == "Hi!"
    assert memory.get_cached_response("something else") is None


def test_cache_response_evicts_when_full(monkeypatch):
    memory.response_cache.clear()
    for i in range(100):
        memory.cache_response(f"msg-{i}", f"reply-{i}")
    assert len(memory.response_cache) == 100

    memory.cache_response("one-more", "reply")
    assert len(memory.response_cache) == 100
    assert memory.get_cached_response("one-more") == "reply"


def test_rate_limit_allows_then_blocks(monkeypatch):
    monkeypatch.setattr(memory.config, "RATE_LIMIT_COUNT", 3)
    monkeypatch.setattr(memory.config, "RATE_LIMIT_WINDOW", 60)
    memory.user_requests.pop("user-a", None)

    assert memory.is_rate_limited("user-a") is False
    assert memory.is_rate_limited("user-a") is False
    assert memory.is_rate_limited("user-a") is False
    assert memory.is_rate_limited("user-a") is True


def test_rate_limit_is_per_user(monkeypatch):
    monkeypatch.setattr(memory.config, "RATE_LIMIT_COUNT", 1)
    monkeypatch.setattr(memory.config, "RATE_LIMIT_WINDOW", 60)
    memory.user_requests.pop("user-b1", None)
    memory.user_requests.pop("user-b2", None)

    assert memory.is_rate_limited("user-b1") is False
    assert memory.is_rate_limited("user-b2") is False
    assert memory.is_rate_limited("user-b1") is True
    assert memory.is_rate_limited("user-b2") is True


def test_rate_limit_window_expires(monkeypatch):
    monkeypatch.setattr(memory.config, "RATE_LIMIT_COUNT", 1)
    monkeypatch.setattr(memory.config, "RATE_LIMIT_WINDOW", 0)
    memory.user_requests.pop("user-c", None)

    assert memory.is_rate_limited("user-c") is False
    assert memory.is_rate_limited("user-c") is False
