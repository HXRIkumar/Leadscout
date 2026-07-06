"""Careers-page probe (SPEC §3.1 A2, §7.4).

Thin helper: does this company have a reachable careers page? A careers page is a
positive niche signal (support hiring shows up there) and a cheap qualifier during
discovery. Uses the central polite_fetch.
"""

from __future__ import annotations

from ..research.fetch import canonical_url, polite_fetch

_CAREERS_PATHS = ["/careers", "/jobs", "/careers/", "/company/careers", "/about/careers"]


def find_careers_url(domain: str) -> str | None:
    base = canonical_url(domain)
    for path in _CAREERS_PATHS:
        url = base + path
        r = polite_fetch(url)
        if r.ok:
            return r.url
    return None
