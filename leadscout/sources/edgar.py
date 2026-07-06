"""SEC EDGAR Form D adapter — RESERVED (B6).

Trigger (SPEC §3.2): Phase 2, when the pipeline needs steady top-up. Timing signals
(funding events) re-enter as a *feed into research*, not a thesis. The V1 EDGAR
adapter design is the reserved implementation.

Politeness when built (SPEC §7.3): descriptive User-Agent with operator email,
<= 10 req/s, prefer bulk/daily index files over hammering full-text search.
"""

from __future__ import annotations

from .base import Candidate

name = "edgar"


class EDGARFormD:
    """RESERVED. Interface present so Discovery Lite composes it additively later."""

    name = "edgar"

    def fetch(self, *, limit: int = 50) -> list[Candidate]:  # pragma: no cover - reserved
        raise NotImplementedError(
            "EDGAR Form D adapter is reserved (B6). Trigger: Phase 2 pipeline top-up. "
            "See docs/ROADMAP_PROGRESS.md."
        )
