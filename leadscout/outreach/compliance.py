"""Compliance layer (SPEC §4.6 / §13) — retained V1, applies to ALL outreach volumes.

Per-region legal basis + the hard requirements baked into every draft, a
suppression-list check run before every send, and mandatory contact-source
provenance. At <=10 sends/day this is cheap discipline; it also future-proofs B9.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import select

from ..config import get_settings
from ..db import session_scope
from ..models import OptOut


class Region(StrEnum):
    US = "us_optout"          # CAN-SPAM (opt-out)
    UK = "uk_lia"             # PECR corporate-subscriber + documented LIA
    EU_LIA = "eu_lia"         # GDPR legitimate interest (LI-friendly states)
    CONSENT_ONLY = "consent_only"  # DE, AT seed — do NOT cold-email
    CA = "ca_cpub"            # CASL conspicuous-publication exception
    APAC = "apac_cpub"        # AU/NZ/SG conspicuous-publication


# country (ISO-ish, lowercase) -> Region
_COUNTRY_REGION: dict[str, Region] = {
    "us": Region.US, "usa": Region.US, "united states": Region.US,
    "uk": Region.UK, "gb": Region.UK, "united kingdom": Region.UK,
    "ie": Region.EU_LIA, "ireland": Region.EU_LIA,
    "de": Region.CONSENT_ONLY, "germany": Region.CONSENT_ONLY,
    "at": Region.CONSENT_ONLY, "austria": Region.CONSENT_ONLY,
    "ca": Region.CA, "canada": Region.CA,
    "au": Region.APAC, "australia": Region.APAC,
    "nz": Region.APAC, "new zealand": Region.APAC,
    "sg": Region.APAC, "singapore": Region.APAC,
}


@dataclass
class RegionRule:
    region: Region
    basis: str
    may_cold_email: bool
    requirements: list[str]


REGION_RULES: dict[Region, RegionRule] = {
    Region.US: RegionRule(Region.US, "CAN-SPAM (opt-out)", True, [
        "Accurate From/subject", "Physical postal address in footer",
        "Working opt-out; honor within 10 days",
    ]),
    Region.UK: RegionRule(Region.UK, "PECR corporate-subscriber + documented LIA", True, [
        "Documented LIA in compliance/LIA.md", "Opt-out in every mail",
        "Sole traders treated as consent-required",
    ]),
    Region.EU_LIA: RegionRule(Region.EU_LIA, "GDPR legitimate interest (LI-friendly)", True, [
        "Documented LIA", "Strictly role-relevant message", "Instant opt-out honoring",
    ]),
    Region.CONSENT_ONLY: RegionRule(Region.CONSENT_ONLY, "Consent required", False, [
        "Do NOT cold-email — excluded by default unless consent exists",
    ]),
    Region.CA: RegionRule(Region.CA, "CASL conspicuous-publication exception", True, [
        "Business email published without a no-contact statement",
        "Message relates to their role", "Record the basis on the contact",
    ]),
    Region.APAC: RegionRule(Region.APAC, "Conspicuous-publication basis (AU/NZ/SG)", True, [
        "Same conspicuous-publication discipline as Canada", "Record the basis per contact",
    ]),
}


def region_for_country(country: str | None) -> Region:
    if not country:
        return Region.US  # safest default (opt-out) with full footer; verify before send
    return _COUNTRY_REGION.get(country.strip().lower(), Region.EU_LIA)


def compliance_footer(region: Region) -> str:
    """The footer baked into every draft for a region."""
    s = get_settings()
    identity = f"{s.operator_name} · {s.operator_email}"
    optout = "Reply STOP or 'unsubscribe' and I won't contact you again."
    if region in (Region.US, Region.UK, Region.EU_LIA):
        addr = s.postal_address or "[POSTAL ADDRESS REQUIRED — set POSTAL_ADDRESS in .env]"
        return f"{identity}\n{addr}\n{optout}"
    return f"{identity}\n{optout}"


def is_suppressed(email: str | None = None, domain: str | None = None) -> bool:
    """Suppression check — run before every send (SPEC §13, global rule)."""
    with session_scope() as sess:
        rows = list(sess.execute(select(OptOut)).scalars())
    for o in rows:
        if email and o.email and o.email.lower() == email.lower():
            return True
        if domain and o.domain and o.domain.lower() == domain.lower():
            return True
    return False


def may_contact(region: Region, email: str | None = None, domain: str | None = None) -> tuple[bool, str]:
    """Combined gate: region allows cold contact AND not suppressed."""
    rule = REGION_RULES[region]
    if not rule.may_cold_email:
        return False, f"region {region.value} is consent-only"
    if is_suppressed(email, domain):
        return False, "on suppression list"
    return True, "ok"
