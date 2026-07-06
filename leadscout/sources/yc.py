"""YC directory adapter (SPEC §7.2). Fragile by design; fails gracefully.

Queries the public YC Algolia index exactly as the site frontend does. The public
search key rotates — we re-extract it from the site when the query fails, and
return [] if we can't. Niche filtering is left to the prefilter.
"""

from __future__ import annotations

import re

import httpx

from ..logging import get_logger
from ..research.fetch import normalize_domain
from .base import Candidate

log = get_logger(__name__)

name = "yc"

_APP_ID = "45BWZJ1SGC"
_INDEX = "YCCompany_production"
_KEY_RE = re.compile(r'"?(?:apiKey|algolia[_-]?api[_-]?key)"?\s*[:=]\s*"([0-9a-f]{32})"', re.IGNORECASE)


def _extract_key() -> str | None:
    """Best-effort: scrape a current public Algolia search key from the YC site."""
    for url in ("https://www.ycombinator.com/companies", "https://www.ycombinator.com/"):
        try:
            r = httpx.get(url, timeout=15, follow_redirects=True)
            m = _KEY_RE.search(r.text)
            if m:
                return m.group(1)
        except httpx.HTTPError:
            continue
    return None


class YCDirectory:
    name = "yc"

    def fetch(self, *, limit: int = 50) -> list[Candidate]:
        key = _extract_key()
        if not key:
            log.info("YC adapter: could not extract Algolia key (fragile by design) — skipping")
            return []
        url = f"https://{_APP_ID.lower()}-dsn.algolia.net/1/indexes/{_INDEX}/query"
        headers = {"X-Algolia-Application-Id": _APP_ID, "X-Algolia-API-Key": key, "Content-Type": "application/json"}
        body = {"params": f"hitsPerPage={limit}&query="}
        try:
            r = httpx.post(url, headers=headers, json=body, timeout=15)
            r.raise_for_status()
            hits = r.json().get("hits", [])
        except (httpx.HTTPError, ValueError) as e:
            log.info("YC query failed: %s", e)
            return []

        out: list[Candidate] = []
        seen: set[str] = set()
        for h in hits:
            website = h.get("website") or ""
            if not website:
                continue
            domain = normalize_domain(website)
            if not domain or domain in seen:
                continue
            seen.add(domain)
            out.append(Candidate(
                name=h.get("name", domain), domain=domain, source="yc",
                description=(h.get("one_liner") or "")[:300], url=website,
                extra={"batch": h.get("batch"), "team_size": h.get("team_size"), "tags": h.get("tags")},
            ))
        log.info("YC adapter: %d candidates", len(out))
        return out
