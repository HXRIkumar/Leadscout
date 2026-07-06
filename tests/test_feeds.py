"""RSS/Atom feed parsing + recency (product-launch detection)."""

from leadscout.research.feeds import days_ago, parse_feed

_RSS = """<?xml version="1.0"?><rss><channel>
  <item><title>Shipped dark mode</title><pubDate>Wed, 02 Jul 2026 10:00:00 +0000</pubDate></item>
  <item><title>New billing API</title><pubDate>Mon, 01 Jun 2026 10:00:00 +0000</pubDate></item>
</channel></rss>"""

_ATOM = """<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
  <entry><title>Launched integrations</title><updated>2026-07-01T00:00:00Z</updated></entry>
</feed>"""


def test_parse_rss():
    entries = parse_feed(_RSS)
    assert [t for t, _ in entries] == ["Shipped dark mode", "New billing API"]
    assert entries[0][1].startswith("Wed, 02 Jul 2026")


def test_parse_atom_with_namespace():
    entries = parse_feed(_ATOM)
    assert entries == [("Launched integrations", "2026-07-01T00:00:00Z")]


def test_parse_garbage_is_empty():
    assert parse_feed("<html>not a feed</html>") == []
    assert parse_feed("definitely not xml") == []


def test_days_ago_parses_both_formats():
    assert days_ago("Wed, 02 Jul 2026 10:00:00 +0000") is not None
    assert days_ago("2026-07-01T00:00:00Z") is not None
    assert days_ago("") is None
    assert days_ago("garbage") is None
