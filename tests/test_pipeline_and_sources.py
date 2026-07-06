"""Lifecycle state machine (retained V1) + Discovery Lite prefilter + scorer seed."""

import pytest

from leadscout.pipeline import FOLLOW_UP_BUSINESS_DAYS, MAX_FOLLOW_UPS, next_status
from leadscout.sources.base import Candidate
from leadscout.sources.discovery import prefilter


def test_follow_up_rule_constants():
    assert FOLLOW_UP_BUSINESS_DAYS == 4
    assert MAX_FOLLOW_UPS == 2


def test_lifecycle_valid_transition():
    assert next_status("new", "shortlisted") == "shortlisted"
    assert next_status("contacted", "replied") == "replied"


def test_lifecycle_illegal_transition():
    with pytest.raises(ValueError):
        next_status("new", "won")
    with pytest.raises(ValueError):
        next_status("won", "new")


def test_prefilter_drops_agency_and_ai_native():
    ok = prefilter(Candidate("Good Co", "good.com", "hn", "billing platform for SaaS"), set())
    assert ok.ok

    agency = prefilter(Candidate("Studio", "studio.com", "hn", "we are a software development agency"), set())
    assert not agency.ok and agency.reason == "disqualifier_agency"

    ai = prefilter(Candidate("Botly", "botly.com", "yc", "an AI-powered LLM copilot"), set())
    assert not ai.ok and ai.reason == "disqualifier_ai_native"


def test_prefilter_drops_opt_out_and_bad_domain():
    assert not prefilter(Candidate("X", "x.com", "hn"), {"x.com"}).ok
    assert not prefilter(Candidate("Y", "not a domain", "hn"), set()).ok


def test_scorer_seed_runs():
    from leadscout.intelligence.scorer import FixedWeightScorer
    from leadscout.research.extract import SignalCandidate
    sigs = [SignalCandidate("support_hiring", "hiring support", "u", 0.8),
            SignalCandidate("help_center", "help center", "u", 0.7)]
    res = FixedWeightScorer().score(sigs, {})
    assert 0 <= res.total <= 100
    assert res.factor_breakdown
