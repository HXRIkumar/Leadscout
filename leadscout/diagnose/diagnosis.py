"""A4 — Pain Detection & Diagnosis orchestrator (consultant-grade).

Deterministic by default (works offline, fully traceable to verified signals),
optionally sharpened by the diagnostician LLM when keys exist. The LLM may only
rephrase/organize from the verified signals — it introduces no new facts.

Produces a consultant-grade read: business summary, pain points, AI + automation
opportunities, an evidence-grounded ROI line, implementation complexity, the
recommended project, an outreach angle, and a proposal outline (B2 preview).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from ..kernel import Kernel
from ..logging import get_logger
from ..research.extract import SignalCandidate
from .cost import CostEstimate
from .patterns import POSITIVE_TYPES, matched_patterns

log = get_logger(__name__)

_ANTI_CONF = 0.6  # anti-signal confidence needed to trigger disqualification

_CLAUSE = {
    "support_hiring": "they are expanding the support/CX team to keep up with ticket volume",
    "help_center": "a public help center exists, yet repetitive questions still reach humans",
    "support_complaints": "customers publicly cite slow or poor support response",
    "support_widget": "a live support widget suggests humans field repetitive questions",
    "growth_pressure": "customer growth is outpacing a small team",
    "community_gap": "a community forum is being used as informal, unscaled support",
    "docs_lagging": "product velocity is outpacing documentation, pushing load onto support",
}

_SUMMARY_BIT = {
    "help_center": "maintains a public help center/docs",
    "support_hiring": "is actively hiring support/CX",
    "support_complaints": "has public complaints about support response",
    "support_widget": "runs a live support widget",
    "growth_pressure": "shows rapid customer growth",
    "community_gap": "leans on a community forum for support",
    "docs_lagging": "ships faster than its docs keep up",
}


@dataclass
class Diagnosis:
    bottleneck: str
    wedge: str
    readiness_qualitative: str
    readiness_reason: str
    disqualified: bool = False
    disqualify_reason: str = ""
    matched_patterns: list[dict] = field(default_factory=list)
    confidence: float = 0.0
    source: str = "deterministic"
    # --- consultant-grade fields ---
    business_summary: str = ""
    pain_points: list[str] = field(default_factory=list)
    ai_opportunities: list[str] = field(default_factory=list)
    automation_opportunities: list[str] = field(default_factory=list)
    estimated_roi: str = ""
    implementation_complexity: str = ""       # low | medium | high
    recommended_project: str = ""             # demo archetype
    outreach_angle: str = ""
    proposal_outline: list[str] = field(default_factory=list)


def _wedge(company_name: str, kernel: Kernel) -> str:
    return (
        f"A retrieval-augmented support assistant trained on {company_name}'s own help center "
        f"and docs, deflecting the repetitive top questions before they reach a human — "
        f"provable on their real top-20 questions in a {kernel.offer.pilot.weeks}-week, "
        f"{kernel.offer.pilot.price} pilot ({kernel.offer.headline_number})."
    )


def _readiness(present: set[str]) -> tuple[str, str]:
    strong = present & {"support_hiring", "support_complaints", "help_center"}
    if "help_center" in present and (present & {"support_hiring", "support_complaints"}):
        return "high", "A help center exists to train on, plus clear signs of live support load."
    if strong:
        return "medium", "At least one strong support-load signal is present in public data."
    if present:
        return "low", "Only corroborating signals found; confirm the support load on a call."
    return "low", "Insufficient public evidence of the support-deflection problem."


def _price_number(price: str) -> float | None:
    digits = re.sub(r"[^0-9.]", "", price or "")
    try:
        return float(digits) if digits else None
    except ValueError:
        return None


def _roi_line(kernel: Kernel, cost: CostEstimate | None) -> str:
    if cost is None or cost.value_usd_per_year <= 0:
        return f"Pilot {kernel.offer.pilot.price} for {kernel.offer.headline_number} — ROI quantified once support load is confirmed."
    pilot = _price_number(kernel.offer.pilot.price)
    base = f"{kernel.offer.pilot.price} pilot against {cost.headline}"
    if pilot:
        pct = pilot / cost.value_usd_per_year * 100
        return f"{base} — ~{pct:.0f}% of the annual at-risk cost; deflecting even part of that load pays the pilot back within weeks."
    return base


def _proposal_outline(kernel: Kernel) -> list[str]:
    o = kernel.offer
    return [
        "Problem & evidence — the verified support-load signals above (each quoted + sourced)",
        f"Proposed pilot — {o.archetype} trained on their public help center + docs",
        f"Success metric — {o.headline_number}, measured on their real top-20 questions",
        f"Timeline — {o.pilot.weeks} weeks",
        f"Price — {o.pilot.price} (fixed)",
        "Path to production — wire into the live support widget; expand coverage; maintenance retainer",
    ]


def _deterministic(
    signals: list[SignalCandidate], kernel: Kernel, company_name: str, cost: CostEstimate | None
) -> Diagnosis:
    anti = [s for s in signals if s.is_anti_signal and s.confidence >= _ANTI_CONF]
    if any(s.signal_type == "ai_native" for s in anti):
        s = next(s for s in anti if s.signal_type == "ai_native")
        return Diagnosis(
            bottleneck="The company's own product appears to be AI-native.",
            wedge="Not a fit — they build LLM systems themselves.",
            readiness_qualitative="low", readiness_reason="Disqualifier #1 (AI-native).",
            disqualified=True,
            disqualify_reason=f"AI-native product (evidence: “{s.evidence_quote[:120]}”)",
        )
    if any(s.signal_type == "agency" for s in anti):
        s = next(s for s in anti if s.signal_type == "agency")
        return Diagnosis(
            bottleneck="The company appears to be an agency / consultancy / dev shop.",
            wedge="Not a fit — competitor, not a client.",
            readiness_qualitative="low", readiness_reason="Disqualifier #3 (agency).",
            disqualified=True,
            disqualify_reason=f"Agency/consultancy (evidence: “{s.evidence_quote[:120]}”)",
        )

    positives = [s for s in signals if not s.is_anti_signal and s.signal_type in POSITIVE_TYPES]
    present = {s.signal_type for s in positives}
    patterns = matched_patterns(signals)

    ordered = sorted(present, key=lambda t: max((s.confidence for s in positives if s.signal_type == t), default=0), reverse=True)
    clauses = [_CLAUSE[t] for t in ordered if t in _CLAUSE][:3]
    bottleneck = (
        "Support load is rising: " + "; ".join(clauses) + "."
        if clauses else
        "Public evidence of a support-deflection problem is thin — worth a quick manual check before outreach."
    )
    readiness, reason = _readiness(present)
    conf = round(sum(s.confidence for s in positives[:3]) / max(1, min(3, len(positives))), 2) if positives else 0.0

    # consultant-grade deterministic fields
    bits = [_SUMMARY_BIT[t] for t in ordered if t in _SUMMARY_BIT][:3]
    business_summary = (
        f"{company_name} " + ", ".join(bits) + "." if bits
        else f"{company_name}: limited public support signal — confirm the operation on a call."
    )
    pain_points = [_CLAUSE[t].capitalize() for t in ordered if t in _CLAUSE][:4]
    complexity = "low" if "help_center" in present else "medium"
    top = positives[0] if positives else None
    outreach_angle = (
        f"Anchor on “{top.evidence_quote[:120]}” ({top.source_url}), then offer the "
        f"{kernel.offer.pilot.weeks}-week deflection pilot."
        if top else "Manual research needed before outreach — public signal is thin."
    )

    return Diagnosis(
        bottleneck=bottleneck, wedge=_wedge(company_name, kernel),
        readiness_qualitative=readiness, readiness_reason=reason,
        matched_patterns=patterns, confidence=conf, source="deterministic",
        business_summary=business_summary,
        pain_points=pain_points,
        ai_opportunities=[_wedge(company_name, kernel)],
        automation_opportunities=[
            "Auto-deflect repetitive tickets before they reach a human",
            "Auto-draft first-response suggestions for support agents from the same knowledge base",
        ],
        estimated_roi=_roi_line(kernel, cost),
        implementation_complexity=complexity,
        recommended_project=kernel.offer.archetype,
        outreach_angle=outreach_angle,
        proposal_outline=_proposal_outline(kernel),
    )


def _llm_refine(
    base: Diagnosis, signals: list[SignalCandidate], kernel: Kernel, company_name: str, cost: CostEstimate | None
) -> Diagnosis:
    """Sharpen/expand wording via the diagnostician prompt. Facts stay grounded in signals."""
    from ..config import get_settings
    if not get_settings().has_any_llm():
        return base
    from ..llm import NoLLMAvailable, llm_complete
    from ..prompts import load_prompt

    verified = "\n".join(
        f"- [{s.signal_type}] “{s.evidence_quote}” ({s.source_url})" for s in signals if not s.is_anti_signal
    ) or "(no positive signals)"
    cost_line = cost.headline if cost else "(not computed)"
    prompt = (
        f"COMPANY: {company_name}\nNICHE PROBLEM: {kernel.problem.name}\n"
        f"OFFER: {kernel.offer.headline_number}, {kernel.offer.pilot.price} / {kernel.offer.pilot.weeks} weeks, "
        f"archetype {kernel.offer.archetype}\nCOST OF PROBLEM (A5): {cost_line}\n\n"
        f"VERIFIED SIGNALS (use ONLY these — do not invent facts):\n{verified}\n"
    )
    try:
        result = llm_complete(prompt, task="diagnosis", system=load_prompt("diagnostician"), json_mode=True)
        data = _parse(result.text)
    except (NoLLMAvailable, ValueError):
        return base
    if not data:
        return base

    if data.get("disqualify"):
        return Diagnosis(
            bottleneck=base.bottleneck, wedge="Not a fit.",
            readiness_qualitative="low", readiness_reason=data.get("readiness_reason", ""),
            disqualified=True,
            disqualify_reason=data.get("disqualify_reason", "LLM flagged disqualifier"),
            matched_patterns=base.matched_patterns, confidence=base.confidence, source="llm",
        )

    def _list(key: str, fallback: list[str]) -> list[str]:
        v = data.get(key)
        return [str(x) for x in v] if isinstance(v, list) and v else fallback

    return Diagnosis(
        bottleneck=data.get("bottleneck") or base.bottleneck,
        wedge=data.get("wedge") or base.wedge,
        readiness_qualitative=data.get("readiness_qualitative") or base.readiness_qualitative,
        readiness_reason=data.get("readiness_reason") or base.readiness_reason,
        matched_patterns=base.matched_patterns, confidence=base.confidence, source="llm",
        business_summary=data.get("business_summary") or base.business_summary,
        pain_points=_list("pain_points", base.pain_points),
        ai_opportunities=_list("ai_opportunities", base.ai_opportunities),
        automation_opportunities=_list("automation_opportunities", base.automation_opportunities),
        estimated_roi=data.get("estimated_roi") or base.estimated_roi,
        implementation_complexity=data.get("implementation_complexity") or base.implementation_complexity,
        recommended_project=data.get("recommended_project") or base.recommended_project,
        outreach_angle=data.get("outreach_angle") or base.outreach_angle,
        proposal_outline=_list("proposal_outline", base.proposal_outline),
    )


def _parse(text: str) -> dict | None:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None


def diagnose(
    signals: list[SignalCandidate], kernel: Kernel, *, company_name: str,
    cost: CostEstimate | None = None, use_llm: bool = True,
) -> Diagnosis:
    base = _deterministic(signals, kernel, company_name, cost)
    if base.disqualified or not use_llm:
        return base
    return _llm_refine(base, signals, kernel, company_name, cost)
