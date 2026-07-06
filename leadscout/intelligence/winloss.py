"""C1 — Win/Loss analysis. RESERVED. Trigger: >= 5-10 closed outcomes.

Mines the `outcomes` table (captured from day 1) for which niches/framings/prices
close, and tunes the Kernel (A1) and Proposal Generator (B2). Interface present so
downstream code can depend on the shape now.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WinLossReport:
    total: int
    won: int
    top_win_reasons: list[str]
    top_loss_reasons: list[str]


def analyze() -> WinLossReport:  # pragma: no cover - reserved
    raise NotImplementedError("C1 reserved. Trigger: >=5-10 closed outcomes. Substrate: outcomes table.")
