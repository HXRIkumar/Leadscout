"""Product-launch detection via RSS/Atom feeds (compliant — the site's own feed).

Recent feed entries evidence product velocity → docs lag → support load. Each recent
entry becomes a dated `docs_lagging` signal (title as the verbatim quote, feed URL as
source, recency in days), verified against the raw feed XML (fail-closed). Stdlib XML
parsing (no new deps); tries a few common feed paths and stops at the first hit.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

from ..logging import get_logger
from .extract import RAG, SignalCandidate
from .fetch import canonical_url, normalize_domain, polite_fetch

log = get_logger(__name__)

_FEED_PATHS = ["/feed", "/rss.xml", "/blog/rss.xml", "/feed.xml", "/atom.xml", "/blog/feed", "/changelog.xml"]
_RECENT_DAYS = 180


def _localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def parse_feed(xml_text: str) -> list[tuple[str, str]]:
    """Return [(title, date_str)] for RSS <item> and Atom <entry> elements."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    out: list[tuple[str, str]] = []
    for el in root.iter():
        if _localname(el.tag) not in ("item", "entry"):
            continue
        title, date = "", ""
        for child in el:
            ln = _localname(child.tag)
            if ln == "title" and child.text:
                title = child.text.strip()
            elif ln in ("pubdate", "published", "updated", "date") and child.text and not date:
                date = child.text.strip()
        if title:
            out.append((title, date))
    return out


def days_ago(date_str: str) -> int | None:
    if not date_str:
        return None
    dt = None
    try:
        dt = parsedate_to_datetime(date_str)   # RFC-822 (RSS pubDate)
    except (TypeError, ValueError):
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))  # ISO-8601 (Atom)
        except ValueError:
            return None
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return (datetime.now(UTC) - dt).days


def detect_product_launches(domain: str, *, max_entries: int = 5, use_cache: bool = True) -> list[SignalCandidate]:
    """Fetch the company's feed and emit dated docs_lagging signals for recent entries."""
    from .extract import verify_signals
    domain = normalize_domain(domain)
    base = canonical_url(domain)
    feed_url, xml_text, entries = "", "", []
    for path in _FEED_PATHS:
        r = polite_fetch(base + path, use_cache=use_cache)
        if r.status == 200 and ("<item" in r.html.lower() or "<entry" in r.html.lower()):
            parsed = parse_feed(r.html)
            if parsed:
                feed_url, xml_text, entries = r.url, r.html, parsed
                break
    if not entries:
        return []

    candidates: list[SignalCandidate] = []
    for title, date in entries[:max_entries]:
        recency = days_ago(date)
        if recency is not None and recency > _RECENT_DAYS:
            continue
        candidates.append(SignalCandidate(
            signal_type="docs_lagging", evidence_quote=title, source_url=feed_url,
            confidence=0.5, mapped_project=RAG, recency_days=recency,
        ))
    verified = verify_signals(candidates, {feed_url: xml_text})
    log.info("feeds: %d recent launch entries for %s", len(verified), domain)
    return verified
