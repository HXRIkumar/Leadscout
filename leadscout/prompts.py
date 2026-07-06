"""Versioned prompt loader (SPEC §4.2 prompts/).

Prompts are maintained as markdown files under repo-root prompts/ so they can be
edited and diffed without touching code.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from .config import get_settings


class PromptNotFound(RuntimeError):
    pass


@lru_cache(maxsize=32)
def load_prompt(name: str) -> str:
    path: Path = get_settings().repo_root / "prompts" / f"{name}.md"
    if not path.exists():
        raise PromptNotFound(f"prompt not found: {path}")
    return path.read_text(encoding="utf-8")
