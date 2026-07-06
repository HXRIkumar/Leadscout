"""LLM layer (SPEC §4.1).

Routing: Groq (bulk research/extraction, free) -> Gemini Flash-Lite (schema
fallback, free) -> frontier (diagnosis + demo scaffolding only, budget-capped).
Cache-first everywhere (never pay twice for the same company).

Everything degrades gracefully: with no API keys, `llm_complete` raises
NoLLMAvailable and callers fall back to deterministic heuristics, so the whole
pipeline runs offline.
"""

from .router import LLMResult, NoLLMAvailable, llm_complete  # noqa: F401
