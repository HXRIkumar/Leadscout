"""Compliance layer (SPEC §4.6/§13)."""

from leadscout.db import init_db, session_scope
from leadscout.models import OptOut
from leadscout.outreach.compliance import (
    Region,
    compliance_footer,
    is_suppressed,
    may_contact,
    region_for_country,
)


def test_region_mapping():
    assert region_for_country("US") == Region.US
    assert region_for_country("Germany") == Region.CONSENT_ONLY
    assert region_for_country("canada") == Region.CA
    assert region_for_country(None) == Region.US  # safe default


def test_consent_only_blocks_cold_email():
    ok, reason = may_contact(Region.CONSENT_ONLY, email="x@de.example")
    assert not ok
    assert "consent-only" in reason


def test_us_footer_has_postal_address():
    footer = compliance_footer(Region.US)
    assert "1 Test St" in footer  # from conftest POSTAL_ADDRESS
    assert "unsubscribe" in footer.lower() or "STOP" in footer


def test_suppression_check():
    init_db()
    with session_scope() as s:
        s.add(OptOut(email="no@x.com", domain="x.com", permanent=True))
    assert is_suppressed(email="no@x.com")
    assert is_suppressed(domain="x.com")
    assert not is_suppressed(email="yes@ok.com")
    ok, reason = may_contact(Region.US, domain="x.com")
    assert not ok and "suppression" in reason
