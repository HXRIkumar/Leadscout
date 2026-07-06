"""A1 — Kernel loader.

Parses and validates kernel/niche.yaml into typed models. Every module reads the
kernel through here so there is exactly one source of truth (SPEC §3.1). Fails loud
if the kernel is missing or malformed — a vague kernel produces polished garbage.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from .config import get_settings


class CostLogicPrimary(BaseModel):
    formula: str
    defaults: dict[str, float]


class CostLogicAlternate(BaseModel):
    formula: str
    fully_loaded_cost_per_ticket: float


class CostLogic(BaseModel):
    primary: CostLogicPrimary
    alternate_when_ticket_volume_public: CostLogicAlternate


class KernelICP(BaseModel):
    vertical: str
    stage: str
    size: str
    geography: list[str]
    buyer: str


class KernelProblem(BaseModel):
    name: str
    cost_logic: CostLogic
    public_evidence_signals: list[str]


class PilotOffer(BaseModel):
    price: str
    weeks: str
    deliverable: str


class KernelOffer(BaseModel):
    headline_number: str
    archetype: str
    pilot: PilotOffer


class Kernel(BaseModel):
    version: int = 1
    icp: KernelICP
    problem: KernelProblem
    offer: KernelOffer
    disqualifiers: list[str]
    proof_assets: list[str] = Field(default_factory=list)


class KernelNotFound(RuntimeError):
    pass


@lru_cache(maxsize=1)
def load_kernel(path: str | None = None) -> Kernel:
    kernel_path = Path(path) if path else get_settings().kernel_file
    if not kernel_path.exists():
        raise KernelNotFound(
            f"Kernel not found at {kernel_path}. Lock kernel/niche.yaml before running the pipeline (SPEC §5.1)."
        )
    data = yaml.safe_load(kernel_path.read_text(encoding="utf-8"))
    return Kernel.model_validate(data)
