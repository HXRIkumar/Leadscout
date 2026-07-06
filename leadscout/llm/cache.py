"""LLM response cache (SPEC §4.1): sha256(model + full prompt) -> response.

Backed by the `llm_cache` table so re-running a company is free.
"""

from __future__ import annotations

import hashlib

from sqlalchemy import select

from ..db import session_scope
from ..models import LLMCache


def cache_key(model: str, prompt: str) -> str:
    return hashlib.sha256(f"{model}\x00{prompt}".encode()).hexdigest()


def get_cached(model: str, prompt: str) -> str | None:
    key = cache_key(model, prompt)
    with session_scope() as s:
        row = s.get(LLMCache, key)
        if row is None:
            return None
        row.hit_count += 1
        return row.response


def set_cached(model: str, prompt: str, response: str) -> None:
    key = cache_key(model, prompt)
    with session_scope() as s:
        existing = s.get(LLMCache, key)
        if existing is None:
            s.add(LLMCache(key=key, model=model, response=response, hit_count=0))
        else:
            existing.response = response


def cache_size() -> int:
    with session_scope() as s:
        return len(s.execute(select(LLMCache.key)).all())
