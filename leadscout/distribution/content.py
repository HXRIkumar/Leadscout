"""A9 — Content Engine Lite (repurposer, SPEC §3.1 A9).

Turn each (REDACTED) brief/demo into 1-2 niche posts for X/LinkedIn and log the
posting cadence. Marginal cost is near zero because the artifacts already exist.
Reputation is this segment's inbound engine and the Phase 5-6 distribution asset.

Redaction is deliberate: posts talk about the *pattern* and the *numbers*, never
the company (that stays private until they're a public case study, B3).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select

from ..config import get_settings
from ..db import init_db, session_scope
from ..kernel import load_kernel
from ..logging import get_logger
from ..models import Brief, Demo

log = get_logger(__name__)


@dataclass
class ContentResult:
    posts: list[str]
    log_path: str


class NoBriefError(RuntimeError):
    pass


def _generalize(bottleneck: str | None) -> str:
    b = (bottleneck or "repetitive support questions pile up faster than a small team can answer them").strip().rstrip(".")
    # strip the leading "Support load is rising: " scaffold for a cleaner post
    b = b.replace("Support load is rising: ", "")
    return b


def repurpose_brief(domain: str, *, use_llm: bool = True) -> ContentResult:
    """Generate 1-2 redacted niche posts from a company's brief (+ demo if present)."""
    init_db()
    kernel = load_kernel()
    with session_scope() as s:
        brief = s.query(Brief).filter(Brief.domain == domain).order_by(Brief.id.desc()).first()
        if brief is None:
            raise NoBriefError(f"No brief for {domain}. Run `leadscout brief {domain}` first.")
        bottleneck = brief.bottleneck
        demo = s.execute(
            select(Demo).where(Demo.domain == domain).order_by(Demo.id.desc())
        ).scalars().first()
        rate = demo.deflection_rate if demo else None

    pattern = _generalize(bottleneck)
    headline = kernel.offer.headline_number

    insight = (
        f"Most B2B SaaS teams I dig into have the same quiet problem: {pattern}.\n\n"
        f"The fix usually isn't another support hire — it's deflecting the repetitive tier "
        f"before it ever reaches a human. Done right that's {headline}, and the content to "
        f"train on already exists in their own help center.\n\n"
        f"Support scales with customers. Deflection scales with docs."
    )

    rate_txt = f"~{rate*100:.0f}% of their top questions" if rate is not None else "a big chunk of the repetitive tier"
    build = (
        f"Spent an evening building a support-deflection bot trained ONLY on a company's public "
        f"help docs — no access to anything private.\n\n"
        f"On {rate_txt} it answered straight from their own documentation, with sources.\n\n"
        f"A working artifact beats a pitch deck every time. If you run support at a growing SaaS, "
        f"this is buildable in days, not quarters."
    )

    posts = [insight, build]
    if use_llm:
        posts = [_llm_polish(p) or p for p in posts]

    # cadence log
    log_dir = get_settings().data_path / "content"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "posting_log.md"
    stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"\n## {stamp} — from brief `{domain}` (redacted)\n\n")
        for i, p in enumerate(posts, 1):
            f.write(f"### Draft {i}\n\n{p}\n\n")

    return ContentResult(posts=posts, log_path=str(log_path))


def _llm_polish(post: str) -> str | None:
    from ..config import get_settings
    if not get_settings().has_any_llm():
        return None
    from ..llm import NoLLMAvailable, llm_complete
    prompt = (
        "Rewrite this into one punchy LinkedIn/X post for a technical-founder audience. "
        "Keep it specific and non-salesy, keep any numbers, no hashtags, no company names, "
        "no invented facts. Return only the post.\n\n" + post
    )
    try:
        # content polish runs on the free tier ($0 marginal), not frontier
        return llm_complete(prompt, task="extraction",
                            system="You write sharp, credible, non-hypey posts for a technical audience.").text.strip()
    except NoLLMAvailable:
        return None
