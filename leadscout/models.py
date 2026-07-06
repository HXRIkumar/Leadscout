"""SQLAlchemy 2.x data model (SPEC §4.3).

Retained V1 tables (companies, artifacts, signals, scores, leads, outreach,
opt_outs, llm_cache) + V2 extensions (briefs, demos, contacts, interactions,
engagements, outcomes, patterns) + reserved-seam tables created empty from day 1
(scores/B5, proposals/B2, outcomes) so Category B/C modules are architecturally
present at near-zero cost (§4.4).

Design rules:
- `companies.domain` is the canonical join key across the V1 spine.
- Reserved tables carry a docstring naming their trigger; nothing reads them yet.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


# =============================================================================
# V1 spine — retained unchanged (SPEC §6: "keep unchanged")
# =============================================================================


class Company(Base):
    __tablename__ = "companies"

    domain: Mapped[str] = mapped_column(String, primary_key=True)  # canonical join key
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    country: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    employee_estimate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stage: Mapped[str | None] = mapped_column(String, nullable=True)  # seed, series-a, unknown
    sources_seen: Mapped[str | None] = mapped_column(String, nullable=True)  # csv of source tags
    disqualified_reason: Mapped[str | None] = mapped_column(String, nullable=True)  # null if alive
    first_seen: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    last_crawled: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    artifacts: Mapped[list[Artifact]] = relationship(back_populates="company")
    signals: Mapped[list[Signal]] = relationship(back_populates="company")
    briefs: Mapped[list[Brief]] = relationship(back_populates="company")


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    domain: Mapped[str] = mapped_column(ForeignKey("companies.domain"), index=True)
    source: Mapped[str] = mapped_column(String)  # hn, yc, edgar, site, careers, github
    url: Mapped[str] = mapped_column(String)
    raw_path: Mapped[str | None] = mapped_column(String, nullable=True)
    clean_text_path: Mapped[str | None] = mapped_column(String, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    company: Mapped[Company] = relationship(back_populates="artifacts")


class Signal(Base):
    """Extracted research evidence. Every row is verbatim-verified (SPEC §4.1)."""

    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    domain: Mapped[str] = mapped_column(ForeignKey("companies.domain"), index=True)
    signal_type: Mapped[str] = mapped_column(String)
    evidence_quote: Mapped[str] = mapped_column(Text)  # verbatim, validated
    source_url: Mapped[str] = mapped_column(String)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    recency_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mapped_project: Mapped[str | None] = mapped_column(String, nullable=True)
    verification: Mapped[str | None] = mapped_column(String, nullable=True)  # verbatim | reattributed
    extracted_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    company: Mapped[Company] = relationship(back_populates="signals")


class Score(Base):
    """RESERVED (B5 — Lead Scoring). Trigger: candidate pool > 200 or Phase 3.

    Schema present, formula seeded in intelligence/scorer.py, disabled in daily flow.
    """

    __tablename__ = "scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    domain: Mapped[str] = mapped_column(ForeignKey("companies.domain"), index=True)
    total: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    factor_breakdown: Mapped[str | None] = mapped_column(Text, nullable=True)  # json of sub-scores
    estimated_value_band: Mapped[str | None] = mapped_column(String, nullable=True)
    scored_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    domain: Mapped[str] = mapped_column(ForeignKey("companies.domain"), index=True)
    status: Mapped[str] = mapped_column(String, default="new")
    contact_name: Mapped[str | None] = mapped_column(String, nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String, nullable=True)
    contact_source: Mapped[str | None] = mapped_column(String, nullable=True)  # must be recorded
    region_rule: Mapped[str | None] = mapped_column(String, nullable=True)
    next_action_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    outreach: Mapped[list[Outreach]] = relationship(back_populates="lead")


class Outreach(Base):
    __tablename__ = "outreach"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), index=True)
    channel: Mapped[str] = mapped_column(String)  # email, linkedin_manual, warm_intro
    draft_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    outcome: Mapped[str] = mapped_column(String, default="none")  # none, reply, bounce, optout

    lead: Mapped[Lead] = relationship(back_populates="outreach")


class OptOut(Base):
    __tablename__ = "opt_outs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    domain: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    date: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    permanent: Mapped[bool] = mapped_column(Boolean, default=True)
    reason: Mapped[str | None] = mapped_column(String, nullable=True)


class LLMCache(Base):
    """sha256(model + full prompt) -> response JSON, hit count (SPEC §4.1)."""

    __tablename__ = "llm_cache"

    key: Mapped[str] = mapped_column(String, primary_key=True)  # sha256 hex
    model: Mapped[str] = mapped_column(String)
    response: Mapped[str] = mapped_column(Text)
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


# =============================================================================
# V2 extensions — the loop's new substrate (SPEC §4.3)
# =============================================================================


class Brief(Base):
    """A3-A5 output: one company diagnosed. The Week-1 deliverable."""

    __tablename__ = "briefs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    domain: Mapped[str] = mapped_column(ForeignKey("companies.domain"), index=True)
    bottleneck: Mapped[str | None] = mapped_column(Text, nullable=True)
    wedge: Mapped[str | None] = mapped_column(Text, nullable=True)
    cost_estimate: Mapped[str | None] = mapped_column(String, nullable=True)
    readiness_qualitative: Mapped[str | None] = mapped_column(String, nullable=True)
    brief_path: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    company: Mapped[Company] = relationship(back_populates="briefs")
    demos: Mapped[list[Demo]] = relationship(back_populates="brief")


class Demo(Base):
    """A6 output. RESERVED implementation (Week 2); schema present now."""

    __tablename__ = "demos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    brief_id: Mapped[int | None] = mapped_column(ForeignKey("briefs.id"), index=True, nullable=True)
    domain: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    template_family: Mapped[str | None] = mapped_column(String, nullable=True)
    demo_path: Mapped[str | None] = mapped_column(String, nullable=True)
    loom_script_path: Mapped[str | None] = mapped_column(String, nullable=True)
    deflection_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String, default="scaffolded")

    brief: Mapped[Brief | None] = relationship(back_populates="demos")


class Contact(Base):
    """A8 warm network. Relationship-graph seed for C4 (§3.3)."""

    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String)
    company: Mapped[str | None] = mapped_column(String, nullable=True)
    source: Mapped[str | None] = mapped_column(String, nullable=True)  # how you know them
    warmth: Mapped[str | None] = mapped_column(String, nullable=True)  # cold/warm/hot
    channel: Mapped[str | None] = mapped_column(String, nullable=True)
    last_touch: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_touch: Mapped[date | None] = mapped_column(Date, nullable=True)

    interactions: Mapped[list[Interaction]] = relationship(back_populates="contact")


class Interaction(Base):
    """Structured capture from day 1 (§4.4). Substrate for C3/C4."""

    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contact_id: Mapped[int | None] = mapped_column(ForeignKey("contacts.id"), nullable=True, index=True)
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id"), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String)  # call, note, email, intro, meeting
    notes_path: Mapped[str | None] = mapped_column(String, nullable=True)
    at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    contact: Mapped[Contact | None] = relationship(back_populates="interactions")


class Engagement(Base):
    """Won work. RESERVED (Phase 2); schema present so outcomes can attach."""

    __tablename__ = "engagements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), index=True)
    scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    started: Mapped[date | None] = mapped_column(Date, nullable=True)
    ended: Mapped[date | None] = mapped_column(Date, nullable=True)

    outcome: Mapped[Outcome] = relationship(back_populates="engagement", uselist=False)


class Outcome(Base):
    """RESERVED substrate (§4.4) — the moat's foundation. Written from day 1 once
    engagements exist. Mined by C1 (win/loss), C2 (pricing), C3 (patterns).
    """

    __tablename__ = "outcomes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagements.id"), index=True)
    won: Mapped[bool] = mapped_column(Boolean, default=False)
    result_metric: Mapped[str | None] = mapped_column(String, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    deal_size: Mapped[float | None] = mapped_column(Float, nullable=True)

    engagement: Mapped[Engagement] = relationship(back_populates="outcome")


class Pattern(Base):
    """A11 pattern-library index. Stable string IDs so C7 can lift markdown into a
    graph without rework (§4.4). Backed by tagged markdown in data/pattern_library/.
    """

    __tablename__ = "patterns"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # stable slug id
    niche: Mapped[str | None] = mapped_column(String, nullable=True)
    name: Mapped[str] = mapped_column(String)
    evidence_signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    demo_family: Mapped[str | None] = mapped_column(String, nullable=True)
    times_seen: Mapped[int] = mapped_column(Integer, default=0)


class Proposal(Base):
    """RESERVED (B2 — Proposal Generator). Trigger: After First Client.

    Empty-but-created table (§4.4). Turns diagnosis into scoped, priced proposals.
    """

    __tablename__ = "proposals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id"), nullable=True, index=True)
    brief_id: Mapped[int | None] = mapped_column(ForeignKey("briefs.id"), nullable=True, index=True)
    scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    framing: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
