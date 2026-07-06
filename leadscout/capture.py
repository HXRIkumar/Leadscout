"""A11 — Knowledge Capture Substrate (partial: pattern-library sync).

Syncs the tagged-markdown pattern library (data/pattern_library/*.md) into the
`patterns` table so A4 diagnosis and (later) C3/C7 read a consistent index. Stable
IDs are the join key (SPEC §4.4). The rest of A11 (outcome/interaction capture,
call-notes flow) is Week 3.
"""

from __future__ import annotations

import yaml

from .config import get_settings
from .db import init_db, session_scope
from .logging import get_logger
from .models import Pattern

log = get_logger(__name__)


def _parse_frontmatter(text: str) -> dict | None:
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        data = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def sync_pattern_library() -> int:
    """Upsert every pattern markdown file into the `patterns` table. Returns count."""
    init_db()
    lib = get_settings().data_path / "pattern_library"
    if not lib.exists():
        log.info("pattern library not found at %s", lib)
        return 0

    count = 0
    with session_scope() as s:
        for path in sorted(lib.glob("*.md")):
            if path.name.lower() == "readme.md":
                continue
            fm = _parse_frontmatter(path.read_text(encoding="utf-8"))
            if not fm or "id" not in fm:
                log.info("skipping %s (no frontmatter id)", path.name)
                continue
            pid = str(fm["id"])
            sig_types = fm.get("signal_types") or []
            existing = s.get(Pattern, pid)
            if existing is None:
                existing = Pattern(id=pid, times_seen=int(fm.get("times_seen", 0) or 0))
                s.add(existing)
            existing.niche = fm.get("niche")
            existing.name = fm.get("name", pid)
            existing.demo_family = fm.get("demo_family")
            existing.evidence_signature = ",".join(sig_types) if isinstance(sig_types, list) else str(sig_types)
            count += 1
    log.info("synced %d patterns", count)
    return count
