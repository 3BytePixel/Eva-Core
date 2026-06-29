from __future__ import annotations

from fastapi.testclient import TestClient

from eva_core.app import create_app
from eva_core.providers import ChatMessage, ChatResult
from eva_core.service import EvaCore


def _make_client(all_keys_settings, reply: str = "stub reply") -> TestClient:
    core = EvaCore(all_keys_settings)

    def fake_chat(provider, messages, **kwargs):
        assert all(isinstance(m, ChatMessage) for m in messages)
        return ChatResult(provider=provider, model="stub-model", content=reply)

    core.chat = fake_chat  # type: ignore[method-assign]
    return TestClient(create_app(core))


def test_health():
    from eva_core.config import Settings

    client = TestClient(create_app(EvaCore(Settings(_env_file=None))))
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_status_lists_providers(all_keys_settings):
    client = _make_client(all_keys_settings)
    data = client.get("/api/status").json()
    names = {p["name"] for p in data["providers"]}
    assert names == {"openai", "xai", "gemini", "claude"}
    assert all(p["available"] for p in data["providers"])
    assert data["speech"]["available"] is True


def test_index_served(all_keys_settings):
    client = _make_client(all_keys_settings)
    res = client.get("/")
    assert res.status_code == 200
    assert "Eva-Core" in res.text


def test_chat_endpoint(all_keys_settings):
    client = _make_client(all_keys_settings, reply="hi there")
    res = client.post(
        "/api/chat",
        json={"provider": "openai", "messages": [{"role": "user", "content": "hello"}]},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["content"] == "hi there"
    assert body["provider"] == "openai"


def test_chat_unknown_provider(all_keys_settings):
    # Use a real core so the unknown-provider error path is exercised.
    client = TestClient(create_app(EvaCore(all_keys_settings)))
    res = client.post(
        "/api/chat",
        json={"provider": "does-not-exist", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert res.status_code == 400
