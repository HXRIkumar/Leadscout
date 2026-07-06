"""A10 — Pipeline CRM-lite (SPEC §11/§13).

Lifecycle state machine + follow-up rule (retained V1) AND the functional CRM
operations: promote a researched company to a lead, advance its status, record a
send (setting the follow-up date), and surface follow-ups due. Deals die in
follow-up; this is also where conversations become data (substrate for C1-C4).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select

from ..db import init_db, session_scope
from ..models import Lead, Outreach

# Follow-up rule (SPEC §12/§13): +4 business days, max 2 follow-ups.
FOLLOW_UP_BUSINESS_DAYS = 4
MAX_FOLLOW_UPS = 2

# Lead lifecycle (SPEC §11 state diagram): state -> allowed next states.
LIFECYCLE_TRANSITIONS: dict[str, set[str]] = {
    "new": {"shortlisted", "skipped", "disqualified"},
    "shortlisted": {"contacted", "disqualified"},
    "contacted": {"replied", "followup_due"},
    "followup_due": {"contacted", "lost"},
    "replied": {"call_booked", "lost"},
    "call_booked": {"won", "lost"},
    "won": set(),
    "lost": set(),
    "skipped": set(),
    "disqualified": set(),
}

_OPEN_FOLLOWUP_STATES = {"contacted", "followup_due"}


def next_status(current: str, target: str) -> str:
    """Validate a lifecycle transition; raise on an illegal move."""
    allowed = LIFECYCLE_TRANSITIONS.get(current)
    if allowed is None:
        raise ValueError(f"unknown status: {current!r}")
    if target not in allowed:
        raise ValueError(f"illegal transition {current!r} -> {target!r} (allowed: {sorted(allowed)})")
    return target


def add_business_days(start: date, n: int) -> date:
    """Add n business days (skip Sat/Sun)."""
    d = start
    added = 0
    while added < n:
        d += timedelta(days=1)
        if d.weekday() < 5:  # Mon-Fri
            added += 1
    return d


# --- Functional operations ---------------------------------------------------


@dataclass
class LeadView:
    id: int
    domain: str
    status: str
    next_action_date: date | None
    notes: str | None


def promote_to_lead(
    domain: str,
    *,
    contact_name: str | None = None,
    contact_email: str | None = None,
    contact_source: str | None = None,
    region_rule: str | None = None,
) -> int:
    """Promote a researched company to a lead (status 'shortlisted'). Idempotent by domain."""
    init_db()
    with session_scope() as s:
        existing = s.execute(select(Lead).where(Lead.domain == domain)).scalars().first()
        if existing is not None:
            return existing.id
        lead = Lead(
            domain=domain, status="shortlisted", contact_name=contact_name,
            contact_email=contact_email, contact_source=contact_source, region_rule=region_rule,
        )
        s.add(lead)
        s.flush()
        return lead.id


def advance(lead_id: int, target: str, note: str | None = None) -> str:
    """Transition a lead's status (validated). Sets follow-up date on 'contacted'."""
    init_db()
    with session_scope() as s:
        lead = s.get(Lead, lead_id)
        if lead is None:
            raise ValueError(f"no lead with id {lead_id}")
        new = next_status(lead.status, target)
        lead.status = new
        if note:
            lead.notes = (lead.notes + "\n" if lead.notes else "") + note
        if new == "contacted":
            lead.next_action_date = add_business_days(date.today(), FOLLOW_UP_BUSINESS_DAYS)
        return new


def record_send(lead_id: int, channel: str = "email", draft_text: str | None = None) -> None:
    """Log an outreach send and move the lead to 'contacted' with a follow-up date."""
    init_db()
    with session_scope() as s:
        lead = s.get(Lead, lead_id)
        if lead is None:
            raise ValueError(f"no lead with id {lead_id}")
        s.add(Outreach(lead_id=lead_id, channel=channel, draft_text=draft_text, sent_at=datetime.now(UTC)))
        if lead.status in ("shortlisted", "followup_due"):
            lead.status = "contacted"
        lead.next_action_date = add_business_days(date.today(), FOLLOW_UP_BUSINESS_DAYS)


def follow_ups_due(as_of: date | None = None) -> list[LeadView]:
    """Leads whose next_action_date <= as_of and still in an open follow-up state."""
    init_db()
    today = as_of or date.today()
    with session_scope() as s:
        rows = s.execute(select(Lead)).scalars().all()
        return [
            LeadView(r.id, r.domain, r.status, r.next_action_date, r.notes)
            for r in rows
            if r.status in _OPEN_FOLLOWUP_STATES and r.next_action_date is not None and r.next_action_date <= today
        ]


def funnel_counts() -> dict[str, int]:
    """Plain counts by status (SPEC §11 funnel view — no vanity metrics)."""
    init_db()
    counts: dict[str, int] = {}
    with session_scope() as s:
        for r in s.execute(select(Lead)).scalars().all():
            counts[r.status] = counts.get(r.status, 0) + 1
    return counts
