"""Manual-research link-outs (compliant, SPEC §3.5 / §7.7 / decision D8).

Restricted sources (LinkedIn, G2, Capterra, Crunchbase, Reddit, Product Hunt) are
NEVER scraped — their ToS prohibit it and LinkedIn scraping is a Never-Build. Instead
we generate pre-filled search URLs the operator opens by hand, so they get the
decision-maker + review + funding research surface in one click, compliantly. Pure
string building — no network, no scraping.
"""

from __future__ import annotations

from urllib.parse import quote_plus


def research_links(domain: str, company_name: str) -> dict[str, str]:
    """Pre-filled manual-research URLs (decision makers, reviews, funding, mentions)."""
    c = quote_plus(company_name)
    d = quote_plus(domain)
    people_q = quote_plus(f'{company_name} (founder OR CTO OR "head of support" OR "customer support")')
    return {
        "LinkedIn — company": f"https://www.linkedin.com/search/results/companies/?keywords={c}",
        "LinkedIn — decision makers": f"https://www.linkedin.com/search/results/people/?keywords={people_q}",
        "G2 reviews": f"https://www.g2.com/search?query={c}",
        "Capterra reviews": f"https://www.capterra.com/search/?query={c}",
        "Crunchbase (funding)": f"https://www.crunchbase.com/textsearch?q={c}",
        "Reddit — support gripes": f"https://www.reddit.com/search/?q={quote_plus(company_name + ' support')}",
        "Hacker News mentions": f"https://hn.algolia.com/?q={d}",
        "Product Hunt": f"https://www.producthunt.com/search?q={c}",
        "X / Twitter": f"https://twitter.com/search?q={c}",
        "News (Google News)": f"https://news.google.com/search?q={c}",
    }
