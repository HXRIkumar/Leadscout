"""A6 — RAG engine for the support-deflection demo (dependency-free, local-first).

BM25 retrieval over a company's public help/docs pages — no embeddings API, no
torch, honoring the $0-baseline principle (SPEC §4.5). The answer step uses the LLM
router when keys exist, else falls back to extractive answers (top retrieved
passage), so the demo is runnable offline.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


@dataclass
class Chunk:
    text: str
    source_url: str


def chunk_corpus(corpus: dict[str, str], *, target_chars: int = 600) -> list[Chunk]:
    """Split each source's clean text into ~target_chars passages on sentence bounds."""
    chunks: list[Chunk] = []
    for url, text in corpus.items():
        sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
        buf = ""
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            if len(buf) + len(sent) + 1 > target_chars and buf:
                chunks.append(Chunk(buf.strip(), url))
                buf = sent
            else:
                buf = f"{buf} {sent}".strip()
        if buf.strip():
            chunks.append(Chunk(buf.strip(), url))
    return [c for c in chunks if len(c.text) >= 40]


class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.docs = docs
        self.k1 = k1
        self.b = b
        self.N = len(docs)
        self.avgdl = (sum(len(d) for d in docs) / self.N) if self.N else 0.0
        self.tf = [Counter(d) for d in docs]
        df: dict[str, int] = {}
        for d in docs:
            for t in set(d):
                df[t] = df.get(t, 0) + 1
        self.idf = {t: math.log(1 + (self.N - n + 0.5) / (n + 0.5)) for t, n in df.items()}

    def score(self, query_tokens: list[str], i: int) -> float:
        dl = len(self.docs[i])
        s = 0.0
        for t in query_tokens:
            f = self.tf[i].get(t, 0)
            if not f:
                continue
            idf = self.idf.get(t, 0.0)
            s += idf * (f * (self.k1 + 1)) / (f + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1)))
        return s

    def top(self, query: str, n: int = 3) -> list[tuple[int, float]]:
        q = tokenize(query)
        scored = [(i, self.score(q, i)) for i in range(self.N)]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [(i, sc) for i, sc in scored[:n] if sc > 0]


@dataclass
class Answer:
    question: str
    answer: str
    sources: list[str]
    score: float
    deflectable: bool
    source: str = "extractive"  # or "llm"


@dataclass
class RagResult:
    chunks: list[Chunk]
    answers: list[Answer]
    deflection_rate: float           # proxy: share of questions confidently answerable
    questions: list[str] = field(default_factory=list)


# Confidence threshold on BM25 score above which we call a question "deflectable".
_DEFLECT_THRESHOLD = 3.0

_GENERIC_QUESTIONS = [
    "How do I get started?",
    "How do I reset my password?",
    "What are your pricing plans?",
    "How do I contact support?",
    "How do I cancel my subscription?",
    "How do I integrate with my existing tools?",
    "Is my data secure?",
    "How do I invite my team?",
]


def derive_questions(corpus: dict[str, str], *, limit: int = 20) -> list[str]:
    """Real support questions from the docs (sentences ending in '?'), else generic."""
    seen: set[str] = set()
    out: list[str] = []
    for text in corpus.values():
        for m in re.findall(r"[A-Z][^?.!\n]{8,140}\?", text):
            q = re.sub(r"\s+", " ", m).strip()
            key = q.lower()
            if key not in seen:
                seen.add(key)
                out.append(q)
    for g in _GENERIC_QUESTIONS:
        if g.lower() not in seen:
            out.append(g)
            seen.add(g.lower())
    return out[:limit]


def _answer_with_llm(question: str, passages: list[Chunk]) -> str | None:
    from ..config import get_settings
    if not get_settings().has_any_llm():
        return None
    from ..llm import NoLLMAvailable, llm_complete
    ctx = "\n\n".join(f"[{c.source_url}] {c.text}" for c in passages)
    prompt = (
        "Answer the support question using ONLY the context passages below. If the "
        "answer isn't in the context, say you'd route it to a human. Be concise.\n\n"
        f"QUESTION: {question}\n\nCONTEXT:\n{ctx}"
    )
    try:
        # frontier task (demo generation): quality of demo answers is what the prospect
        # sees. Cheap on gpt-5-mini and budget-guarded; falls back to free tier without
        # frontier keys, and to extractive answers with no keys at all.
        return llm_complete(
            prompt, task="demo",
            system="You are a helpful, accurate support assistant. Ground every answer in the provided context.",
        ).text.strip()
    except NoLLMAvailable:
        return None


def build_rag(corpus: dict[str, str], *, questions: list[str] | None = None, use_llm: bool = True) -> RagResult:
    chunks = chunk_corpus(corpus)
    qs = questions or derive_questions(corpus)
    if not chunks:
        return RagResult(chunks=[], answers=[], deflection_rate=0.0, questions=qs)

    bm25 = BM25([tokenize(c.text) for c in chunks])
    answers: list[Answer] = []
    deflectable = 0
    for q in qs:
        hits = bm25.top(q, n=3)
        passages = [chunks[i] for i, _ in hits]
        top_score = hits[0][1] if hits else 0.0
        is_deflect = top_score >= _DEFLECT_THRESHOLD
        if is_deflect:
            deflectable += 1

        ans_text = _answer_with_llm(q, passages) if (use_llm and passages) else None
        source = "llm"
        if ans_text is None:
            source = "extractive"
            ans_text = passages[0].text[:400] if passages else "No relevant help content found — route to a human."

        answers.append(Answer(
            question=q, answer=ans_text, sources=[c.source_url for c in passages],
            score=round(top_score, 2), deflectable=is_deflect, source=source,
        ))

    rate = deflectable / len(qs) if qs else 0.0
    return RagResult(chunks=chunks, answers=answers, deflection_rate=round(rate, 2), questions=qs)
