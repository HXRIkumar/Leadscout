"""Evidence verification — the anti-hallucination rule (SPEC §4.1, §9).

> Every factual claim carries a verbatim quote + source URL, programmatically
> verified against fetched text; failures are dropped and logged.

This is the single rule that makes the whole system trustworthy. It FAILS CLOSED:
a quote that cannot be found verbatim (whitespace-normalized) in the fetched text
is rejected — never surfaced. Applies identically to heuristic and LLM output.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

MIN_QUOTE_CHARS = 12  # reject trivially-short "quotes" that match by accident


def normalize_ws(text: str) -> str:
    """Whitespace-normalized form used for verbatim matching."""
    return re.sub(r"\s+", " ", text or "").strip()


@dataclass
class VerificationResult:
    ok: bool
    source_url: str | None = None  # corrected URL if re-attributed
    reason: str = ""


def verify_quote(quote: str, claimed_url: str, corpus: dict[str, str]) -> VerificationResult:
    """Verify a quote against the corpus of {source_url: clean_text} actually fetched.

    - Pass if the quote appears verbatim in the claimed source's text.
    - If the quote is genuine but attributed to the wrong fetched URL, re-attribute
      (the evidence is real, only the citation was off) — still not a fabrication.
    - Fail closed otherwise.
    """
    q = normalize_ws(quote)
    if len(q) < MIN_QUOTE_CHARS:
        return VerificationResult(False, reason="quote_too_short")

    # 1) claimed source
    claimed_text = corpus.get(claimed_url)
    if claimed_text is not None and q in normalize_ws(claimed_text):
        return VerificationResult(True, source_url=claimed_url)

    # 2) re-attribution: genuine quote, wrong URL
    for url, text in corpus.items():
        if q in normalize_ws(text):
            return VerificationResult(True, source_url=url, reason="reattributed")

    # 3) not found anywhere -> fabricated / paraphrased -> drop
    if claimed_url not in corpus:
        return VerificationResult(False, reason="url_not_in_corpus")
    return VerificationResult(False, reason="quote_not_found")


def find_verbatim(needle: str, corpus: dict[str, str]) -> str | None:
    """Return the source_url whose text contains `needle` verbatim, else None."""
    n = normalize_ws(needle)
    if len(n) < MIN_QUOTE_CHARS:
        return None
    for url, text in corpus.items():
        if n in normalize_ws(text):
            return url
    return None
