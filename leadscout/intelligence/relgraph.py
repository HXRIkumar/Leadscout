"""C4 — Relationship memory -> intelligence. RESERVED.

Memory: After 10 clients. Graph analytics: After 50 / Agency. Who knows whom, who
refers, who champions. The fields (`warmth`, `source`, intro edges via
interactions) are captured from day 1 on the contacts/interactions tables (A8).
"""

from __future__ import annotations


def referral_paths(contact_id: int) -> list[list[int]]:  # pragma: no cover - reserved
    raise NotImplementedError("C4 reserved. Trigger: After 10 (memory) / 50 (graph). Substrate: contacts + interactions.")
