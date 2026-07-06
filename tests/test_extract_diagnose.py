"""Heuristic extraction + diagnosis + cost, all offline (no LLM)."""

from leadscout.diagnose import diagnose, estimate_cost
from leadscout.kernel import load_kernel
from leadscout.research.extract import extract_signals, verify_signals

CORPUS = {
    "https://acme.com/careers": "We are hiring a Customer Support Specialist and 4 support engineers.",
    "https://acme.com/help": "Browse articles in our knowledge base. Find answers here.",
    "https://acme.com/": "Acme is the fastest growing billing platform. Thousands of customers trust us.",
}


def test_heuristic_extracts_support_signals():
    sigs = extract_signals(CORPUS, load_kernel(), prefer_llm=False)
    types = {s.signal_type for s in sigs}
    assert "support_hiring" in types
    assert "help_center" in types
    # every surfaced signal is verbatim in its source
    for s in sigs:
        assert s.evidence_quote in " ".join(CORPUS.values()) or s.evidence_quote in CORPUS[s.source_url]


def test_unverifiable_candidate_dropped():
    from leadscout.research.extract import SignalCandidate
    fake = SignalCandidate("support_hiring", "this text is not anywhere in corpus at all", "https://acme.com/", 0.9)
    kept = verify_signals([fake], CORPUS)
    assert kept == []


def test_diagnosis_high_readiness():
    sigs = extract_signals(CORPUS, load_kernel(), prefer_llm=False)
    dx = diagnose(sigs, load_kernel(), company_name="Acme", use_llm=False)
    assert not dx.disqualified
    assert dx.readiness_qualitative == "high"
    assert "support" in dx.bottleneck.lower()
    assert dx.matched_patterns


def test_ai_native_disqualifies():
    corpus = {"https://x.com/": "Our product is powered by AI and built on GPT large language models."}
    sigs = extract_signals(corpus, load_kernel(), prefer_llm=False)
    dx = diagnose(sigs, load_kernel(), company_name="X", use_llm=False)
    assert dx.disqualified


def test_cost_infers_headcount_from_evidence():
    sigs = extract_signals(CORPUS, load_kernel(), prefer_llm=False)
    cost = estimate_cost(sigs, load_kernel())
    # "4 support engineers" should be inferred
    assert cost.inputs["support_headcount"] == 4
    assert cost.inputs["headcount_source"] == "inferred_from_evidence"
    assert cost.value_usd_per_year > 0


def test_cost_defaults_without_evidence():
    corpus = {"https://y.com/help": "Browse articles in our knowledge base."}
    sigs = extract_signals(corpus, load_kernel(), prefer_llm=False)
    cost = estimate_cost(sigs, load_kernel())
    assert cost.inputs["headcount_source"] == "kernel_default"
    assert cost.inputs["support_headcount"] == 3


def test_mislabeled_anti_signal_dropped():
    # Regression: an LLM tagged an open-source quote as ai_native (verbatim, but the
    # quote has no disqualifying keyword) — it must be dropped, not disqualify anyone.
    from leadscout.research.extract import SignalCandidate, verify_signals
    corpus = {"https://x.com/": "Our code is open source too, so you're never locked in."}
    mislabel = SignalCandidate("ai_native", "Our code is open source too, so you're never locked in.",
                               "https://x.com/", 0.9, is_anti_signal=True)
    assert verify_signals([mislabel], corpus) == []


def test_real_anti_signal_kept():
    from leadscout.research.extract import SignalCandidate, verify_signals
    corpus = {"https://x.com/": "Our product is powered by AI and built on GPT."}
    real = SignalCandidate("ai_native", "Our product is powered by AI and built on GPT.",
                           "https://x.com/", 0.9, is_anti_signal=True)
    kept = verify_signals([real], corpus)
    assert len(kept) == 1  # contains "powered by ai" -> confirmed disqualifier
