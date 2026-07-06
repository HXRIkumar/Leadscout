"""Search-based discovery via an official web-search API (compliant).

Uses the Brave Search API (official, ToS-permitted, free tier ~2k queries/mo) to
turn a niche-targeted query into candidate company domains. Results are CANDIDATES
— nothing is asserted as fact until a `brief` verifies it — so this never fabricates.
Platform/aggregator domains are filtered out. Without a key the adapter no-ops
gracefully (returns [] with a log line), so the interface is present and activates
the moment SEARCH_API_KEY is set (decision D9).
"""

from __future__ import annotations

import httpx

from ..config import get_settings
from ..logging import get_logger
from ..research.fetch import normalize_domain
from .base import Candidate

log = get_logger(__name__)

name = "search"

# Aggregators/platforms that are never the prospect themselves.
_PLATFORMS = {
    "github.com", "linkedin.com", "twitter.com", "x.com", "reddit.com", "youtube.com",
    "medium.com", "wikipedia.org", "g2.com", "capterra.com", "crunchbase.com",
    "producthunt.com", "facebook.com", "instagram.com", "gartner.com", "trustpilot.com",
    "glassdoor.com", "indeed.com", "ycombinator.com", "google.com", "apple.com",
}


def _is_platform(domain: str) -> bool:
    return domain in _PLATFORMS or domain.endswith((".google.com", ".amazon.com"))


class SearchSource:
    """Discovery adapter (Source protocol). Query is instance state."""

    name = "search"

    def __init__(self, query: str):
        self.query = query

    def fetch(self, *, limit: int = 20) -> list[Candidate]:
        s = get_settings()
        if not s.search_api_key:
            log.info("search discovery needs SEARCH_API_KEY (Brave). Skipping (see D9).")
            return []
        try:
            r = httpx.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={"X-Subscription-Token": s.search_api_key, "Accept": "application/json"},
                params={"q": self.query, "count": min(20, limit)},
                timeout=20,
            )
            r.raise_for_status()
            results = r.json().get("web", {}).get("results", [])
        except (httpx.HTTPError, ValueError) as e:
            log.warning("search failed: %s", e)
            return []

        out: list[Candidate] = []
        seen: set[str] = set()
        for item in results:
            domain = normalize_domain(item.get("url", ""))
            if not domain or domain in seen or _is_platform(domain):
                continue
            seen.add(domain)
            out.append(Candidate(
                name=(item.get("title") or domain)[:60],
                domain=domain, source="search",
                description=(item.get("description") or "")[:300],
                url=item.get("url", ""),
            ))
        log.info("search adapter: %d candidates", len(out))
        return out
