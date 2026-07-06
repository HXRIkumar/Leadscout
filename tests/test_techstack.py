"""Tech-stack / support-widget detection from raw HTML (compliant, verified)."""

from leadscout.research.extract import verify_signals
from leadscout.research.fetch import FetchResult
from leadscout.research.techstack import detect_widgets


def _fr(url: str, html: str) -> FetchResult:
    return FetchResult(url=url, status=200, html=html, clean_text="text")


def test_detect_intercom_verbatim():
    r = _fr("https://x.com/", '<script src="https://widget.intercom.io/widget/abc"></script>')
    sigs = detect_widgets([r])
    assert len(sigs) == 1
    assert sigs[0].signal_type == "support_widget"
    assert sigs[0].meta["vendor"] == "Intercom"
    assert sigs[0].evidence_quote in r.html          # verbatim
    assert verify_signals(sigs, {r.url: r.html})     # passes the fail-closed verifier


def test_detect_dedupes_across_pages():
    html = 'x <script src="https://static.zdassets.com/ekr/snippet.js"></script> y'
    sigs = detect_widgets([_fr("https://x.com/", html), _fr("https://x.com/help", html)])
    assert [s.meta["vendor"] for s in sigs] == ["Zendesk"]  # one vendor, not two


def test_no_false_positive():
    assert detect_widgets([_fr("https://x.com/", "<html><body>no widgets here</body></html>")]) == []
