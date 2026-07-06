"""A10 daily digest (CLI + markdown, SPEC §11).

Follow-ups-due view + funnel counts. Web dashboard is B1 (reserved). No vanity
metrics — plain counts the operator can act on in five minutes.
"""

from __future__ import annotations

from datetime import date

from .crm import follow_ups_due, funnel_counts

_FUNNEL_ORDER = ["new", "shortlisted", "contacted", "replied", "call_booked", "won", "lost", "skipped", "disqualified"]


def build_digest(as_of: date | None = None) -> str:
    today = as_of or date.today()
    due = follow_ups_due(today)
    counts = funnel_counts()

    lines = [f"# Pipeline digest — {today.isoformat()}", ""]
    lines.append(f"## Follow-ups due ({len(due)})")
    lines.append("")
    if due:
        for lv in due:
            lines.append(f"- **#{lv.id}** `{lv.domain}` — {lv.status} — due {lv.next_action_date}")
    else:
        lines.append("_None due._")
    lines.append("")

    lines.append("## Funnel")
    lines.append("")
    if counts:
        for status in _FUNNEL_ORDER:
            if status in counts:
                lines.append(f"- {status}: {counts[status]}")
        for status, n in counts.items():
            if status not in _FUNNEL_ORDER:
                lines.append(f"- {status}: {n}")
    else:
        lines.append("_No leads yet. Promote one: `leadscout promote <domain>`._")
    lines.append("")
    return "\n".join(lines)
