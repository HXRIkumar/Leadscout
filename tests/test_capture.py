"""A11 pattern-library sync (SPEC §4.4 substrate)."""

from leadscout.capture import sync_pattern_library
from leadscout.config import get_settings
from leadscout.db import session_scope
from leadscout.models import Pattern

PATTERN_MD = """---
id: test-pattern
niche: support-deflection
name: Test pattern
demo_family: rag_support_bot
signal_types: [support_hiring, help_center]
times_seen: 2
---
Body text.
"""


def _seed():
    lib = get_settings().data_path / "pattern_library"
    lib.mkdir(parents=True, exist_ok=True)
    (lib / "test-pattern.md").write_text(PATTERN_MD, encoding="utf-8")
    (lib / "README.md").write_text("# ignored", encoding="utf-8")


def test_sync_upserts_patterns():
    _seed()
    n = sync_pattern_library()
    assert n == 1  # README skipped
    with session_scope() as s:
        p = s.get(Pattern, "test-pattern")
        assert p is not None
        assert p.name == "Test pattern"
        assert p.demo_family == "rag_support_bot"
        assert "support_hiring" in (p.evidence_signature or "")
        assert p.times_seen == 2


def test_sync_is_idempotent():
    _seed()
    sync_pattern_library()
    sync_pattern_library()
    with session_scope() as s:
        assert len(list(s.query(Pattern).all())) == 1
