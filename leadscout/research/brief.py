"""Brief composer — the Week-1 deliverable (SPEC §5.2 W1).

`brief <url>` -> evidence-verified diagnosis + costed pain. Every claim carries a
verbatim quote + source URL that fails closed. Persists company, artifacts,
verified signals, and the brief to SQLite, and writes data/companies/<domain>/brief.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from ..db import init_db, session_scope
from ..diagnose import CostEstimate, Diagnosis, diagnose, estimate_cost
from ..kernel import Kernel, load_kernel
from ..logging import RunLog, get_logger
from ..models import Artifact, Brief, Company, Signal
from .extract import SignalCandidate, extract_signals
from .fetch import FetchResult, crawl_company, normalize_domain, page_paths

log = get_logger(__name__)


@dataclass
class BriefResult:
    domain: str
    company_name: str
    brief_path: str
    diagnosis: Diagnosis
    cost: CostEstimate
    signals: list[SignalCandidate]
    pages: list[str] = field(default_factory=list)
    runlog: RunLog | None = None


def _company_name(domain: str, corpus_titles: dict[str, str]) -> str:
    # crude: derive from domain; refined naming is A3 future work
    core = domain.split(".")[0]
    return core.capitalize()


def build_brief(url: str, *, use_cache: bool = True, use_llm: bool = True, kernel: Kernel | None = None) -> BriefResult:
    init_db()
    kernel = kernel or load_kernel()
    domain = normalize_domain(url)
    runlog = RunLog(run=f"brief_{domain}")

    # 1) research: polite crawl
    results: list[FetchResult] = crawl_company(domain, use_cache=use_cache)
    runlog.pages_fetched = sum(1 for r in results if not r.from_cache)
    runlog.pages_from_cache = sum(1 for r in results if r.from_cache)
    if not results:
        runlog.error("no pages fetched (site unreachable, blocked, or JS-only)")

    corpus: dict[str, str] = {r.url: r.clean_text for r in results if r.clean_text}

    # 2) extract + verify signals (fail-closed)
    signals = extract_signals(corpus, kernel, runlog, prefer_llm=use_llm)

    # 3) diagnose (A4)
    company_name = _company_name(domain, {})
    dx = diagnose(signals, kernel, company_name=company_name, use_llm=use_llm)

    # 4) cost-of-problem (A5)
    cost = estimate_cost(signals, kernel)

    # 5) compose markdown
    md = _compose_markdown(domain, company_name, kernel, dx, cost, signals, list(corpus.keys()), runlog)
    from ..config import get_settings
    brief_path = get_settings().data_path / "companies" / domain / "brief.md"
    brief_path.parent.mkdir(parents=True, exist_ok=True)
    brief_path.write_text(md, encoding="utf-8")

    # 6) persist
    _persist(domain, company_name, kernel, dx, cost, signals, results, str(brief_path))

    runlog.write()
    return BriefResult(
        domain=domain, company_name=company_name, brief_path=str(brief_path),
        diagnosis=dx, cost=cost, signals=signals, pages=list(corpus.keys()), runlog=runlog,
    )


def _persist(domain, company_name, kernel, dx, cost, signals, results, brief_path) -> None:
    now = datetime.now(UTC)
    with session_scope() as s:
        company = s.get(Company, domain)
        if company is None:
            company = Company(domain=domain, first_seen=now)
            s.add(company)
        company.name = company_name
        company.last_crawled = now
        company.disqualified_reason = dx.disqualify_reason or None
        sources = ",".join(sorted({"site"}))
        company.sources_seen = sources

        # artifacts (idempotent-ish: replace by url within this run is overkill; add fresh)
        existing_urls = {a.url for a in s.query(Artifact).filter(Artifact.domain == domain).all()}
        for r in results:
            if r.url in existing_urls:
                continue
            raw_p, txt_p = page_paths(r.url)
            s.add(Artifact(domain=domain, source="site", url=r.url,
                           raw_path=str(raw_p), clean_text_path=str(txt_p), fetched_at=now))

        # signals: clear prior signals for this domain and rewrite verified set
        for old in s.query(Signal).filter(Signal.domain == domain).all():
            s.delete(old)
        for sig in signals:
            s.add(Signal(
                domain=domain, signal_type=sig.signal_type, evidence_quote=sig.evidence_quote,
                source_url=sig.source_url, confidence=sig.confidence,
                mapped_project=sig.mapped_project, extracted_at=now,
            ))

        # brief row
        s.add(Brief(
            domain=domain, bottleneck=dx.bottleneck, wedge=dx.wedge,
            cost_estimate=cost.headline, readiness_qualitative=dx.readiness_qualitative,
            brief_path=brief_path, created_at=now,
        ))


def _compose_markdown(domain, company_name, kernel, dx, cost, signals, pages, runlog) -> str:
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    positives = [s for s in signals if not s.is_anti_signal]
    anti = [s for s in signals if s.is_anti_signal]

    lines: list[str] = []
    lines.append(f"# Brief — {company_name} (`{domain}`)")
    lines.append("")
    lines.append(f"*Generated {today} · LeadScout v2 · niche: support-deflection · "
                 f"offer: {kernel.offer.headline_number}, {kernel.offer.pilot.price}/{kernel.offer.pilot.weeks}wk*")
    lines.append("")

    if dx.disqualified:
        lines.append("## ⛔ Disqualified")
        lines.append("")
        lines.append(f"> **{dx.disqualify_reason}**")
        lines.append("")
        lines.append(dx.bottleneck)
        lines.append("")

    lines.append("## Diagnosis")
    lines.append("")
    lines.append(f"**Bottleneck.** {dx.bottleneck}")
    lines.append("")
    lines.append(f"**Wedge.** {dx.wedge}")
    lines.append("")
    lines.append(f"**AI-readiness (qualitative).** `{dx.readiness_qualitative}` — {dx.readiness_reason}")
    lines.append("")
    lines.append(f"*Diagnosis confidence: {dx.confidence:.0%} · source: {dx.source}*")
    lines.append("")

    lines.append("## Cost of the problem")
    lines.append("")
    lines.append(f"**{cost.headline}**")
    lines.append("")
    lines.append(f"- Method: {cost.method}")
    if cost.evidence:
        for e in cost.evidence:
            lines.append(f"- Headcount evidence: “{e['quote']}” — <{e['source_url']}>")
    lines.append("")

    if dx.matched_patterns:
        lines.append("## Matched pain patterns")
        lines.append("")
        for p in dx.matched_patterns:
            lines.append(f"- `{p['id']}` — {p['name']} (confidence {p['confidence']:.0%})")
        lines.append("")

    lines.append("## Evidence (every claim is verbatim-verified)")
    lines.append("")
    if positives:
        for s in positives:
            lines.append(f"- **{s.signal_type}** ({s.confidence:.0%}): “{s.evidence_quote}”")
            lines.append(f"  <br>↳ source: <{s.source_url}>")
    else:
        lines.append("_No positive support-deflection signals passed verification._")
    lines.append("")

    if anti:
        lines.append("### Anti-signals (toward disqualification)")
        lines.append("")
        for s in anti:
            lines.append(f"- **{s.signal_type}**: “{s.evidence_quote}” — <{s.source_url}>")
        lines.append("")

    lines.append("## Sources fetched")
    lines.append("")
    for u in pages:
        lines.append(f"- <{u}>")
    if not pages:
        lines.append("_No sources fetched._")
    lines.append("")

    lines.append("---")
    lines.append(
        f"*Fail-closed evidence: {runlog.signals_extracted} claim(s) verified, "
        f"{runlog.signals_rejected_unverified} rejected as unverifiable. "
        f"Pages: {len(pages)} used. No claim without a verbatim quote + source URL.*"
    )
    lines.append("")
    return "\n".join(lines)
