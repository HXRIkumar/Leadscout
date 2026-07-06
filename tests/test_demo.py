"""A6 Micro-Demo Generator — offline (corpus passed directly, no crawl, no LLM)."""

import json

from leadscout.db import session_scope
from leadscout.demo import scaffold_demo
from leadscout.demo.rag import build_rag
from leadscout.models import Demo

CORPUS = {
    "https://acme.com/help/getting-started": (
        "Getting started with Acme is easy. To get started, create an account and "
        "verify your email. Then you can invite your team from the settings page."
    ),
    "https://acme.com/help/password": (
        "To reset your password, go to the login page and click forgot password. You "
        "will receive a password reset link by email. Follow the link to set a new password."
    ),
    "https://acme.com/help/billing": (
        "Our pricing plans include Free, Pro, and Enterprise. To change your plan, go to "
        "billing settings. You can cancel your subscription anytime from the billing page."
    ),
}
QUESTIONS = ["How do I reset my password?", "How do I cancel my subscription?"]


def test_build_rag_answers_and_sources():
    rag = build_rag(CORPUS, questions=QUESTIONS, use_llm=False)
    assert rag.chunks
    assert len(rag.answers) == 2
    assert 0.0 <= rag.deflection_rate <= 1.0
    pw = next(a for a in rag.answers if "password" in a.question.lower())
    assert pw.sources  # retrieval found something
    assert "password" in pw.answer.lower()


def test_scaffold_emits_runnable_demo():
    res = scaffold_demo("acme.com", corpus=CORPUS, questions=QUESTIONS, use_llm=False)
    from pathlib import Path
    d = Path(res.demo_path)
    for f in ("knowledge_base.json", "questions.json", "answer.py", "loom_script.md", "README.md"):
        assert (d / f).exists(), f
    kb = json.loads((d / "knowledge_base.json").read_text())
    assert kb and "source_url" in kb[0]
    # the standalone bot must be valid Python
    compile((d / "answer.py").read_text(), "answer.py", "exec")


def test_demo_persisted():
    scaffold_demo("beta.com", corpus=CORPUS, questions=QUESTIONS, use_llm=False)
    with session_scope() as s:
        row = s.query(Demo).filter(Demo.domain == "beta.com").first()
        assert row is not None
        assert row.template_family == "rag_support_bot"
        assert row.deflection_rate is not None
