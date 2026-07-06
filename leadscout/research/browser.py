"""B7 — Browser fallback (single Playwright function).

Evidence (SPEC §3.2/§4.1): API/script-first beats browser-driving on cost and
reliability, so this is a *single fallback*, invoked only when `polite_fetch` gets
thin/JS-only content on a robots-allowed page — never a swarm, never around robots.

Dependency-guarded: if Playwright isn't installed (`pip install -e ".[browser]"`
+ `playwright install chromium`) or the render fails, it returns None and the
caller keeps its non-browser result. Deeper agentic research is reserved (B7 later).
"""

from __future__ import annotations

from ..config import get_settings
from ..logging import get_logger

log = get_logger(__name__)


def browser_fetch(url: str, *, timeout: int | None = None) -> str | None:
    """Render a page with headless Chromium and return its HTML, or None on any failure."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.info("playwright not installed; browser fallback unavailable ([browser] extra)")
        return None

    s = get_settings()
    ms = (timeout or s.crawl_timeout_seconds) * 1000
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page(user_agent=s.user_agent)
                page.goto(url, timeout=ms, wait_until="networkidle")
                return page.content()
            finally:
                browser.close()
    except Exception as e:  # launch/goto/timeout — stay resilient
        log.info("browser fallback failed for %s: %s", url, e)
        return None
