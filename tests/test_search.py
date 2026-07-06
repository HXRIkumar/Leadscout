"""Search-based discovery adapter (Brave), platform filtering + graceful no-key."""

import respx
from httpx import Response

from leadscout.config import get_settings
from leadscout.sources.search import SearchSource

_BRAVE = "https://api.search.brave.com/res/v1/web/search"


@respx.mock
def test_search_filters_platforms(monkeypatch):
    monkeypatch.setenv("SEARCH_API_KEY", "brave-test")
    get_settings.cache_clear()
    respx.get(_BRAVE).mock(return_value=Response(200, json={"web": {"results": [
        {"url": "https://acme.io/", "title": "Acme", "description": "billing SaaS"},
        {"url": "https://github.com/acme", "title": "gh", "description": "repo"},
        {"url": "https://beta.com/pricing", "title": "Beta", "description": "support tool"},
    ]}}))
    domains = [c.domain for c in SearchSource("b2b saas help center").fetch(limit=10)]
    assert "acme.io" in domains and "beta.com" in domains
    assert "github.com" not in domains          # platform filtered out


def test_search_no_key_is_graceful():
    get_settings.cache_clear()
    assert SearchSource("q").fetch() == []      # no SEARCH_API_KEY -> [] (no crash)
