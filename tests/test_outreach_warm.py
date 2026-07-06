"""A7 outreach drafting + A8 warm network — offline."""

from datetime import date, timedelta

import pytest

from leadscout.db import init_db, session_scope
from leadscout.distribution.warm import add_contact, import_csv, log_touch, reactivation_due
from leadscout.models import Brief, Company, Signal
from leadscout.outreach.compliance import Region
from leadscout.outreach.draft import NoBriefError, draft_message


def _seed_brief(domain="acme.com"):
    init_db()
    with session_scope() as s:
        s.add(Company(domain=domain, name="Acme"))
        s.add(Brief(domain=domain, bottleneck="Support load is rising: help center gaps.",
                    wedge="A RAG bot on your docs.", cost_estimate="≈ $57,750/yr in deflectable support load",
                    readiness_qualitative="high"))
        s.add(Signal(domain=domain, signal_type="help_center",
                     evidence_quote="Browse articles in our knowledge base.",
                     source_url=f"https://{domain}/help", confidence=0.8, mapped_project="rag_support_bot"))


# --- A7 ---

def test_draft_anchors_on_verified_fact_and_has_footer():
    _seed_brief()
    res = draft_message("acme.com", region=Region.US, contact_name="Sam", use_llm=False)
    assert "knowledge base" in res.cold_message          # anchored on the verified quote
    assert "1 Test St" in res.cold_message                # US footer has postal address (conftest)
    assert "Sam" in res.cold_message
    assert res.sendable
    assert res.warm_intro


def test_draft_blocked_in_consent_only_region():
    _seed_brief("beta.com")
    res = draft_message("beta.com", region=Region.CONSENT_ONLY, use_llm=False)
    assert not res.sendable
    assert "consent-only" in res.block_reason


def test_draft_without_brief_raises():
    init_db()
    with pytest.raises(NoBriefError):
        draft_message("nobrief.com", use_llm=False)


# --- A8 ---

def test_warm_add_and_due():
    cid = add_contact("Alex Doe", company="Acme", source="ex-colleague", warmth="hot")
    due = reactivation_due()
    assert any(c.id == cid for c in due)  # never touched -> due


def test_warm_log_touch_resets_clock():
    cid = add_contact("Jo Roe", warmth="warm")
    log_touch(cid, kind="email", notes="said hi", cadence_days=30)
    assert not any(c.id == cid for c in reactivation_due(as_of=date.today()))
    assert any(c.id == cid for c in reactivation_due(as_of=date.today() + timedelta(days=31)))


def test_warm_import_csv(tmp_path):
    p = tmp_path / "contacts.csv"
    p.write_text("name,company,source,warmth,channel\n"
                 "Pat Lee,Globex,conference,warm,linkedin\n"
                 "Kim Ng,Initech,,cold,\n", encoding="utf-8")
    n = import_csv(str(p))
    assert n == 2
    assert len(reactivation_due()) >= 2
