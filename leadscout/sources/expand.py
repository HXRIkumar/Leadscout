"""Competitor / similar-company expansion (compliant, quality-safeguarded).

Given a seed company, the frontier LLM suggests comparable in-niche B2B SaaS
companies. Suggestions are CANDIDATES only — nothing is asserted as fact. Quality
gates keep this from becoming a spam-list: (1) the niche prefilter drops
agencies/AI-native, (2) platforms are filtered, (3) with verify=True each domain
must actually resolve to a reachable site (drops hallucinated domains). The
candidates still get a full `brief` before any trust. Never fabricates.
"""

from __future__ import annotations

import json
import re

from ..logging import get_logger
from ..research.fetch import canonical_url, normalize_domain, polite_fetch
from .base import Candidate
from .discovery import prefilter
from .search import _is_platform

log = get_logger(__name__)


def _parse_json(text: str) -> dict | None:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None


def similar_companies(
    seed_domain: str, *, limit: int = 8, context: str | None = None, verify: bool = True, persist: bool = True
) -> list[Candidate]:
    from ..config import get_settings
    if not get_settings().has_any_llm():
        log.info("expansion needs an LLM (frontier). Skipping.")
        return []

    seed = normalize_domain(seed_domain)
    if context is None:
        try:
            r = polite_fetch(canonical_url(seed))
            context = r.clean_text[:600] if r.ok else seed
        except Exception:
            context = seed

    from ..llm import NoLLMAvailable, llm_complete
    prompt = (
        f"Seed company: {seed} — {context}\n\n"
        f"List up to {limit} OTHER real, established B2B SaaS companies in a similar space that "
        f"likely run a customer-support operation. EXCLUDE AI-native/LLM-product companies and "
        f"agencies/dev-shops. Only real companies with real websites — do NOT invent domains. "
        f'Return STRICT JSON: {{"companies":[{{"name":"","domain":"","one_liner":""}}]}}.'
    )
    try:
        res = llm_complete(prompt, task="expand", json_mode=True,
                           system="You suggest comparable B2B SaaS companies for outreach. Never invent domains.")
        data = _parse_json(res.text)
    except NoLLMAvailable:
        return []

    items = data.get("companies", []) if isinstance(data, dict) else []
    out: list[Candidate] = []
    seen: set[str] = {seed}
    for it in items:
        if not isinstance(it, dict):
            continue
        domain = normalize_domain(it.get("domain", ""))
        if not domain or domain in seen or _is_platform(domain):
            continue
        seen.add(domain)
        cand = Candidate(name=(it.get("name") or domain)[:60], domain=domain, source="expand",
                         description=(it.get("one_liner") or "")[:300])
        if not prefilter(cand, set()).ok:      # niche gate (agency/ai-native)
            continue
        if verify:
            try:
                if not polite_fetch(canonical_url(domain)).ok:   # domain must actually resolve
                    continue
            except Exception:
                continue
        out.append(cand)

    if persist and out:
        from .discovery import add_manual
        for c in out:
            add_manual(c.domain, c.name, c.description)   # persists as a candidate company
    log.info("expansion: %d verified similar companies from %s", len(out), seed)
    return out
