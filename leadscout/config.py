"""Runtime configuration (SPEC §4.1 secrets/config).

`.env` + pydantic-settings. Everything has a default so the whole pipeline runs
offline with no keys (heuristic extractor fallback). Keys unlock LLM quality.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root = two levels up from this file (leadscout/config.py -> repo/).
REPO_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Identity ---
    operator_email: str = "you@example.com"
    operator_name: str = "Operator"
    postal_address: str = ""

    # --- LLM providers (optional) ---
    groq_api_key: str = ""
    gemini_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    # Frontier provider is provider-agnostic (see leadscout/llm/router.py). Default: OpenAI.
    # Re-enable Anthropic with FRONTIER_PROVIDER=anthropic + FRONTIER_MODEL=<claude model>.
    frontier_provider: str = "openai"    # openai | anthropic
    frontier_model: str = "gpt-5-mini"   # lightweight GPT-5 reasoning model, right-sized for diagnosis

    # --- Enrichment ---
    github_token: str = ""
    github_enrichment: bool = True   # attach GitHub eng-context facts to briefs (official API)
    hunter_api_key: str = ""

    # --- Budget guards ---
    frontier_monthly_budget_inr: int = 1000
    groq_daily_request_cap: int = 14000
    hunter_monthly_cap: int = 50

    # --- Crawl politeness ---
    crawl_min_interval_seconds: float = 2.0
    crawl_timeout_seconds: int = 10
    crawl_max_pages_per_company: int = 8
    use_browser_fallback: bool = False   # B7: single Playwright fallback for JS-only pages (needs [browser] extra)

    # --- Paths ---
    database_url: str = "sqlite:///data/leadscout.sqlite"
    data_dir: str = "data"
    kernel_path: str = "kernel/niche.yaml"

    # --- Derived helpers ---
    @property
    def repo_root(self) -> Path:
        return REPO_ROOT

    @property
    def data_path(self) -> Path:
        p = self.data_dir
        return Path(p) if Path(p).is_absolute() else REPO_ROOT / p

    @property
    def kernel_file(self) -> Path:
        p = self.kernel_path
        return Path(p) if Path(p).is_absolute() else REPO_ROOT / p

    @property
    def user_agent(self) -> str:
        # Honest identification (SPEC §7.3 / §4.1).
        return f"LeadScout/0.2 (+{self.operator_email})"

    def has_any_llm(self) -> bool:
        return bool(
            self.groq_api_key or self.gemini_api_key or self.openai_api_key or self.anthropic_api_key
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
