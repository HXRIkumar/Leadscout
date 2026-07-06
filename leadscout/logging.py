"""Structured logging + per-run summary (SPEC §15).

Console logging via `rich`, plus a `RunLog` that accumulates the counters the spec
cares about (fetched, extracted, rejected quotes, LLM calls) and writes a JSON
summary to data/logs/ so every run is auditable.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from rich.logging import RichHandler

from .config import get_settings

_CONFIGURED = False


def get_logger(name: str = "leadscout") -> logging.Logger:
    global _CONFIGURED
    if not _CONFIGURED:
        logging.basicConfig(
            level=logging.INFO,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
        )
        _CONFIGURED = True
    return logging.getLogger(name)


@dataclass
class RunLog:
    """Accumulates counters for one pipeline run and persists a summary."""

    run: str
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    pages_fetched: int = 0
    pages_from_cache: int = 0
    pages_blocked_by_robots: int = 0
    signals_extracted: int = 0
    signals_rejected_unverified: int = 0
    llm_calls: int = 0
    llm_cache_hits: int = 0
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def note(self, msg: str) -> None:
        self.notes.append(msg)

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def write(self) -> Path:
        logs_dir = get_settings().data_path / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        path = logs_dir / f"{self.run}_{stamp}.json"
        data = asdict(self)
        data["finished_at"] = datetime.now(UTC).isoformat()
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return path
