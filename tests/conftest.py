"""Shared test fixtures. Every test runs against a temp DB + temp data dir, with
crawl rate-limiting disabled, and no live network (respx mocks httpx).
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def temp_env(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/test.sqlite")
    monkeypatch.setenv("KERNEL_PATH", str(REPO / "kernel" / "niche.yaml"))
    monkeypatch.setenv("CRAWL_MIN_INTERVAL_SECONDS", "0")
    monkeypatch.setenv("OPERATOR_EMAIL", "op@example.com")
    monkeypatch.setenv("OPERATOR_NAME", "Op")
    monkeypatch.setenv("POSTAL_ADDRESS", "1 Test St, Testville")
    # ensure no real keys leak in from the environment
    for k in ("GROQ_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(k, raising=False)

    # reset cached singletons so the temp env takes effect
    from leadscout.config import get_settings
    get_settings.cache_clear()
    from leadscout.kernel import load_kernel
    load_kernel.cache_clear()
    import leadscout.db as db
    db._engine = None
    db._SessionFactory = None
    import leadscout.research.fetch as fetch
    fetch._last_fetch_at.clear()
    fetch._robots_cache.clear()

    yield
    get_settings.cache_clear()
    load_kernel.cache_clear()
