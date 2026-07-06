"""A2 — Discovery Lite (the module that keeps the LeadScout name).

Thin adapters assemble a hand-fit list of 30-50 in-niche companies. Finding is a
commodity (SPEC §2.2 rank 1), so this gets days, not weeks. EDGAR is reserved (B6).
"""

from .base import Candidate, Source  # noqa: F401
from .discovery import discover, prefilter  # noqa: F401
