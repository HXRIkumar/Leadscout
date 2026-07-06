"""A7 — Outreach drafting (1:1 only, SPEC §3.1 A7 / §12).

brief + one verified fact -> a 90-120 word personal message + a warm-intro-request
variant + the correct compliance footer by region. Deterministic by default
(safe, offline); LLM-polished when keys exist (prompts/writer.md). Sent MANUALLY
from the operator's own inbox. Mass/automated sending is Never Build (§3.5).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select

from ..db import init_db, session_scope
from ..kernel import load_kernel
from ..logging import get_logger
from ..models import Brief, Signal
from .compliance import Region, compliance_footer, may_contact, region_for_country

log = get_logger(__name__)


class NoBriefError(RuntimeError):
    pass


@dataclass
class DraftResult:
    domain: str
    region: Region
    anchor_quote: str | None
    anchor_source: str | None
    cold_message: str
    warm_intro: str
    footer: str
    sendable: bool
    block_reason: str = ""


def _anchor_signal(domain: str) -> Signal | None:
    """Highest-confidence positive verified signal = the fact to anchor on."""
    with session_scope() as s:
        rows = s.execute(select(Signal).where(Signal.domain == domain)).scalars().all()
        positives = [r for r in rows if r.mapped_project]  # positives carry a mapped_project
        if not positives:
            positives = rows
        if not positives:
            return None
        best = max(positives, key=lambda r: r.confidence)
        # detach a plain copy
        return Signal(domain=best.domain, signal_type=best.signal_type,
                      evidence_quote=best.evidence_quote, source_url=best.source_url,
                      confidence=best.confidence, mapped_project=best.mapped_project)


def _latest_brief(domain: str) -> Brief | None:
    with session_scope() as s:
        b = s.query(Brief).filter(Brief.domain == domain).order_by(Brief.id.desc()).first()
        if b is None:
            return None
        return Brief(domain=b.domain, bottleneck=b.bottleneck, wedge=b.wedge,
                     cost_estimate=b.cost_estimate, readiness_qualitative=b.readiness_qualitative)


def _cold_message(company: str, contact: str, bottleneck: str, anchor: Signal | None,
                  cost: str | None, kernel, footer: str) -> str:
    hi = f"Hi {contact}," if contact else "Hi,"
    anchor_line = (
        f"I was reading through {company}'s site and noticed: “{anchor.evidence_quote[:140]}”."
        if anchor else f"I've been researching {company}."
    )
    problem = (bottleneck or "It looks like repetitive support questions are eating your team's time.").rstrip(".")
    cost_line = f" (roughly {cost})" if cost else ""
    body = (
        f"{hi}\n\n"
        f"{anchor_line} {problem}{cost_line}.\n\n"
        f"I build support-deflection assistants for teams like yours — trained on your own help "
        f"docs, they typically take ~35% of repetitive tickets off the queue. I actually put together "
        f"a small working version on {company}'s public docs; happy to send a 60-second Loom.\n\n"
        f"Worth a quick call to see if it's useful?\n\n"
        f"{footer}"
    )
    return body


def _warm_intro(company: str, bottleneck: str) -> str:
    problem = (bottleneck or "a growing support burden").rstrip(".")
    return (
        f"Quick ask — could you intro me to someone at {company}? I've been researching them "
        f"({problem}) and built a small support-deflection demo on their public docs I think "
        f"they'd find genuinely useful. No pressure if it's not a natural connection."
    )


def draft_message(domain: str, *, region: Region | None = None, contact_name: str = "",
                  use_llm: bool = True) -> DraftResult:
    init_db()
    kernel = load_kernel()
    brief = _latest_brief(domain)
    if brief is None:
        raise NoBriefError(f"No brief for {domain}. Run `leadscout brief {domain}` first.")

    region = region or region_for_country(None)
    footer = compliance_footer(region)
    anchor = _anchor_signal(domain)
    company = domain.split(".")[0].capitalize()

    sendable, reason = may_contact(region, domain=domain)

    cold = _cold_message(company, contact_name, brief.bottleneck, anchor, brief.cost_estimate, kernel, footer)
    warm = _warm_intro(company, brief.bottleneck)

    if use_llm:
        cold = _llm_polish(cold, anchor, footer) or cold

    return DraftResult(
        domain=domain, region=region,
        anchor_quote=anchor.evidence_quote if anchor else None,
        anchor_source=anchor.source_url if anchor else None,
        cold_message=cold, warm_intro=warm, footer=footer,
        sendable=sendable, block_reason="" if sendable else reason,
    )


def _llm_polish(draft: str, anchor: Signal | None, footer: str) -> str | None:
    from ..config import get_settings
    if not get_settings().has_any_llm():
        return None
    from ..llm import NoLLMAvailable, llm_complete
    from ..prompts import load_prompt
    prompt = (
        "Polish this cold outreach draft to 90-120 words: tighten, keep it human and "
        "specific, keep the single anchored fact, keep one clear CTA, and keep the footer "
        "EXACTLY as-is at the end. Do not invent any new facts.\n\n"
        f"ANCHOR FACT (do not change): {anchor.evidence_quote if anchor else '(none)'}\n\n"
        f"DRAFT:\n{draft}\n\nFOOTER (keep verbatim):\n{footer}"
    )
    try:
        # outreach polish runs on the free tier ($0 marginal per §4.1), not frontier
        return llm_complete(prompt, task="extraction", system=load_prompt("writer")).text.strip()
    except NoLLMAvailable:
        return None
