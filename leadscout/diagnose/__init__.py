"""A4 + A5 — Pain Detection & Diagnosis + Cost-of-Problem Estimator.

Maps verified facts -> the niche's known pain patterns -> the specific bottleneck,
the wedge (a RAG deflection bot), a qualitative AI-readiness read, and a defensible
dollar figure. Every output traces back to a verified signal (SPEC §3.1 A4/A5).
"""

from .cost import CostEstimate, estimate_cost  # noqa: F401
from .diagnosis import Diagnosis, diagnose  # noqa: F401
