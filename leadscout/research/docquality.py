"""Documentation-quality scoring (compliant, offline).

For a support-deflection RAG pilot, the amount and structure of a company's PUBLIC
help/docs is the single best predictor of how much a bot can deflect — it's the
training material. This scores the already-fetched doc pages (no new network) into a
0-100 coverage score + band, cited by the doc URLs. Feeds demo feasibility and the
diagnosis's implementation-complexity read.
"""

from __future__ import annotations

from dataclasses import dataclass, field

_DOC_PATHS = ("help", "docs", "support", "faq", "knowledge", "guide", "documentation")


@dataclass
class DocQuality:
    doc_pages: int
    total_chars: int
    score: int            # 0-100
    band: str             # thin | moderate | rich
    sources: list[str] = field(default_factory=list)


def assess_docs(corpus: dict[str, str]) -> DocQuality:
    """Score public documentation coverage from the fetched corpus (help/docs pages)."""
    doc_urls = [u for u in corpus if any(k in u.lower() for k in _DOC_PATHS) and corpus[u]]
    total = sum(len(corpus[u]) for u in doc_urls)
    pages = len(doc_urls)
    # coverage = page breadth (up to 40) + trainable volume (up to 60)
    page_score = min(40, pages * 10)
    vol_score = min(60, total // 500)   # ~1 pt / 500 chars of clean doc text
    score = int(min(100, page_score + vol_score))
    band = "rich" if score >= 70 else "moderate" if score >= 35 else "thin"
    return DocQuality(doc_pages=pages, total_chars=total, score=score, band=band, sources=doc_urls)
