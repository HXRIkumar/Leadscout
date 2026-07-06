"""HN "Who is hiring" adapter (SPEC §7.1). Best-effort, fails gracefully.

Algolia to find the current thread -> Firebase for top-level comments (job posts).
Each post typically starts "Company | Role | Location | ...". We take the company
name and first linked domain as a candidate. Niche filtering happens in the
prefilter, not here (finding is a commodity).
"""

from __future__ import annotations

import re

import httpx

from ..logging import get_logger
from ..research.fetch import normalize_domain
from .base import Candidate

log = get_logger(__name__)

name = "hn"

_ALGOLIA = "https://hn.algolia.com/api/v1/search_by_date"
_FIREBASE = "https://hacker-news.firebaseio.com/v0/item/{}.json"
_URL_RE = re.compile(r'https?://[^\s"\'<>)]+', re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")


def _latest_thread_id() -> int | None:
    try:
        r = httpx.get(_ALGOLIA, params={"tags": "story,author_whoishiring", "hitsPerPage": 6}, timeout=15)
        r.raise_for_status()
        for hit in r.json().get("hits", []):
            title = (hit.get("title") or "").lower()
            if "who is hiring" in title:
                return int(hit["objectID"])
    except (httpx.HTTPError, KeyError, ValueError) as e:
        log.info("HN thread lookup failed: %s", e)
    return None


def _item(item_id: int) -> dict | None:
    try:
        r = httpx.get(_FIREBASE.format(item_id), timeout=15)
        r.raise_for_status()
        return r.json()
    except (httpx.HTTPError, ValueError):
        return None


def _parse_comment(text: str) -> Candidate | None:
    plain = _TAG_RE.sub(" ", text or "")
    plain = re.sub(r"\s+", " ", plain).strip()
    if not plain:
        return None
    urls = _URL_RE.findall(text or "")
    domain = normalize_domain(urls[0]) if urls else ""
    if not domain or "news.ycombinator" in domain:
        return None
    head = re.split(r"[|–\-–—]", plain)[0].strip()
    name_ = head[:60] if head else domain
    return Candidate(name=name_, domain=domain, source="hn", description=plain[:300], url=urls[0] if urls else "")


class HNWhoIsHiring:
    name = "hn"

    def fetch(self, *, limit: int = 50) -> list[Candidate]:
        thread = _latest_thread_id()
        if not thread:
            return []
        root = _item(thread)
        if not root:
            return []
        kids = root.get("kids", [])[: limit * 3]
        out: list[Candidate] = []
        seen: set[str] = set()
        for kid in kids:
            if len(out) >= limit:
                break
            item = _item(kid)
            if not item or item.get("deleted") or item.get("dead"):
                continue
            cand = _parse_comment(item.get("text", ""))
            if cand and cand.domain not in seen:
                seen.add(cand.domain)
                out.append(cand)
        log.info("HN adapter: %d candidates", len(out))
        return out
