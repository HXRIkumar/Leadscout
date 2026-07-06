"""Brief composer — the Week-1 deliverable (SPEC §5.2 W1).

`brief <url>` -> evidence-verified diagnosis + costed pain. Every claim carries a
verbatim quote + source URL that fails closed. Persists company, artifacts,
verified signals, and the brief to SQLite, and writes data/companies/<domain>/brief.md.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime

from ..db import init_db, session_scope
from ..diagnose import CostEstimate, Diagnosis, diagnose, estimate_cost
from ..intelligence.scorer import ScoreResult, opportunity_score
from ..kernel import Kernel, load_kernel
from ..logging import RunLog, get_logger
from ..models import Artifact, Brief, Company, Score, Signal
from .docquality import DocQuality, assess_docs
from .extract import SignalCandidate, extract_signals, verify_signals
from .fetch import FetchResult, crawl_company, normalize_domain, page_paths
from .github import GitHubProfile
from .github import enrich as enrich_github
from .links import research_links
from .techstack import detect_widgets

log = get_logger(__name__)


@dataclass
class BriefResult:
    domain: str
    company_name: str
    brief_path: str
    diagnosis: Diagnosis
    cost: CostEstimate
    signals: list[SignalCandidate]
    score: ScoreResult | None = None
    doc_quality: DocQuality | None = None
    github: GitHubProfile | None = None
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

    # 2b) tech-stack detection from raw HTML (compliant; verified against the HTML)
    html_corpus = {r.url: r.html for r in results if r.html}
    widget_signals = verify_signals(detect_widgets(results), html_corpus, runlog)
    seen = {(s.signal_type, s.evidence_quote) for s in signals}
    for w in widget_signals:
        if (w.signal_type, w.evidence_quote) not in seen:
            signals.append(w)
    signals.sort(key=lambda s: s.confidence, reverse=True)

    # 3) cost-of-problem (A5) — computed first so the diagnosis can cite ROI
    cost = estimate_cost(signals, kernel)

    # 4) diagnose (A4) — consultant-grade, grounded in verified signals + cost
    company_name = _company_name(domain, {})
    dx = diagnose(signals, kernel, company_name=company_name, cost=cost, use_llm=use_llm)

    # 5) opportunity score (explainable, deterministic) for triage/ranking
    score = opportunity_score(signals, kernel.offer.archetype, disqualified=dx.disqualified)

    # 5b) documentation coverage (RAG deflection potential), from fetched docs
    doc_quality = assess_docs(corpus)

    # 5c) GitHub engineering-context enrichment (compliant official API; facts-only)
    from ..config import get_settings as _gs
    github = enrich_github(domain, company_name) if _gs().github_enrichment else None

    # 6) compose markdown
    md = _compose_markdown(domain, company_name, kernel, dx, cost, score, doc_quality, github,
                           signals, list(corpus.keys()), runlog)
    from ..config import get_settings
    brief_path = get_settings().data_path / "companies" / domain / "brief.md"
    brief_path.parent.mkdir(parents=True, exist_ok=True)
    brief_path.write_text(md, encoding="utf-8")

    # 7) persist
    _persist(domain, company_name, kernel, dx, cost, score, signals, results, str(brief_path))

    runlog.write()
    return BriefResult(
        domain=domain, company_name=company_name, brief_path=str(brief_path),
        diagnosis=dx, cost=cost, signals=signals, score=score, doc_quality=doc_quality,
        github=github, pages=list(corpus.keys()), runlog=runlog,
    )


def _persist(domain, company_name, kernel, dx, cost, score, signals, results, brief_path) -> None:
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

        # scores: keep one latest opportunity score per domain (for ranking)
        for old_sc in s.query(Score).filter(Score.domain == domain).all():
            s.delete(old_sc)
        s.add(Score(domain=domain, total=score.total,
                    factor_breakdown=json.dumps(score.factor_breakdown),
                    estimated_value_band=score.estimated_value_band, scored_at=now))

        # signals: clear prior signals for this domain and rewrite verified set
        for old in s.query(Signal).filter(Signal.domain == domain).all():
            s.delete(old)
        for sig in signals:
            s.add(Signal(
                domain=domain, signal_type=sig.signal_type, evidence_quote=sig.evidence_quote,
                source_url=sig.source_url, confidence=sig.confidence,
                mapped_project=sig.mapped_project, verification=sig.verification, extracted_at=now,
            ))

        # brief row
        s.add(Brief(
            domain=domain, bottleneck=dx.bottleneck, wedge=dx.wedge,
            cost_estimate=cost.headline, readiness_qualitative=dx.readiness_qualitative,
            brief_path=brief_path, created_at=now,
        ))


def _compose_markdown(domain, company_name, kernel, dx, cost, score, doc_quality, github, signals, pages, runlog) -> str:
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

    if not dx.disqualified and dx.business_summary:
        lines.append("## Consultant analysis")
        lines.append("")
        lines.append(f"**Business summary.** {dx.business_summary}")
        lines.append("")
        if dx.pain_points:
            lines.append("**Pain points.**")
            lines += [f"- {p}" for p in dx.pain_points]
            lines.append("")
        if dx.ai_opportunities:
            lines.append("**AI opportunities.**")
            lines += [f"- {p}" for p in dx.ai_opportunities]
            lines.append("")
        if dx.automation_opportunities:
            lines.append("**Automation opportunities.**")
            lines += [f"- {p}" for p in dx.automation_opportunities]
            lines.append("")
        lines.append(f"**Recommended project.** `{dx.recommended_project}` · "
                     f"**Implementation complexity:** {dx.implementation_complexity}")
        lines.append("")
        lines.append(f"**Estimated ROI.** {dx.estimated_roi}")
        lines.append("")
        lines.append(f"**Outreach angle.** {dx.outreach_angle}")
        lines.append("")
        if dx.proposal_outline:
            lines.append("**Proposal outline.**")
            lines += [f"{i}. {p}" for i, p in enumerate(dx.proposal_outline, 1)]
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

    lines.append("## Opportunity score")
    lines.append("")
    band = f" · value band {score.estimated_value_band}" if score.estimated_value_band else ""
    lines.append(f"**{score.total}/100**{band}")
    if score.factor_breakdown:
        lines.append("")
        lines.append("- Factors: " + " · ".join(f"{k} {v:g}" for k, v in score.factor_breakdown.items()))
    lines.append("")

    lines.append("## Documentation coverage")
    lines.append("")
    lines.append(f"**{doc_quality.score}/100 ({doc_quality.band})** — {doc_quality.doc_pages} "
                 f"help/doc page(s), ~{doc_quality.total_chars:,} chars of trainable content "
                 f"(RAG deflection potential).")
    if doc_quality.sources:
        lines.append("")
        for u in doc_quality.sources[:6]:
            lines.append(f"- <{u}>")
    lines.append("")

    if github:
        lines.append("## Engineering (GitHub)")
        lines.append("")
        langs = ", ".join(github.top_languages) or "n/a"
        lines.append(
            f"**github.com/{github.login}** — {github.public_repos} public repos; "
            f"top languages: {langs}; ML/AI repos: {'yes' if github.has_ml_ai_repos else 'no'}; "
            f"recently active: {'yes' if github.recently_active else 'no'}."
        )
        lines.append(f"  <br>↳ source: <{github.url}>")
        if github.has_ml_ai_repos and github.ml_evidence:
            lines.append(f"  <br>↳ ML/AI repo: <{github.ml_evidence}>")
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
            v = f" · ✓ {s.verification}" if s.verification else ""
            lines.append(f"- **{s.signal_type}** ({s.confidence:.0%}{v}): “{s.evidence_quote}”")
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

    lines.append("## Manual research (decision makers + restricted sources)")
    lines.append("")
    lines.append("_Open in a browser — compliant manual research only; LeadScout never "
                 "scrapes these sources (SPEC §3.5/§7.7, decision D8)._")
    lines.append("")
    for label, url in research_links(domain, company_name).items():
        lines.append(f"- [{label}]({url})")
    lines.append("")

    lines.append("---")
    lines.append(
        f"*Fail-closed evidence: {runlog.signals_extracted} claim(s) verified, "
        f"{runlog.signals_rejected_unverified} rejected as unverifiable. "
        f"Pages: {len(pages)} used. No claim without a verbatim quote + source URL.*"
    )
    lines.append("")
    return "\n".join(lines)
