"""Polite crawling (SPEC §4.1 / §7.4): one central `polite_fetch()`.

- robots.txt honored as binding (cached per domain)
- >= 2 s between requests to the same domain
- honest User-Agent, bounded timeout
- on-disk fetch cache (never fetch the same page twice)
- clean main text via trafilatura

No headless browser here — JS-only pages are marked and skipped; the Playwright
fallback is reserved (B7, leadscout/research/browser.py stub).
"""

from __future__ import annotations

import re
import time
import urllib.robotparser
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
import trafilatura
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ..config import get_settings
from ..logging import get_logger

log = get_logger(__name__)

# Candidate paths probed per company (SPEC §7.4). First match of each kind.
CANDIDATE_PATHS = [
    "",  # homepage
    "/careers", "/jobs", "/careers/", "/company/careers",
    "/pricing",
    "/help", "/docs", "/support", "/faq", "/help-center", "/knowledge-base",
    "/blog", "/changelog",
    "/about",
]

_last_fetch_at: dict[str, float] = {}
_robots_cache: dict[str, urllib.robotparser.RobotFileParser | None] = {}


@dataclass
class FetchResult:
    url: str
    status: int
    html: str
    clean_text: str
    blocked_by_robots: bool = False
    from_cache: bool = False
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.status == 200 and not self.blocked_by_robots and bool(self.clean_text)


def normalize_domain(url_or_domain: str) -> str:
    """Canonical domain: strip scheme, www, path, port, lowercase."""
    v = url_or_domain.strip().lower()
    if "://" not in v:
        v = "https://" + v
    netloc = urlparse(v).netloc
    netloc = netloc.split("@")[-1].split(":")[0]
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


def canonical_url(domain: str) -> str:
    return f"https://{normalize_domain(domain)}"


def _slug(url: str) -> str:
    p = urlparse(url)
    path = (p.path or "/").rstrip("/") or "home"
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", f"{path}_{p.query}").strip("_")
    return slug[:80] or "home"


def page_paths(url: str) -> tuple[Path, Path]:
    """Return (raw_html_path, clean_text_path) used by the on-disk fetch cache."""
    s = get_settings()
    domain = normalize_domain(url)
    raw_dir = s.data_path / "companies" / domain / "raw"
    slug = _slug(url)
    return raw_dir / f"{slug}.html", raw_dir / f"{slug}.txt"


def _robots(domain: str) -> urllib.robotparser.RobotFileParser | None:
    if domain in _robots_cache:
        return _robots_cache[domain]
    rp = urllib.robotparser.RobotFileParser()
    url = f"https://{domain}/robots.txt"
    try:
        resp = httpx.get(url, headers={"User-Agent": get_settings().user_agent}, timeout=8.0, follow_redirects=True)
        if resp.status_code == 200:
            rp.parse(resp.text.splitlines())
        else:
            rp = None  # no robots -> allow
    except httpx.HTTPError:
        rp = None  # fetch failed -> be lenient but log
        log.info("robots.txt unreachable for %s (allowing)", domain)
    _robots_cache[domain] = rp
    return rp


def robots_allowed(url: str) -> bool:
    domain = normalize_domain(url)
    rp = _robots(domain)
    if rp is None:
        return True
    return rp.can_fetch(get_settings().user_agent, url)


def _respect_rate_limit(domain: str) -> None:
    s = get_settings()
    last = _last_fetch_at.get(domain)
    if last is not None:
        elapsed = time.monotonic() - last
        wait = s.crawl_min_interval_seconds - elapsed
        if wait > 0:
            time.sleep(wait)
    _last_fetch_at[domain] = time.monotonic()


@retry(
    retry=retry_if_exception_type(httpx.TransportError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
def _raw_get(url: str, timeout: float, user_agent: str) -> httpx.Response:
    return httpx.get(url, headers={"User-Agent": user_agent}, timeout=timeout, follow_redirects=True)


def polite_fetch(url: str, *, use_cache: bool = True) -> FetchResult:
    """Fetch one URL politely. Central choke point for ALL crawling."""
    s = get_settings()
    domain = normalize_domain(url)
    raw_dir = s.data_path / "companies" / domain / "raw"
    slug = _slug(url)
    raw_path = raw_dir / f"{slug}.html"
    txt_path = raw_dir / f"{slug}.txt"

    if use_cache and raw_path.exists() and txt_path.exists():
        return FetchResult(
            url=url, status=200,
            html=raw_path.read_text(encoding="utf-8", errors="ignore"),
            clean_text=txt_path.read_text(encoding="utf-8", errors="ignore"),
            from_cache=True,
        )

    if not robots_allowed(url):
        log.info("robots.txt disallows %s", url)
        return FetchResult(url=url, status=0, html="", clean_text="", blocked_by_robots=True)

    _respect_rate_limit(domain)
    try:
        resp = _raw_get(url, s.crawl_timeout_seconds, s.user_agent)
    except httpx.HTTPError as e:
        return FetchResult(url=url, status=0, html="", clean_text="", error=str(e))

    if resp.status_code != 200:
        return FetchResult(url=url, status=resp.status_code, html="", clean_text="")

    html = resp.text
    clean = trafilatura.extract(html, include_comments=False, include_tables=True) or ""

    # B7: single browser fallback for thin/JS-only pages (robots already honored above).
    if len(clean) < 200 and s.use_browser_fallback:
        from .browser import browser_fetch
        rendered = browser_fetch(url)
        if rendered:
            alt = trafilatura.extract(rendered, include_comments=False, include_tables=True) or ""
            if len(alt) > len(clean):
                html, clean = rendered, alt

    if len(clean) < 100:
        # still thin (JS-only, no browser): keep a raw tag-stripped fallback
        clean = re.sub(r"<[^>]+>", " ", html)
        clean = re.sub(r"\s+", " ", clean).strip()

    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(html, encoding="utf-8")
    txt_path.write_text(clean, encoding="utf-8")
    return FetchResult(url=url, status=200, html=html, clean_text=clean)


def _discover_links(html: str, base_url: str) -> list[str]:
    """Find on-domain links matching high-value paths, for one level of follow."""
    domain = normalize_domain(base_url)
    found: list[str] = []
    for m in re.finditer(r'href=["\']([^"\']+)["\']', html, flags=re.IGNORECASE):
        href = m.group(1)
        full = urljoin(base_url, href)
        if normalize_domain(full) != domain:
            continue
        path = urlparse(full).path.lower()
        if any(k in path for k in ("help", "docs", "support", "faq", "career", "job", "pricing", "changelog", "community")):
            found.append(full.split("#")[0])
    # dedupe, keep order
    seen: set[str] = set()
    uniq = []
    for u in found:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq


def crawl_company(domain: str, *, max_pages: int | None = None, use_cache: bool = True) -> list[FetchResult]:
    """Fetch the candidate page set for a company, politely (SPEC §7.4).

    Returns successful FetchResults (blocked/failed pages are logged, not returned).
    """
    s = get_settings()
    domain = normalize_domain(domain)
    cap = max_pages or s.crawl_max_pages_per_company
    base = canonical_url(domain)

    results: list[FetchResult] = []
    tried: set[str] = set()

    # 1) homepage first (also used for link discovery)
    home = polite_fetch(base, use_cache=use_cache)
    tried.add(base)
    if home.ok:
        results.append(home)

    # 2) candidate paths
    candidates = [urljoin(base + "/", p.lstrip("/")) for p in CANDIDATE_PATHS if p]
    # 3) plus one level of obvious links discovered on the homepage
    if home.html:
        candidates += _discover_links(home.html, base)

    for url in candidates:
        if len(results) >= cap:
            break
        url = url.rstrip("/")
        if url in tried or url == base:
            continue
        tried.add(url)
        r = polite_fetch(url, use_cache=use_cache)
        if r.ok:
            results.append(r)
    return results
