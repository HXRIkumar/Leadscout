"""A6 — Micro-Demo Generator (the engineering centerpiece).

brief/company in -> a working, tailored support-deflection artifact out: a RAG bot
trained on the company's PUBLIC help center + docs, answering their real questions,
plus an auto-drafted Loom script. Emits a self-contained, runnable demo folder under
data/companies/<domain>/demo/. A human reviews everything before it's sent (SPEC A6).

Zero-setup: the emitted answer.py is dependency-free (stdlib BM25) and runs offline.
The richer LLM answers (when keys exist) are precomputed into questions.json.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from ..config import get_settings
from ..db import init_db, session_scope
from ..logging import get_logger
from ..models import Brief, Demo
from ..research.fetch import crawl_company, normalize_domain
from .rag import RagResult, build_rag

log = get_logger(__name__)

_KB_PATHS = ("help", "docs", "support", "faq", "knowledge", "guide")


@dataclass
class DemoResult:
    domain: str
    demo_path: str
    deflection_rate: float
    n_questions: int
    n_chunks: int
    template_family: str
    rag: RagResult


def _knowledge_corpus(domain: str, use_cache: bool) -> dict[str, str]:
    results = crawl_company(domain, use_cache=use_cache)
    kb = {r.url: r.clean_text for r in results if any(k in r.url.lower() for k in _KB_PATHS) and r.clean_text}
    if not kb:  # fall back to all fetched pages if no obvious help/docs surface
        kb = {r.url: r.clean_text for r in results if r.clean_text}
    return kb


def scaffold_demo(
    domain: str,
    *,
    template_family: str = "rag_support_bot",
    corpus: dict[str, str] | None = None,
    questions: list[str] | None = None,
    use_cache: bool = True,
    use_llm: bool = True,
) -> DemoResult:
    init_db()
    domain = normalize_domain(domain)
    corpus = corpus if corpus is not None else _knowledge_corpus(domain, use_cache)
    rag = build_rag(corpus, questions=questions, use_llm=use_llm)

    demo_dir = get_settings().data_path / "companies" / domain / "demo"
    demo_dir.mkdir(parents=True, exist_ok=True)

    # 1) knowledge base (the demo's retrieval corpus)
    kb = [{"text": c.text, "source_url": c.source_url} for c in rag.chunks]
    (demo_dir / "knowledge_base.json").write_text(json.dumps(kb, indent=2), encoding="utf-8")

    # 2) questions + answers (precomputed, incl. LLM answers when available)
    qa = [{
        "question": a.question, "answer": a.answer, "sources": a.sources,
        "score": a.score, "deflectable": a.deflectable, "answer_source": a.source,
    } for a in rag.answers]
    (demo_dir / "questions.json").write_text(json.dumps(qa, indent=2), encoding="utf-8")

    # 3) self-contained runnable bot
    (demo_dir / "answer.py").write_text(_ANSWER_PY, encoding="utf-8")

    # 4) Loom walkthrough script + README
    loom_path = demo_dir / "loom_script.md"
    loom_path.write_text(_loom_script(domain, rag, template_family), encoding="utf-8")
    (demo_dir / "README.md").write_text(_readme(domain, rag), encoding="utf-8")

    # 5) persist
    with session_scope() as s:
        brief = s.query(Brief).filter(Brief.domain == domain).order_by(Brief.id.desc()).first()
        s.add(Demo(
            brief_id=brief.id if brief else None, domain=domain, template_family=template_family,
            demo_path=str(demo_dir), loom_script_path=str(loom_path),
            deflection_rate=rag.deflection_rate, status="scaffolded",
        ))

    log.info("demo scaffolded for %s: %d chunks, %d questions, %.0f%% coverage",
             domain, len(rag.chunks), len(rag.answers), rag.deflection_rate * 100)
    return DemoResult(
        domain=domain, demo_path=str(demo_dir), deflection_rate=rag.deflection_rate,
        n_questions=len(rag.answers), n_chunks=len(rag.chunks), template_family=template_family, rag=rag,
    )


def _loom_script(domain: str, rag: RagResult, family: str) -> str:
    examples = [a for a in rag.answers if a.deflectable][:3]
    lines = [
        f"# Loom walkthrough — {domain} support-deflection demo",
        "",
        "> Auto-drafted. Review + edit before recording. ~90 seconds.",
        "",
        "## Beat 1 — the problem (0:00-0:20)",
        f"\"I noticed {domain} is fielding a lot of repetitive support questions. "
        "I built you something over the weekend — a bot trained on your own help docs.\"",
        "",
        "## Beat 2 — the demo (0:20-1:00)",
        f"\"It's trained purely on your public docs — {len(rag.chunks)} passages. "
        "Watch it answer your real questions:\"",
        "",
    ]
    for a in examples:
        lines.append(f"- Ask: *{a.question}*")
        lines.append(f"  → it answers from {a.sources[0] if a.sources else 'your docs'}")
    lines += [
        "",
        "## Beat 3 — the number (1:00-1:20)",
        f"\"On your top {len(rag.answers)} questions it confidently handles "
        f"~{rag.deflection_rate*100:.0f}% — that's support load off your team's plate.\"",
        "",
        "## Beat 4 — the ask (1:20-1:30)",
        "\"If useful, I'd run a 3-week pilot to wire this into your real help widget "
        "and measure deflection on live tickets. Worth a quick call?\"",
        "",
    ]
    return "\n".join(lines)


def _readme(domain: str, rag: RagResult) -> str:
    return "\n".join([
        f"# Support-deflection demo — {domain}",
        "",
        f"Trained on **{len(rag.chunks)} passages** from {domain}'s public help/docs.",
        f"Confident coverage on **{rag.deflection_rate*100:.0f}%** of the "
        f"{len(rag.answers)} tested questions (BM25 proxy; live-ticket deflection is "
        "what the pilot measures).",
        "",
        "## Run it (zero setup)",
        "```bash",
        "python answer.py \"How do I get started?\"",
        "```",
        "",
        "Files: `knowledge_base.json` (retrieval corpus), `questions.json` "
        "(precomputed Q&A incl. LLM answers if keys were set), `answer.py` "
        "(standalone bot), `loom_script.md` (walkthrough).",
        "",
        "> Built only from public data. A human reviews before anything is sent.",
        "",
    ])


# Self-contained, dependency-free bot the prospect can run anywhere.
_ANSWER_PY = '''#!/usr/bin/env python3
"""Standalone support-deflection bot (BM25 over knowledge_base.json). Zero deps.

Usage:  python answer.py "How do I reset my password?"
"""
import json, math, re, sys
from collections import Counter
from pathlib import Path

KB = json.loads((Path(__file__).parent / "knowledge_base.json").read_text(encoding="utf-8"))


def tok(t):
    return re.findall(r"[a-z0-9]+", t.lower())


docs = [tok(c["text"]) for c in KB]
N = len(docs) or 1
avgdl = sum(len(d) for d in docs) / N
df = {}
for d in docs:
    for w in set(d):
        df[w] = df.get(w, 0) + 1
idf = {w: math.log(1 + (N - n + 0.5) / (n + 0.5)) for w, n in df.items()}
tf = [Counter(d) for d in docs]


def score(q, i):
    dl = len(docs[i]); s = 0.0
    for w in q:
        f = tf[i].get(w, 0)
        if f:
            s += idf.get(w, 0) * (f * 2.5) / (f + 1.5 * (0.25 + 0.75 * dl / (avgdl or 1)))
    return s


def answer(question):
    q = tok(question)
    ranked = sorted(range(len(docs)), key=lambda i: score(q, i), reverse=True)
    if not ranked or score(q, ranked[0]) <= 0:
        return "I'll route that to a human teammate.", None
    best = KB[ranked[0]]
    return best["text"], best["source_url"]


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "How do I get started?"
    text, src = answer(question)
    print(f"Q: {question}\\n\\nA: {text}\\n")
    if src:
        print(f"(source: {src})")
'''
