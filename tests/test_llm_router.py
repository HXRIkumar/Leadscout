"""LLM router provider-routing + GPT-5 reasoning-model request shape + budget."""

import json

import respx
from httpx import Response

from leadscout.config import get_settings
from leadscout.db import init_db
from leadscout.llm import llm_complete
from leadscout.llm.budget import estimate_inr
from leadscout.llm.providers import _is_reasoning_model

_OPENAI = "https://api.openai.com/v1/chat/completions"
_GROQ = "https://api.groq.com/openai/v1/chat/completions"


def test_is_reasoning_model():
    assert _is_reasoning_model("gpt-5-mini")
    assert _is_reasoning_model("gpt-5")
    assert _is_reasoning_model("o3-mini")
    assert not _is_reasoning_model("llama-3.1-8b-instant")
    assert not _is_reasoning_model("gpt-4o-mini")
    assert not _is_reasoning_model("claude-haiku-4-5")


@respx.mock
def test_frontier_routes_to_openai_gpt5_no_temperature(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("FRONTIER_PROVIDER", "openai")
    monkeypatch.setenv("FRONTIER_MODEL", "gpt-5-mini")
    get_settings.cache_clear()
    init_db()

    route = respx.post(_OPENAI).mock(return_value=Response(200, json={
        "choices": [{"message": {"content": "{\"bottleneck\": \"x\"}"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }))

    res = llm_complete("diagnose this company", task="diagnosis", json_mode=True)
    assert res.provider == "openai"
    assert res.model == "gpt-5-mini"       # honors FRONTIER_MODEL, not a hardcoded default

    body = json.loads(route.calls.last.request.content)
    assert body["model"] == "gpt-5-mini"
    assert "temperature" not in body       # reasoning models reject non-default temperature
    assert body["response_format"]["type"] == "json_object"


@respx.mock
def test_bulk_routes_to_groq_with_temperature(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test")
    get_settings.cache_clear()
    init_db()

    route = respx.post(_GROQ).mock(return_value=Response(200, json={
        "choices": [{"message": {"content": "[]"}}],
        "usage": {"prompt_tokens": 3, "completion_tokens": 1},
    }))

    res = llm_complete("extract signals", task="extraction")
    assert res.provider == "groq"
    body = json.loads(route.calls.last.request.content)
    assert body["temperature"] == 0        # non-reasoning model keeps deterministic temp


@respx.mock
def test_anthropic_still_selectable_by_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("FRONTIER_PROVIDER", "anthropic")
    monkeypatch.setenv("FRONTIER_MODEL", "claude-haiku-4-5")
    get_settings.cache_clear()
    init_db()

    respx.post("https://api.anthropic.com/v1/messages").mock(return_value=Response(200, json={
        "content": [{"type": "text", "text": "ok"}],
        "usage": {"input_tokens": 8, "output_tokens": 4},
    }))

    res = llm_complete("diagnose", task="diagnosis")
    assert res.provider == "anthropic"     # re-enable is env-only, no code change
    assert res.model == "claude-haiku-4-5"


def test_budget_provider_agnostic():
    assert estimate_inr("gpt-5-mini", 1_000_000, 1_000_000) > 0
    assert estimate_inr("claude-haiku-4-5", 1_000_000, 1_000_000) > 0
    # an unlisted model still gets a positive (conservative) estimate, never zero
    assert estimate_inr("some-future-model", 1_000_000, 0) > 0
