"""B5 — Lead scoring. RESERVED (trigger: candidate pool > 200 or Phase 3).

The `Scorer` Protocol and the V1 fixed-weight formula (SPEC §10) are preserved
here as the seed, and the `scores` table exists — but scoring is DISABLED in the
daily flow (at 30-50 curated accounts, reading beats ranking, SPEC §3.2/§6).
When the trigger fires, wire FixedWeightScorer into the pipeline; C5 later
reweights it from outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from ..research.extract import SignalCandidate

# V1 factor weights (SPEC §10), preserved as the seed. Sum = 100.
V1_WEIGHTS = {
    "ai_opportunity_fit": 30,
    "timing_urgency": 25,
    "company_size_fit": 15,
    "funding_budget": 15,
    "reachability": 15,
}


@dataclass
class ScoreResult:
    total: int
    factor_breakdown: dict[str, float] = field(default_factory=dict)
    estimated_value_band: str = ""


class Scorer(Protocol):
    def score(self, signals: list[SignalCandidate], facts: dict) -> ScoreResult:
        ...


class FixedWeightScorer:
    """Seed implementation of the V1 formula. NOT wired into the daily flow (B5)."""

    def score(self, signals: list[SignalCandidate], facts: dict | None = None) -> ScoreResult:
        facts = facts or {}
        positives = [s for s in signals if not s.is_anti_signal]
        breakdown: dict[str, float] = {}

        best = max((s.confidence for s in positives), default=0.0)
        distinct = len({s.signal_type for s in positives})
        fit = best * V1_WEIGHTS["ai_opportunity_fit"] + min(5, (distinct - 1) * 2 if distinct > 1 else 0)
        breakdown["ai_opportunity_fit"] = round(min(V1_WEIGHTS["ai_opportunity_fit"] + 5, fit), 1)

        # timing: presence of recency; without dates we proxy with signal strength
        breakdown["timing_urgency"] = round(best * V1_WEIGHTS["timing_urgency"], 1)
        # size/reachability/funding proxies (real values wired at trigger from enrichment)
        breakdown["company_size_fit"] = float(V1_WEIGHTS["company_size_fit"] * 0.6)
        breakdown["funding_budget"] = float(
            V1_WEIGHTS["funding_budget"] if any(s.signal_type == "funding_event" for s in signals) else 0
        )
        breakdown["reachability"] = float(V1_WEIGHTS["reachability"] * 0.5)

        total = int(round(min(100.0, sum(breakdown.values()))))
        return ScoreResult(total=total, factor_breakdown=breakdown)


# Project value bands (SPEC §14) by demo archetype — startup / mid-market.
_VALUE_BANDS = {
    "rag_support_bot": "$5k–$20k (startup) / $25k–$75k (mid-market)",
    "doc_extraction": "$7.5k–$25k / $30k–$100k",
    "workflow_automation": "$3k–$20k / $25k–$100k",
}


def opportunity_score(
    signals: list[SignalCandidate], archetype: str, *, disqualified: bool = False
) -> ScoreResult:
    """Explainable 0-100 opportunity score for triage/ranking. Deterministic, cited
    via factor_breakdown. Disqualified companies score 0. Activated per the lead-gen
    goal (the B5 seed formula, wired for ranking — C5 will reweight from outcomes)."""
    if disqualified:
        return ScoreResult(total=0, factor_breakdown={"disqualified": 0.0}, estimated_value_band="n/a — disqualified")
    r = FixedWeightScorer().score(signals)
    r.estimated_value_band = _VALUE_BANDS.get(archetype, "")
    return r
