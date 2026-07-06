"""A4 — Pain Detection & Diagnosis orchestrator.

Deterministic by default (works offline, fully traceable to verified signals),
optionally sharpened by the diagnostician LLM prompt when keys exist. The LLM may
only rephrase from the verified signals — it introduces no new facts.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from ..kernel import Kernel
from ..logging import get_logger
from ..research.extract import SignalCandidate
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


def _deterministic(signals: list[SignalCandidate], kernel: Kernel, company_name: str) -> Diagnosis:
    anti = [s for s in signals if s.is_anti_signal and s.confidence >= _ANTI_CONF]
    if any(s.signal_type == "ai_native" for s in anti):
        s = next(s for s in anti if s.signal_type == "ai_native")
        return Diagnosis(
            bottleneck="The company's own product appears to be AI-native.",
            wedge="Not a fit — they build LLM systems themselves.",
            readiness_qualitative="low",
            readiness_reason="Disqualifier #1 (AI-native).",
            disqualified=True,
            disqualify_reason=f"AI-native product (evidence: “{s.evidence_quote[:120]}”)",
        )
    if any(s.signal_type == "agency" for s in anti):
        s = next(s for s in anti if s.signal_type == "agency")
        return Diagnosis(
            bottleneck="The company appears to be an agency / consultancy / dev shop.",
            wedge="Not a fit — competitor, not a client.",
            readiness_qualitative="low",
            readiness_reason="Disqualifier #3 (agency).",
            disqualified=True,
            disqualify_reason=f"Agency/consultancy (evidence: “{s.evidence_quote[:120]}”)",
        )

    positives = [s for s in signals if not s.is_anti_signal and s.signal_type in POSITIVE_TYPES]
    present = {s.signal_type for s in positives}
    patterns = matched_patterns(signals)

    # top clauses by signal confidence
    ordered = sorted(present, key=lambda t: max((s.confidence for s in positives if s.signal_type == t), default=0), reverse=True)
    clauses = [_CLAUSE[t] for t in ordered if t in _CLAUSE][:3]
    if clauses:
        bottleneck = "Support load is rising: " + "; ".join(clauses) + "."
    else:
        bottleneck = "Public evidence of a support-deflection problem is thin — worth a quick manual check before outreach."

    readiness, reason = _readiness(present)
    conf = round(sum(s.confidence for s in positives[:3]) / max(1, min(3, len(positives))), 2) if positives else 0.0

    return Diagnosis(
        bottleneck=bottleneck,
        wedge=_wedge(company_name, kernel),
        readiness_qualitative=readiness,
        readiness_reason=reason,
        matched_patterns=patterns,
        confidence=conf,
        source="deterministic",
    )


def _llm_refine(base: Diagnosis, signals: list[SignalCandidate], kernel: Kernel, company_name: str) -> Diagnosis:
    """Optionally sharpen wording via the diagnostician prompt. Facts stay fixed."""
    from ..config import get_settings
    if not get_settings().has_any_llm():
        return base
    from ..llm import NoLLMAvailable, llm_complete
    from ..prompts import load_prompt

    verified = "\n".join(
        f"- [{s.signal_type}] “{s.evidence_quote}” ({s.source_url})" for s in signals if not s.is_anti_signal
    ) or "(no positive signals)"
    prompt = (
        f"COMPANY: {company_name}\nNICHE PROBLEM: {kernel.problem.name}\n"
        f"OFFER: {kernel.offer.headline_number}, {kernel.offer.pilot.price} / {kernel.offer.pilot.weeks} weeks\n\n"
        f"VERIFIED SIGNALS:\n{verified}\n"
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
            readiness_qualitative="low",
            readiness_reason=data.get("readiness_reason", ""),
            disqualified=True,
            disqualify_reason=data.get("disqualify_reason", "LLM flagged disqualifier"),
            matched_patterns=base.matched_patterns, confidence=base.confidence, source="llm",
        )
    return Diagnosis(
        bottleneck=data.get("bottleneck") or base.bottleneck,
        wedge=data.get("wedge") or base.wedge,
        readiness_qualitative=data.get("readiness_qualitative") or base.readiness_qualitative,
        readiness_reason=data.get("readiness_reason") or base.readiness_reason,
        matched_patterns=base.matched_patterns,
        confidence=base.confidence,
        source="llm",
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


def diagnose(signals: list[SignalCandidate], kernel: Kernel, *, company_name: str, use_llm: bool = True) -> Diagnosis:
    base = _deterministic(signals, kernel, company_name)
    if base.disqualified or not use_llm:
        return base
    return _llm_refine(base, signals, kernel, company_name)
