"""Opportunity ranking (activated B5): order briefed companies by explainable score.

At the operator's direction (lead-gen goal) the reserved scorer is wired for
triage. Ranking reads the latest persisted Score per company (written by each
`brief` run) joined with the latest brief's readiness. Deterministic + explainable.
"""

from __future__ import annotations

from dataclasses import dataclass

from .db import init_db, session_scope
from .models import Brief, Company, Score


@dataclass
class RankRow:
    domain: str
    name: str
    score: int
    value_band: str
    readiness: str
    disqualified: bool


def ranked_opportunities(include_disqualified: bool = False) -> list[RankRow]:
    init_db()
    with session_scope() as s:
        companies = {c.domain: c for c in s.query(Company).all()}
        scores: dict[str, Score] = {}
        for sc in s.query(Score).order_by(Score.scored_at).all():
            scores[sc.domain] = sc  # latest per domain wins
        briefs: dict[str, Brief] = {}
        for b in s.query(Brief).order_by(Brief.id).all():
            briefs[b.domain] = b

        rows: list[RankRow] = []
        for domain, sc in scores.items():
            c = companies.get(domain)
            disq = bool(c and c.disqualified_reason)
            if disq and not include_disqualified:
                continue
            b = briefs.get(domain)
            rows.append(RankRow(
                domain=domain,
                name=(c.name if c else domain) or domain,
                score=sc.total,
                value_band=sc.estimated_value_band or "",
                readiness=(b.readiness_qualitative if b else "") or "",
                disqualified=disq,
            ))
    rows.sort(key=lambda r: r.score, reverse=True)
    return rows
