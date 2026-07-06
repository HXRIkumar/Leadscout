"""GitHub enrichment via the official REST API (compliant, SPEC §7.5).

Adds engineering-context facts to a lead: public repo count, primary languages,
whether they run ML/AI repos, and recent activity — useful qualification signal
(small eng team + no ML platform = a better fit for an outsourced deflection pilot).

Precision-first: we only resolve the org by the domain root (e.g. plausible.io ->
github.com/plausible), never a fuzzy name search — wrong-company facts would violate
"never fabricate". Facts are cited by the GitHub org URL. Best-effort: any failure
(no org, rate limit, offline) returns None and the brief simply omits the section.
Facts-only: this does NOT auto-disqualify (avoids false positives).
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import httpx

from ..config import get_settings
from ..logging import get_logger
from .fetch import normalize_domain

log = get_logger(__name__)

_ML_KEYWORDS = ("ml", "ai", "llm", "machine-learning", "ml-platform", "mlops", "deep-learning")
_ACTIVE_DAYS = 90


@dataclass
class GitHubProfile:
    login: str
    url: str
    public_repos: int
    top_languages: list[str] = field(default_factory=list)
    has_ml_ai_repos: bool = False
    recently_active: bool = False
    ml_evidence: str = ""


def _headers(token: str) -> dict:
    h = {"Accept": "application/vnd.github+json", "User-Agent": get_settings().user_agent}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def enrich(domain: str, company_name: str = "") -> GitHubProfile | None:
    s = get_settings()
    login = normalize_domain(domain).split(".")[0]
    if not login:
        return None
    headers = _headers(s.github_token)
    try:
        org = httpx.get(f"https://api.github.com/orgs/{login}", headers=headers, timeout=15)
        if org.status_code != 200:
            return None
        org_data = org.json()
        repos_resp = httpx.get(
            f"https://api.github.com/orgs/{login}/repos",
            headers=headers, params={"sort": "pushed", "per_page": 30}, timeout=15,
        )
        repos = repos_resp.json() if repos_resp.status_code == 200 else []
    except (httpx.HTTPError, ValueError) as e:
        log.info("github enrichment failed for %s: %s", login, e)
        return None
    if not isinstance(repos, list):
        repos = []

    langs = Counter(r.get("language") for r in repos if r.get("language"))
    cutoff = (datetime.now(UTC) - timedelta(days=_ACTIVE_DAYS)).isoformat()
    recently_active = any((r.get("pushed_at") or "") >= cutoff for r in repos)

    has_ml, ml_evidence = False, ""
    for r in repos:
        hay = f"{r.get('name', '')} {r.get('description') or ''} {' '.join(r.get('topics', []) or [])}".lower()
        if any(re.search(rf"\b{re.escape(k)}\b", hay) for k in _ML_KEYWORDS):
            has_ml = True
            ml_evidence = r.get("html_url") or r.get("name") or ""
            break

    return GitHubProfile(
        login=login,
        url=org_data.get("html_url", f"https://github.com/{login}"),
        public_repos=int(org_data.get("public_repos", 0) or 0),
        top_languages=[lang for lang, _ in langs.most_common(3)],
        has_ml_ai_repos=has_ml,
        recently_active=recently_active,
        ml_evidence=ml_evidence,
    )
