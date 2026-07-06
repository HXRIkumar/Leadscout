"""A5 — Cost-of-Problem Estimator.

Puts a defensible dollar figure on the wedge problem using the kernel's cost model.
Overrides the default support headcount whenever a verified signal lets us infer a
better number (e.g. "hiring 4 support engineers"). The number is what makes the
brief sell (SPEC §3.1 A5).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..kernel import Kernel
from ..research.extract import SignalCandidate

_HEADCOUNT_CAP = 50  # sanity ceiling for inferred support headcount


@dataclass
class CostEstimate:
    value_usd_per_year: float
    headline: str
    method: str
    inputs: dict
    evidence: list[dict] = field(default_factory=list)  # quotes supporting the inputs


def _infer_headcount(signals: list[SignalCandidate]) -> tuple[int | None, dict | None]:
    """Best-effort: pull a support headcount from support-hiring quotes."""
    best: tuple[int, dict] | None = None
    for s in signals:
        if s.signal_type != "support_hiring":
            continue
        for n in re.findall(r"\b(\d{1,2})\b", s.evidence_quote):
            val = int(n)
            if 1 <= val <= _HEADCOUNT_CAP:
                if best is None or val > best[0]:
                    best = (val, {"signal_type": s.signal_type, "quote": s.evidence_quote, "source_url": s.source_url})
    if best:
        return best[0], best[1]
    return None, None


def estimate_cost(signals: list[SignalCandidate], kernel: Kernel) -> CostEstimate:
    primary = kernel.problem.cost_logic.primary
    defaults = primary.defaults
    loaded = float(defaults.get("loaded_annual_cost_per_rep", 55000))
    deflectable = float(defaults.get("deflectable_fraction", 0.35))
    default_hc = int(defaults.get("support_headcount", 3))

    inferred, evidence_row = _infer_headcount(signals)
    headcount = inferred if inferred else default_hc

    value = headcount * loaded * deflectable
    headline = f"≈ ${value:,.0f}/yr in deflectable support load"

    evidence = [evidence_row] if evidence_row else []
    method = (
        f"{headcount} support rep(s) × ${loaded:,.0f}/yr loaded × {deflectable:.0%} deflectable"
        + ("" if inferred else " (headcount is the kernel default — no public headcount signal found)")
    )
    return CostEstimate(
        value_usd_per_year=round(value, 0),
        headline=headline,
        method=method,
        inputs={
            "support_headcount": headcount,
            "headcount_source": "inferred_from_evidence" if inferred else "kernel_default",
            "loaded_annual_cost_per_rep": loaded,
            "deflectable_fraction": deflectable,
        },
        evidence=evidence,
    )
