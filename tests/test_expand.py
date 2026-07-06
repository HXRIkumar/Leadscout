"""Competitor / similar-company expansion (LLM-suggest + prefilter, quality-safeguarded)."""

import json

import respx
from httpx import Response

from leadscout.config import get_settings
from leadscout.db import init_db
from leadscout.sources.expand import similar_companies

_OPENAI = "https://api.openai.com/v1/chat/completions"


@respx.mock
def test_expand_suggests_and_prefilters(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("FRONTIER_PROVIDER", "openai")
    monkeypatch.setenv("FRONTIER_MODEL", "gpt-5-mini")
    get_settings.cache_clear()
    init_db()

    payload = {"companies": [
        {"name": "Beta", "domain": "beta.com", "one_liner": "billing SaaS with a help center"},
        {"name": "Studio", "domain": "studio.com", "one_liner": "we are a software development agency"},
        {"name": "Self", "domain": "acme.com", "one_liner": "the seed"},
    ]}
    respx.post(_OPENAI).mock(return_value=Response(200, json={
        "choices": [{"message": {"content": json.dumps(payload)}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }))

    cands = similar_companies("acme.com", context="billing platform", verify=False, persist=False)
    domains = [c.domain for c in cands]
    assert "beta.com" in domains
    assert "studio.com" not in domains   # agency prefiltered out (quality gate)
    assert "acme.com" not in domains     # seed skipped


def test_expand_without_llm_is_graceful():
    get_settings.cache_clear()
    assert similar_companies("acme.com", context="x", verify=False, persist=False) == []
