"""Discovery Lite orchestrator + deterministic prefilter (SPEC §8).

Runs thin adapters, dedupes by canonical domain, applies a deterministic prefilter
(each failure records its reason), and persists survivors as candidate companies.
Depth over breadth: this feeds a curated 30-50 list, not a mass queue (SPEC §6).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select

from ..db import init_db, session_scope
from ..logging import get_logger
from ..models import Company, OptOut
from ..research.fetch import normalize_domain
from .base import Candidate
from .hn import HNWhoIsHiring
from .yc import YCDirectory

log = get_logger(__name__)

_AGENCY_KW = ["agency", "consultancy", "consulting", "dev shop", "development studio",
              "we build software for", "software house", "digital studio"]
_AI_NATIVE_KW = ["ai-powered", "llm", "gpt-", "generative ai", "ai platform",
                 "ai copilot", "ai agent platform", "ai-native", "powered by ai"]

DEFAULT_SOURCES = [HNWhoIsHiring(), YCDirectory()]


@dataclass
class PrefilterResult:
    ok: bool
    reason: str = ""


def prefilter(cand: Candidate, opt_out_domains: set[str]) -> PrefilterResult:
    """Deterministic niche prefilter (kernel disqualifiers). Reason recorded on fail."""
    domain = normalize_domain(cand.domain)
    if not domain or "." not in domain or " " in domain:
        return PrefilterResult(False, "unresolvable_domain")
    if domain in opt_out_domains:
        return PrefilterResult(False, "opt_out")
    blob = f"{cand.name} {cand.description}".lower()
    if any(k in blob for k in _AGENCY_KW):
        return PrefilterResult(False, "disqualifier_agency")
    if any(k in blob for k in _AI_NATIVE_KW):
        return PrefilterResult(False, "disqualifier_ai_native")
    return PrefilterResult(True)


def discover(sources=None, *, limit: int = 50, persist: bool = True) -> list[Candidate]:
    """Assemble a candidate list from adapters; prefilter; persist survivors."""
    init_db()
    sources = sources or DEFAULT_SOURCES

    with session_scope() as s:
        opt_out_domains = {o.domain for o in s.execute(select(OptOut)).scalars() if o.domain}

    collected: dict[str, Candidate] = {}
    for src in sources:
        try:
            for cand in src.fetch(limit=limit):
                d = normalize_domain(cand.domain)
                if d and d not in collected:
                    cand.domain = d
                    collected[d] = cand
        except Exception as e:  # adapters must never crash discovery
            log.warning("source %s failed: %s", getattr(src, "name", src), e)

    survivors: list[Candidate] = []
    now = datetime.now(UTC)
    for domain, cand in collected.items():
        pf = prefilter(cand, opt_out_domains)
        if persist:
            with session_scope() as s:
                company = s.get(Company, domain)
                if company is None:
                    company = Company(domain=domain, first_seen=now)
                    s.add(company)
                company.name = cand.name
                existing = set((company.sources_seen or "").split(",")) - {""}
                existing.add(cand.source)
                company.sources_seen = ",".join(sorted(existing))
                if not company.description:
                    company.description = cand.description
                company.disqualified_reason = None if pf.ok else pf.reason
        if pf.ok:
            survivors.append(cand)
        else:
            log.info("prefilter dropped %s: %s", domain, pf.reason)

    log.info("discovery: %d collected, %d survivors", len(collected), len(survivors))
    return survivors


def add_manual(domain: str, name: str | None = None, description: str = "") -> Candidate:
    """Manually add an in-niche company (SPEC A2: HN/YC + manual adds)."""
    init_db()
    domain = normalize_domain(domain)
    cand = Candidate(name=name or domain, domain=domain, source="manual", description=description)
    now = datetime.now(UTC)
    with session_scope() as s:
        company = s.get(Company, domain)
        if company is None:
            company = Company(domain=domain, first_seen=now)
            s.add(company)
        company.name = cand.name
        existing = set((company.sources_seen or "").split(",")) - {""}
        existing.add("manual")
        company.sources_seen = ",".join(sorted(existing))
        if description:
            company.description = description
    return cand


def list_candidates(include_disqualified: bool = False) -> list[Company]:
    init_db()
    with session_scope() as s:
        q = select(Company)
        rows = list(s.execute(q).scalars())
        if not include_disqualified:
            rows = [r for r in rows if not r.disqualified_reason]
        # detach: read attrs into simple holders
        return [
            Company(domain=r.domain, name=r.name, description=r.description,
                    sources_seen=r.sources_seen, disqualified_reason=r.disqualified_reason)
            for r in rows
        ]
