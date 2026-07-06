"""Signal extraction (SPEC §9, A3).

Two extractors behind one interface:
- HeuristicExtractor: no LLM. Keyword-anchored sentence matching. Its evidence
  quotes are literal substrings of the fetched text, so they always verify —
  this is what makes `brief <url>` work fully offline with zero API keys.
- LLMExtractor: Groq/Gemini via the router with a rubric prompt; higher recall.

Both produce SignalCandidates; `verify_signals()` drops anything whose quote is
not verbatim in the fetched text (SPEC §4.1, fail-closed).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache

from ..kernel import Kernel
from ..logging import RunLog, get_logger
from .verify import normalize_ws, verify_quote

log = get_logger(__name__)

RAG = "rag_support_bot"

# signal_type -> (keywords, mapped_project, base_confidence, is_anti_signal)
SIGNAL_RULES: list[tuple[str, list[str], str | None, float, bool]] = [
    ("support_hiring", [
        "support engineer", "customer support specialist", "support specialist",
        "customer success manager", "customer success", "technical support",
        "support representative", "support agent", "head of support", "support team",
        "customer experience", "cx team",
    ], RAG, 0.7, False),
    ("help_center", [
        "help center", "help centre", "knowledge base", "support center",
        "browse articles", "find answers", "help articles", "documentation portal",
    ], RAG, 0.7, False),
    ("support_complaints", [
        "slow response", "waiting for support", "no response from support",
        "poor support", "support is slow", "slow to respond", "response time",
    ], RAG, 0.75, False),
    ("support_widget", [
        "intercom", "zendesk", "gorgias", "help scout", "freshdesk", "front app",
    ], RAG, 0.6, False),
    ("growth_pressure", [
        "fastest growing", "rapidly growing", "growing customer base",
        "scaling quickly", "thousands of customers", "onboarding new customers",
        "millions of users",
    ], RAG, 0.5, False),
    ("community_gap", [
        "community forum", "discourse", "ask the community", "community support",
    ], RAG, 0.5, False),
    ("docs_lagging", [
        "changelog", "release notes", "product updates", "what's new",
    ], RAG, 0.4, False),
    ("funding_event", [
        "raised funding", "raised a round", "series a funding", "seed round",
        "seed funding", "million in funding", "backed by", "venture funding",
        "closed our round", "our funding round",
    ], None, 0.4, False),
    # anti-signals -> feed disqualification
    ("ai_native", [
        "ai-powered", "powered by ai", "large language model", "our ai agent",
        "generative ai", "ai copilot", "built on gpt", "llm-powered",
    ], None, 0.6, True),
    ("agency", [
        "we build software for", "development agency", "software agency",
        "digital agency", "software consultancy", "we help companies build",
        "dev shop", "we are an agency", "we're an agency", "for our clients",
    ], None, 0.6, True),
]


@dataclass
class SignalCandidate:
    signal_type: str
    evidence_quote: str
    source_url: str
    confidence: float
    mapped_project: str | None = None
    recency_days: int | None = None
    is_anti_signal: bool = False
    meta: dict = field(default_factory=dict)


@lru_cache(maxsize=1024)
def _kw_pattern(kw: str) -> re.Pattern:
    """Word-boundary matcher so 'our clients' never matches inside 'your clients'."""
    return re.compile(r"\b" + re.escape(kw) + r"\b")


def _kw_hits(keywords: list[str], text_low: str) -> list[str]:
    return [k for k in keywords if _kw_pattern(k).search(text_low)]


def split_sentences(text: str) -> list[str]:
    # split on sentence enders and newlines/bullets; keep chunks of reasonable length
    parts = re.split(r"(?<=[.!?])\s+|\n+|•|·|•", text)
    out = []
    for p in parts:
        p = p.strip()
        if 12 <= len(p) <= 400:
            out.append(p)
    return out


class HeuristicExtractor:
    """Deterministic, offline. Every quote is a literal substring -> always verifies."""

    def extract(self, corpus: dict[str, str]) -> list[SignalCandidate]:
        candidates: list[SignalCandidate] = []
        seen: set[tuple[str, str]] = set()
        per_type_count: dict[str, int] = {}
        for url, text in corpus.items():
            for sentence in split_sentences(text):
                low = sentence.lower()
                for stype, keywords, mapped, base_conf, is_anti in SIGNAL_RULES:
                    hits = _kw_hits(keywords, low)
                    if not hits:
                        continue
                    if per_type_count.get(stype, 0) >= 3:
                        continue
                    key = (stype, normalize_ws(sentence)[:120])
                    if key in seen:
                        continue
                    seen.add(key)
                    per_type_count[stype] = per_type_count.get(stype, 0) + 1
                    conf = min(0.9, base_conf + 0.05 * (len(hits) - 1))
                    candidates.append(SignalCandidate(
                        signal_type=stype,
                        evidence_quote=sentence,
                        source_url=url,
                        confidence=round(conf, 2),
                        mapped_project=mapped,
                        is_anti_signal=is_anti,
                    ))
        return candidates


class LLMExtractor:
    """Higher-recall extraction via the LLM router. Output is still verified."""

    def extract(self, corpus: dict[str, str], kernel: Kernel) -> list[SignalCandidate]:
        from ..llm import NoLLMAvailable, llm_complete  # lazy import
        from ..prompts import load_prompt

        system = load_prompt("researcher")
        # keep prompt bounded; concatenate sources with URL markers
        blocks = []
        for url, text in corpus.items():
            blocks.append(f"### SOURCE: {url}\n{text[:6000]}")
        corpus_text = "\n\n".join(blocks)[:24000]
        signal_types = [r[0] for r in SIGNAL_RULES]
        prompt = (
            f"NICHE PROBLEM: {kernel.problem.name}\n"
            f"Allowed signal_type values: {', '.join(signal_types)}\n\n"
            "From the SOURCES below, extract company facts and signals relevant to the niche. "
            "Return STRICT JSON: {\"signals\": [{\"signal_type\": ..., \"evidence_quote\": "
            "\"verbatim substring copied EXACTLY from a source\", \"source_url\": ..., "
            "\"confidence\": 0.0-1.0}]}. The evidence_quote MUST be an exact substring of the "
            "source text — do not paraphrase. Return an empty list if nothing qualifies.\n\n"
            f"SOURCES:\n{corpus_text}"
        )
        try:
            result = llm_complete(prompt, task="extraction", system=system, json_mode=True)
        except NoLLMAvailable:
            return []

        candidates: list[SignalCandidate] = []
        for sig in _parse_signals_json(result.text):
            stype = sig.get("signal_type", "").strip()
            rule = next((r for r in SIGNAL_RULES if r[0] == stype), None)
            candidates.append(SignalCandidate(
                signal_type=stype or "other",
                evidence_quote=sig.get("evidence_quote", ""),
                source_url=sig.get("source_url", ""),
                confidence=float(sig.get("confidence", 0.6) or 0.6),
                mapped_project=(rule[2] if rule else None),
                is_anti_signal=(rule[4] if rule else False),
            ))
        return candidates


def _parse_signals_json(text: str) -> list[dict]:
    text = text.strip()
    # tolerate code fences
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", text).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # try to locate the first {...} object
        m = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not m:
            return []
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return []
    sigs = data.get("signals", []) if isinstance(data, dict) else []
    return [s for s in sigs if isinstance(s, dict)]


# Disqualifying keywords per anti-signal type — used to gate LLM classifications.
_ANTI_KEYWORDS: dict[str, list[str]] = {r[0]: r[1] for r in SIGNAL_RULES if r[4]}


def anti_signal_confirmed(signal_type: str, quote: str) -> bool:
    """An anti-signal (ai_native/agency) is trusted only if its own quote contains a
    real disqualifying keyword. Prevents an LLM mislabel (e.g. tagging an "open source"
    quote as ai_native) from wrongly disqualifying a prospect — "evidence or it didn't
    happen" applied to the *classification*, not just the quote's existence.
    """
    kws = _ANTI_KEYWORDS.get(signal_type)
    if not kws:
        return True  # not an anti-signal we gate
    return bool(_kw_hits(kws, quote.lower()))


def verify_signals(
    candidates: list[SignalCandidate], corpus: dict[str, str], runlog: RunLog | None = None
) -> list[SignalCandidate]:
    """Drop any candidate whose quote is not verbatim in the corpus (fail-closed),
    and any anti-signal whose quote doesn't contain a real disqualifying keyword."""
    verified: list[SignalCandidate] = []
    for c in candidates:
        vr = verify_quote(c.evidence_quote, c.source_url, corpus)
        if not vr.ok:
            log.info("dropped unverified signal (%s): %s", vr.reason, c.evidence_quote[:80])
            if runlog:
                runlog.signals_rejected_unverified += 1
            continue
        if c.is_anti_signal and not anti_signal_confirmed(c.signal_type, c.evidence_quote):
            log.info("dropped mislabeled anti-signal (%s, no keyword): %s",
                     c.signal_type, c.evidence_quote[:80])
            if runlog:
                runlog.signals_rejected_unverified += 1
            continue
        if vr.source_url and vr.source_url != c.source_url:
            c.source_url = vr.source_url
        verified.append(c)
        if runlog:
            runlog.signals_extracted += 1
    verified.sort(key=lambda s: s.confidence, reverse=True)
    return verified


def extract_signals(
    corpus: dict[str, str], kernel: Kernel, runlog: RunLog | None = None, *, prefer_llm: bool = True
) -> list[SignalCandidate]:
    """Extract + verify signals. LLM if available, else/also heuristic backfill."""
    from ..config import get_settings

    candidates: list[SignalCandidate] = []
    used_llm = False
    if prefer_llm and get_settings().has_any_llm():
        candidates = LLMExtractor().extract(corpus, kernel)
        used_llm = bool(candidates)

    verified = verify_signals(candidates, corpus, runlog)

    # Heuristic backfill: always run when LLM produced nothing verified, or wasn't used.
    if not verified:
        heur = HeuristicExtractor().extract(corpus)
        verified = verify_signals(heur, corpus, runlog)
        if runlog and used_llm:
            runlog.note("LLM yielded no verified signals; used heuristic backfill")
    return verified
