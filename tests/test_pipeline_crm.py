"""A10 Pipeline CRM-lite functional operations."""

from datetime import date, timedelta

from leadscout.pipeline.crm import (
    add_business_days,
    advance,
    follow_ups_due,
    funnel_counts,
    promote_to_lead,
    record_send,
)
from leadscout.pipeline.digest import build_digest


def test_add_business_days_skips_weekends():
    # 2026-07-04 is a Saturday; +1 business day -> Monday 2026-07-06
    assert add_business_days(date(2026, 7, 3), 1) == date(2026, 7, 6)
    r = add_business_days(date(2026, 7, 6), 4)
    assert r.weekday() < 5
    assert (r - date(2026, 7, 6)).days >= 4


def test_promote_is_idempotent():
    a = promote_to_lead("acme.com")
    b = promote_to_lead("acme.com")
    assert a == b


def test_advance_and_followup_date_set_on_contacted():
    lid = promote_to_lead("beta.com")
    new = advance(lid, "contacted", note="sent intro")
    assert new == "contacted"
    # a follow-up should now be due within a week
    due = follow_ups_due(as_of=date.today() + timedelta(days=7))
    assert any(v.id == lid for v in due)
    # but not due today (4 business days out)
    assert not any(v.id == lid for v in follow_ups_due(as_of=date.today()))


def test_record_send_sets_contacted():
    lid = promote_to_lead("gamma.com")
    record_send(lid, channel="email", draft_text="hi")
    due = follow_ups_due(as_of=date.today() + timedelta(days=10))
    assert any(v.id == lid and v.status == "contacted" for v in due)


def test_funnel_counts_and_digest():
    promote_to_lead("delta.com")
    counts = funnel_counts()
    assert counts.get("shortlisted", 0) >= 1
    md = build_digest()
    assert "Pipeline digest" in md
    assert "Funnel" in md
