"""LLM router (SPEC §4.1): one `llm_complete()` entry point.

Routing policy (provider-agnostic — chosen by FRONTIER_PROVIDER, default OpenAI):
- bulk (research / extraction, incl. outreach + content polish)  -> Groq (free) -> Gemini (free)
- premium (diagnosis / demo generation / proposal / architecture) -> frontier (OpenAI by
  default; Anthropic if FRONTIER_PROVIDER=anthropic), budget-capped -> free fallback

Cache-first (never pay twice). Budget-guarded (hard caps, warn at 80%). If no
provider is usable (no keys / all failed / budget exhausted), raises
NoLLMAvailable so callers fall back to deterministic heuristics — the pipeline
always runs, keys only raise quality.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ..config import get_settings
from ..logging import get_logger
from . import providers as P
from .budget import BudgetGuard
from .cache import get_cached, set_cached

log = get_logger(__name__)

BULK_TASKS = {"research", "extraction"}
# Premium reasoning tasks routed to the frontier provider (OpenAI by default):
# diagnosis, demo generation, proposal-quality reasoning, architecture suggestions.
FRONTIER_TASKS = {"diagnosis", "demo", "proposal", "architecture"}


class NoLLMAvailable(RuntimeError):
    """No provider produced a result (no keys, all errored, or budget exhausted)."""


@dataclass
class LLMResult:
    text: str
    model: str
    provider: str
    cached: bool


@dataclass
class _Candidate:
    provider: str
    model: str
    budget_kind: str | None  # "frontier" | "groq" | None
    call: Callable[[], P.ProviderResponse]


def _candidates(task: str, system: str, prompt: str, json_mode: bool) -> list[_Candidate]:
    s = get_settings()
    out: list[_Candidate] = []

    def groq() -> _Candidate:
        return _Candidate("groq", P.GROQ_MODEL, "groq",
                          lambda: P.groq_complete(s.groq_api_key, system, prompt, json_mode=json_mode))

    def gemini() -> _Candidate:
        return _Candidate("gemini", P.GEMINI_MODEL, None,
                          lambda: P.gemini_complete(s.gemini_api_key, system, prompt, json_mode=json_mode))

    def anthropic() -> _Candidate:
        return _Candidate("anthropic", s.frontier_model, "frontier",
                          lambda: P.anthropic_complete(s.anthropic_api_key, system, prompt,
                                                       model=s.frontier_model, json_mode=json_mode))

    def openai_frontier() -> _Candidate:
        return _Candidate("openai", s.frontier_model, "frontier",
                          lambda: P.openai_complete(s.openai_api_key, system, prompt,
                                                    model=s.frontier_model, json_mode=json_mode))

    if task in FRONTIER_TASKS:
        if s.frontier_provider == "anthropic" and s.anthropic_api_key:
            out.append(anthropic())
        elif s.frontier_provider == "openai" and s.openai_api_key:
            out.append(openai_frontier())
        # free fallbacks so diagnosis still produces something without frontier keys
        if s.groq_api_key:
            out.append(groq())
        if s.gemini_api_key:
            out.append(gemini())
    else:  # bulk
        if s.groq_api_key:
            out.append(groq())
        if s.gemini_api_key:
            out.append(gemini())
    return out


def llm_complete(
    prompt: str,
    *,
    task: str,
    system: str = "",
    json_mode: bool = False,
    budget: BudgetGuard | None = None,
) -> LLMResult:
    """Route, cache, budget-guard, and return an LLM completion.

    Raises NoLLMAvailable if nothing usable produced a result.
    """
    guard = budget or BudgetGuard()
    cache_prompt = f"{system}\n\n{prompt}" if system else prompt

    candidates = _candidates(task, system, prompt, json_mode)
    if not candidates:
        raise NoLLMAvailable(f"no provider configured for task={task!r}")

    last_err: Exception | None = None
    for c in candidates:
        # 1) cache-first
        cached = get_cached(c.model, cache_prompt)
        if cached is not None:
            return LLMResult(text=cached, model=c.model, provider=c.provider, cached=True)

        # 2) budget gate
        if c.budget_kind == "frontier":
            ok, warn = guard.frontier_ok()
            if not ok:
                log.warning("frontier budget exhausted; skipping %s", c.provider)
                continue
            if warn:
                log.warning("frontier budget at >=80%%")
        elif c.budget_kind == "groq":
            ok, warn = guard.groq_ok()
            if not ok:
                log.warning("groq daily cap reached; skipping")
                continue

        # 3) call
        try:
            resp = c.call()
        except P.ProviderError as e:
            last_err = e
            log.warning("provider %s failed: %s", c.provider, e)
            continue

        # 4) record budget + cache
        if c.budget_kind == "frontier":
            guard.record_frontier(c.model, resp.input_tokens, resp.output_tokens)
        elif c.budget_kind == "groq":
            guard.record_groq()
        set_cached(c.model, cache_prompt, resp.text)
        return LLMResult(text=resp.text, model=c.model, provider=c.provider, cached=False)

    raise NoLLMAvailable(f"all providers failed for task={task!r}: {last_err}")
