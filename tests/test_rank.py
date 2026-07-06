"""Opportunity scoring + ranking (activated B5)."""

from leadscout.db import init_db, session_scope
from leadscout.intelligence.scorer import opportunity_score
from leadscout.models import Company, Score
from leadscout.rank import ranked_opportunities
from leadscout.research.extract import SignalCandidate


def test_opportunity_score_disqualified_is_zero():
    r = opportunity_score([], "rag_support_bot", disqualified=True)
    assert r.total == 0
    assert "disqualified" in r.estimated_value_band


def test_opportunity_score_positive_with_band_and_factors():
    sigs = [
        SignalCandidate("help_center", "hc", "u", 0.9, mapped_project="rag_support_bot"),
        SignalCandidate("support_hiring", "sh", "u", 0.8, mapped_project="rag_support_bot"),
    ]
    r = opportunity_score(sigs, "rag_support_bot")
    assert 0 < r.total <= 100
    assert "$" in r.estimated_value_band          # §14 value band
    assert r.factor_breakdown                      # explainable


def test_ranking_orders_desc_and_hides_disqualified():
    init_db()
    with session_scope() as s:
        s.add(Company(domain="a.com", name="A"))
        s.add(Company(domain="b.com", name="B"))
        s.add(Company(domain="c.com", name="C", disqualified_reason="agency"))
        s.add(Score(domain="a.com", total=40, estimated_value_band="$5k"))
        s.add(Score(domain="b.com", total=80, estimated_value_band="$5k"))
        s.add(Score(domain="c.com", total=0, estimated_value_band="n/a"))

    assert [r.domain for r in ranked_opportunities()] == ["b.com", "a.com"]
    assert "c.com" in [r.domain for r in ranked_opportunities(include_disqualified=True)]
