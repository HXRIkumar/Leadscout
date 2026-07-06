"""Budget guards (SPEC §4.1 / §4.5): hard caps with warnings at 80%.

File-backed counters in data/budget.json. Three independent budgets:
- frontier monthly spend (INR) — resets on month change
- Groq requests today — resets on date change (stay under free 14,400/day)
- Hunter calls this month — resets on month change

Cost-first design: bulk work runs on free tiers; frontier is only touched for
diagnosis + demo scaffolding on the ~30-50 curated accounts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ..config import get_settings

# Approx USD per 1M tokens (input, output). ~83 INR/USD. Used to estimate frontier spend.
# Extend as providers are added. Conservative — over-estimates protect the cap.
_PRICES_USD_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-haiku-4-5-20251001": (1.0, 5.0),
    "claude-sonnet-5": (3.0, 15.0),
    "claude-opus-4-8": (5.0, 25.0),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.5, 10.0),
}
_INR_PER_USD = 83.0


class BudgetExceeded(RuntimeError):
    pass


def estimate_inr(model: str, input_tokens: int, output_tokens: int) -> float:
    inp, out = _PRICES_USD_PER_MTOK.get(model, (5.0, 25.0))  # default to Opus rates (safe over-estimate)
    usd = (input_tokens / 1_000_000) * inp + (output_tokens / 1_000_000) * out
    return usd * _INR_PER_USD


@dataclass
class _Counters:
    month: str = ""
    day: str = ""
    frontier_inr: float = 0.0
    groq_today: int = 0
    hunter_month: int = 0


class BudgetGuard:
    def __init__(self) -> None:
        self._path: Path = get_settings().data_path / "budget.json"
        self._c = self._load()

    def _load(self) -> _Counters:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                return _Counters(**data)
            except Exception:
                pass
        return _Counters()

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._c.__dict__, indent=2), encoding="utf-8")

    def _roll(self) -> None:
        today = date.today()
        month = today.strftime("%Y-%m")
        day = today.isoformat()
        if self._c.month != month:
            self._c.month = month
            self._c.frontier_inr = 0.0
            self._c.hunter_month = 0
        if self._c.day != day:
            self._c.day = day
            self._c.groq_today = 0

    # --- Frontier (INR/month) ---
    def frontier_ok(self) -> tuple[bool, bool]:
        """Returns (allowed, at_warn_threshold)."""
        self._roll()
        cap = get_settings().frontier_monthly_budget_inr
        spent = self._c.frontier_inr
        return spent < cap, spent >= 0.8 * cap

    def record_frontier(self, model: str, input_tokens: int, output_tokens: int) -> float:
        self._roll()
        cost = estimate_inr(model, input_tokens, output_tokens)
        self._c.frontier_inr += cost
        self._save()
        return cost

    # --- Groq (requests/day) ---
    def groq_ok(self) -> tuple[bool, bool]:
        self._roll()
        cap = get_settings().groq_daily_request_cap
        return self._c.groq_today < cap, self._c.groq_today >= 0.8 * cap

    def record_groq(self) -> None:
        self._roll()
        self._c.groq_today += 1
        self._save()

    # --- Hunter (calls/month) ---
    def hunter_ok(self) -> tuple[bool, bool]:
        self._roll()
        cap = get_settings().hunter_monthly_cap
        return self._c.hunter_month < cap, self._c.hunter_month >= 0.8 * cap

    def record_hunter(self) -> None:
        self._roll()
        self._c.hunter_month += 1
        self._save()

    def snapshot(self) -> dict:
        self._roll()
        s = get_settings()
        return {
            "frontier_inr": round(self._c.frontier_inr, 2),
            "frontier_cap_inr": s.frontier_monthly_budget_inr,
            "groq_today": self._c.groq_today,
            "groq_cap": s.groq_daily_request_cap,
            "hunter_month": self._c.hunter_month,
            "hunter_cap": s.hunter_monthly_cap,
        }
