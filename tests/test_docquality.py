"""Documentation-quality scoring (RAG deflection potential)."""

from leadscout.research.docquality import assess_docs


def test_rich_docs_score():
    corpus = {f"https://x.com/docs/{i}": "word " * 400 for i in range(5)}
    dq = assess_docs(corpus)
    assert dq.doc_pages == 5
    assert dq.score > 0
    assert dq.band in {"moderate", "rich"}
    assert all("docs" in u for u in dq.sources)


def test_no_docs_is_thin():
    corpus = {"https://x.com/": "homepage", "https://x.com/pricing": "pricing"}
    dq = assess_docs(corpus)
    assert dq.doc_pages == 0
    assert dq.score == 0
    assert dq.band == "thin"
