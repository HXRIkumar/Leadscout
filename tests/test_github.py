"""GitHub enrichment via the official REST API (precision-first, facts-only)."""

import respx
from httpx import Response

from leadscout.research.github import enrich


@respx.mock
def test_enrich_resolves_org_and_facts():
    respx.get("https://api.github.com/orgs/acme").mock(return_value=Response(200, json={
        "login": "acme", "html_url": "https://github.com/acme", "public_repos": 12,
    }))
    respx.get("https://api.github.com/orgs/acme/repos").mock(return_value=Response(200, json=[
        {"name": "web", "language": "Python", "pushed_at": "2026-07-01T00:00:00Z",
         "topics": [], "description": "our app"},
        {"name": "ml-models", "language": "Python", "pushed_at": "2026-06-01T00:00:00Z",
         "topics": ["machine-learning"], "description": "", "html_url": "https://github.com/acme/ml-models"},
    ]))
    p = enrich("acme.com", "Acme")
    assert p is not None
    assert p.login == "acme" and p.public_repos == 12
    assert "Python" in p.top_languages
    assert p.has_ml_ai_repos is True
    assert p.ml_evidence.endswith("ml-models")
    assert p.recently_active is True


@respx.mock
def test_enrich_none_when_no_matching_org():
    respx.get("https://api.github.com/orgs/ghost").mock(return_value=Response(404))
    assert enrich("ghost.io", "Ghost") is None   # precision-first: no fuzzy fallback
