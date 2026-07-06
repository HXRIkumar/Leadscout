"""A8 — Warm Network Manager (thin, SPEC §3.1 A8).

Import everyone who knows you; track warmth, last touch, reactivation cadence;
surface who's due for a personal (never automated) reactivation or intro ask.
Highest-converting channel in every dataset reviewed (§2.4). Relationship-graph
seed for C4. Populating it needs the operator's own network (docs/DECISIONS_NEEDED D4).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select

from ..config import get_settings
from ..db import init_db, session_scope
from ..logging import get_logger
from ..models import Contact, Interaction

log = get_logger(__name__)

DEFAULT_CADENCE_DAYS = 30


@dataclass
class ContactView:
    id: int
    name: str
    company: str | None
    warmth: str | None
    last_touch: date | None
    next_touch: date | None


def add_contact(name: str, *, company: str | None = None, source: str | None = None,
                warmth: str = "warm", channel: str | None = None) -> int:
    init_db()
    with session_scope() as s:
        c = Contact(name=name, company=company, source=source, warmth=warmth, channel=channel)
        s.add(c)
        s.flush()
        return c.id


def import_csv(path: str) -> int:
    """Import contacts from CSV (columns: name, company, source, warmth, channel)."""
    init_db()
    n = 0
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        with session_scope() as s:
            for row in reader:
                name = (row.get("name") or "").strip()
                if not name:
                    continue
                s.add(Contact(
                    name=name, company=(row.get("company") or "").strip() or None,
                    source=(row.get("source") or "").strip() or None,
                    warmth=(row.get("warmth") or "warm").strip() or "warm",
                    channel=(row.get("channel") or "").strip() or None,
                ))
                n += 1
    log.info("imported %d contacts from %s", n, path)
    return n


def log_touch(contact_id: int, kind: str = "note", notes: str | None = None,
              cadence_days: int = DEFAULT_CADENCE_DAYS) -> None:
    """Record an interaction and reset the reactivation clock."""
    init_db()
    now = datetime.now(UTC)
    notes_path = None
    if notes:
        d = get_settings().data_path / "interactions"
        d.mkdir(parents=True, exist_ok=True)
        notes_path = str(d / f"contact{contact_id}_{now.strftime('%Y%m%dT%H%M%SZ')}.md")
        with open(notes_path, "w", encoding="utf-8") as f:
            f.write(notes)
    with session_scope() as s:
        c = s.get(Contact, contact_id)
        if c is None:
            raise ValueError(f"no contact with id {contact_id}")
        s.add(Interaction(contact_id=contact_id, kind=kind, notes_path=notes_path, at=now))
        c.last_touch = now.date()
        c.next_touch = now.date() + timedelta(days=cadence_days)


def reactivation_due(as_of: date | None = None) -> list[ContactView]:
    """Contacts never touched, or whose next_touch has arrived."""
    init_db()
    today = as_of or date.today()
    with session_scope() as s:
        rows = s.execute(select(Contact)).scalars().all()
        due = [
            ContactView(r.id, r.name, r.company, r.warmth, r.last_touch, r.next_touch)
            for r in rows
            if r.last_touch is None or (r.next_touch is not None and r.next_touch <= today)
        ]
    # warmest first (hot > warm > cold), then never-touched
    order = {"hot": 0, "warm": 1, "cold": 2}
    due.sort(key=lambda v: (order.get((v.warmth or "warm"), 1), v.last_touch is not None))
    return due
