"""Manual-research link-outs (compliant; no scraping)."""

from leadscout.research.links import research_links


def test_links_cover_decision_makers_and_restricted_sources():
    links = research_links("acme.com", "Acme Corp")
    for key in [
        "LinkedIn — company", "LinkedIn — decision makers", "G2 reviews",
        "Capterra reviews", "Crunchbase (funding)", "Reddit — support gripes",
        "Hacker News mentions", "Product Hunt", "X / Twitter", "News (Google News)",
    ]:
        assert key in links
    assert all(v.startswith("https://") for v in links.values())


def test_links_url_encode_and_target_roles():
    links = research_links("acme.com", "Acme Corp")
    assert "Acme+Corp" in links["LinkedIn — company"]        # spaces encoded
    dm = links["LinkedIn — decision makers"].lower()
    assert "founder" in dm and "cto" in dm                   # targets decision makers
