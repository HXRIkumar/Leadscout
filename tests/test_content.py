"""A9 Content Engine Lite — offline."""

import pytest

from leadscout.db import init_db, session_scope
from leadscout.distribution.content import NoBriefError, repurpose_brief
from leadscout.models import Brief, Company, Demo


def test_repurpose_produces_redacted_posts():
    init_db()
    with session_scope() as s:
        s.add(Company(domain="acme.com", name="Acme"))
        s.add(Brief(domain="acme.com", bottleneck="Support load is rising: help center gaps.",
                    wedge="A RAG bot.", cost_estimate="≈ $57,750/yr", readiness_qualitative="high"))
        s.add(Demo(domain="acme.com", template_family="rag_support_bot", deflection_rate=0.42))

    res = repurpose_brief("acme.com", use_llm=False)
    assert len(res.posts) == 2
    joined = " ".join(res.posts)
    assert "Acme" not in joined and "acme.com" not in joined  # redacted
    assert "42%" in joined  # demo deflection rate surfaced
    import os
    assert os.path.exists(res.log_path)


def test_repurpose_without_brief_raises():
    init_db()
    with pytest.raises(NoBriefError):
        repurpose_brief("nobrief.com", use_llm=False)
