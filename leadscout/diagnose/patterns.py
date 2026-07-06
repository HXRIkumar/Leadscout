"""Pattern matching (A4) + pattern-library sync (A11 substrate).

signal_type -> stable pattern id (matches data/pattern_library/ filenames and the
`patterns` table). Stable IDs are deliberate so C7 can lift the tagged markdown
into a graph later without rework (SPEC §4.4).
"""

from __future__ import annotations

from ..research.extract import SignalCandidate

# signal_type -> (pattern_id, human name, demo_family)
PATTERN_MAP: dict[str, tuple[str, str, str | None]] = {
    "support_hiring": ("support-team-scaling-manually", "Support team scaling manually", "rag_support_bot"),
    "help_center": ("help-center-gaps", "Help center exists but gaps remain", "rag_support_bot"),
    "support_complaints": ("slow-support-response", "Slow/poor support response", "rag_support_bot"),
    "support_widget": ("human-answered-repetitive-qs", "Humans answering repetitive questions", "rag_support_bot"),
    "growth_pressure": ("growth-outpacing-support", "Growth outpacing support capacity", "rag_support_bot"),
    "community_gap": ("community-self-support-gap", "Community used as informal support", "rag_support_bot"),
    "docs_lagging": ("docs-lagging-product", "Docs lagging product velocity", "rag_support_bot"),
    "funding_event": ("funded-can-afford", "Recently funded (budget corroboration)", None),
}

# Positive signal types that indicate the wedge problem is present.
POSITIVE_TYPES = {
    "support_hiring", "help_center", "support_complaints", "support_widget",
    "growth_pressure", "community_gap", "docs_lagging",
}


def matched_patterns(signals: list[SignalCandidate]) -> list[dict]:
    """Return distinct matched patterns (id, name, demo_family, best confidence)."""
    best: dict[str, dict] = {}
    for s in signals:
        if s.is_anti_signal:
            continue
        m = PATTERN_MAP.get(s.signal_type)
        if not m:
            continue
        pid, name, family = m
        cur = best.get(pid)
        if cur is None or s.confidence > cur["confidence"]:
            best[pid] = {"id": pid, "name": name, "demo_family": family, "confidence": s.confidence}
    return sorted(best.values(), key=lambda p: p["confidence"], reverse=True)
