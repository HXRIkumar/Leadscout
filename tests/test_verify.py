"""The anti-hallucination rule is the system's foundation — test it hard."""

from leadscout.research.verify import verify_quote

CORPUS = {
    "https://a.com/": "We are hiring a Customer Support Specialist.   Our help\ncenter is growing fast.",
    "https://a.com/help": "Browse articles in our knowledge base.",
}


def test_verbatim_pass():
    r = verify_quote("We are hiring a Customer Support Specialist.", "https://a.com/", CORPUS)
    assert r.ok


def test_whitespace_normalized_match():
    # newline/extra-space in source should still match
    r = verify_quote("Our help center is growing fast.", "https://a.com/", CORPUS)
    assert r.ok


def test_fabricated_quote_rejected():
    r = verify_quote("We deflect 90% of tickets automatically.", "https://a.com/", CORPUS)
    assert not r.ok
    assert r.reason == "quote_not_found"


def test_url_not_in_corpus_rejected():
    r = verify_quote("Browse articles in our knowledge base.", "https://a.com/nope", CORPUS)
    # quote is genuine but claimed url absent -> re-attributed to the real source
    assert r.ok
    assert r.source_url == "https://a.com/help"


def test_reattribution_when_wrong_url():
    r = verify_quote("Browse articles in our knowledge base.", "https://a.com/", CORPUS)
    assert r.ok
    assert r.source_url == "https://a.com/help"
    assert r.reason == "reattributed"


def test_too_short_rejected():
    r = verify_quote("hi", "https://a.com/", CORPUS)
    assert not r.ok
    assert r.reason == "quote_too_short"
