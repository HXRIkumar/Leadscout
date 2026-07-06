"""B7 browser fallback — must degrade gracefully when Playwright is absent."""

from leadscout.research.browser import browser_fetch


def test_browser_fetch_returns_none_without_playwright():
    # playwright is an optional extra (not installed by default). The fallback must
    # return None and NEVER raise, so polite_fetch keeps its non-browser result.
    assert browser_fetch("https://example.com") is None
