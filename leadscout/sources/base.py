"""Discovery source interface (SPEC §15: every adapter implements the same shape)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class Candidate:
    name: str
    domain: str
    source: str                       # hn, yc, edgar, manual
    description: str = ""
    url: str = ""
    extra: dict = field(default_factory=dict)


class Source(Protocol):
    """Adapter contract. Adding a source is additive (SPEC §15)."""

    name: str

    def fetch(self, *, limit: int = 50) -> list[Candidate]:
        ...
