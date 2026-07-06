"""C2 — Proposal pricing model. RESERVED. Trigger: After 10 clients.

Learns price-to-win per ICP from your own outcomes (an edge no competitor can
observe). Feeds the Proposal Generator (B2). Depends on C1 + outcomes.
"""

from __future__ import annotations


def price_to_win(icp: str, archetype: str) -> float:  # pragma: no cover - reserved
    raise NotImplementedError("C2 reserved. Trigger: After 10 clients. Substrate: outcomes + C1.")
