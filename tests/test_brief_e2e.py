"""W1 milestone acceptance (SPEC §5.2): `brief <url>` produces an evidence-verified
diagnosis with a cost number, every claim carrying a verbatim quote + source URL,
failing closed. Fully offline via respx (no live network, no LLM keys).
"""


import respx
from httpx import Response

from leadscout.db import session_scope
from leadscout.models import Brief, Company, Signal
from leadscout.research.brief import build_brief

HOME = """<html><body>
<h1>Acme Billing</h1>
<p>Acme is the fastest growing billing platform for SaaS companies. Thousands of customers trust us every day.</p>
<a href="/careers">Careers</a> <a href="/help">Help center</a>
</body></html>"""

CAREERS = """<html><body>
<h2>Open roles</h2>
<p>We are hiring a Customer Support Specialist and 3 support engineers to join our growing support team.</p>
</body></html>"""

HELP = """<html><body>
<h2>Help center</h2>
<p>Browse articles in our knowledge base. Find answers to the most common questions our customers ask.</p>
</body></html>"""


@respx.mock
def test_brief_end_to_end():
    # NOTE: respx treats an empty-path URL as a wildcard, so anchor the homepage
    # route with a regex and register specific paths before the catch-all.
    respx.get("https://acme.test/robots.txt").mock(return_value=Response(200, text="User-agent: *\nAllow: /"))
    respx.get("https://acme.test/careers").mock(return_value=Response(200, html=CAREERS))
    respx.get("https://acme.test/help").mock(return_value=Response(200, html=HELP))
    respx.get(url__regex=r"^https://acme\.test/?$").mock(return_value=Response(200, html=HOME))
    respx.route().mock(return_value=Response(404))  # catch-all for other probed paths

    res = build_brief("acme.test", use_cache=False, use_llm=False)

    # 1) evidence-verified signals, all traceable to fetched text
    assert res.signals, "expected at least one verified signal"
    for s in res.signals:
        assert s.evidence_quote  # every claim carries a quote
        assert s.source_url.startswith("https://acme.test")

    types = {s.signal_type for s in res.signals}
    assert "support_hiring" in types
    assert "help_center" in types

    # 2) cost number present and defensible
    assert res.cost.value_usd_per_year > 0
    assert "$" in res.cost.headline

    # 3) diagnosis produced
    assert res.diagnosis.bottleneck
    assert not res.diagnosis.disqualified
    assert res.diagnosis.readiness_qualitative in {"high", "medium", "low"}

    # 4) brief markdown written, contains cost + evidence
    md = open(res.brief_path).read()
    assert "Cost of the problem" in md
    assert "≈ $" in md
    assert "verbatim-verified" in md

    # 5) persisted to DB
    with session_scope() as sess:
        assert sess.get(Company, "acme.test") is not None
        assert sess.query(Signal).filter(Signal.domain == "acme.test").count() == len(res.signals)
        assert sess.query(Brief).filter(Brief.domain == "acme.test").count() == 1


@respx.mock
def test_brief_fails_closed_on_unreachable_site():
    respx.get("https://ghost.test/robots.txt").mock(return_value=Response(404))
    respx.route().mock(return_value=Response(500))
    res = build_brief("ghost.test", use_cache=False, use_llm=False)
    # no pages -> no signals, but still produces a (thin) brief, never fabricated claims
    assert res.signals == []
    md = open(res.brief_path).read()
    assert "No positive support-deflection signals passed verification." in md
