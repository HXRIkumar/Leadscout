"""LLM provider calls over a single httpx interface (SPEC §4.1).

One uniform HTTP layer for all providers keeps the budget tool boring and cheap
(the primary path is Groq/Gemini free tiers; OpenAI is the frontier default). Each
function returns a `ProviderResponse` or raises `ProviderError`. Callers (router.py)
own routing, caching, and budget. Provider-agnostic by design: switching the frontier
provider is a config change, not a code change (FRONTIER_PROVIDER / FRONTIER_MODEL).

NOTE (see docs/KNOWN_LIMITATIONS.md #1): uniform httpx is a deliberate deviation
from per-vendor SDKs. The OpenAI call uses the Chat Completions wire format; the
Anthropic call (retained, for FRONTIER_PROVIDER=anthropic) uses the Messages API
wire format. Swapping either to its official SDK later is isolated to this file.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

# Provider default models (verify against current provider docs before first paid use).
GROQ_MODEL = "llama-3.1-8b-instant"      # V1 primary extraction model (bulk, free)
GEMINI_MODEL = "gemini-flash-lite-latest"  # schema fallback (bulk, free)
OPENAI_MODEL = "gpt-5-mini"              # default frontier model (lightweight GPT-5 reasoning)

_ANTHROPIC_VERSION = "2023-06-01"
_TIMEOUT = 60.0

# Reasoning-model families (OpenAI) reject a non-default `temperature` on Chat Completions.
_REASONING_PREFIXES = ("gpt-5", "o1", "o3", "o4")


class ProviderError(RuntimeError):
    pass


def _is_reasoning_model(model: str) -> bool:
    return model.lower().startswith(_REASONING_PREFIXES)


@dataclass
class ProviderResponse:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""


def _post(url: str, *, headers: dict, json: dict, params: dict | None = None) -> dict:
    try:
        resp = httpx.post(url, headers=headers, json=json, params=params, timeout=_TIMEOUT)
    except httpx.HTTPError as e:  # network/timeout
        raise ProviderError(f"request failed: {e}") from e
    if resp.status_code >= 400:
        raise ProviderError(f"HTTP {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def _openai_style(base_url: str, api_key: str, model: str, system: str, prompt: str, json_mode: bool) -> ProviderResponse:
    """Shared shape for OpenAI + Groq (OpenAI-compatible Chat Completions)."""
    body: dict = {
        "model": model,
        "messages": (
            ([{"role": "system", "content": system}] if system else [])
            + [{"role": "user", "content": prompt}]
        ),
    }
    # Reasoning models (gpt-5 / o-series) only accept the default temperature; others get temp 0.
    if not _is_reasoning_model(model):
        body["temperature"] = 0
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    data = _post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=body,
    )
    text = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    return ProviderResponse(
        text=text,
        input_tokens=usage.get("prompt_tokens", 0),
        output_tokens=usage.get("completion_tokens", 0),
        model=model,
    )


def groq_complete(api_key: str, system: str, prompt: str, *, json_mode: bool = False, model: str = GROQ_MODEL) -> ProviderResponse:
    return _openai_style("https://api.groq.com/openai/v1", api_key, model, system, prompt, json_mode)


def openai_complete(api_key: str, system: str, prompt: str, *, json_mode: bool = False, model: str = OPENAI_MODEL) -> ProviderResponse:
    return _openai_style("https://api.openai.com/v1", api_key, model, system, prompt, json_mode)


def gemini_complete(api_key: str, system: str, prompt: str, *, json_mode: bool = False, model: str = GEMINI_MODEL) -> ProviderResponse:
    body: dict = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    gen_cfg: dict = {"temperature": 0}
    if json_mode:
        gen_cfg["responseMimeType"] = "application/json"
    body["generationConfig"] = gen_cfg
    data = _post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={"Content-Type": "application/json"},
        json=body,
        params={"key": api_key},
    )
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        raise ProviderError(f"unexpected Gemini response: {str(data)[:300]}") from e
    usage = data.get("usageMetadata", {})
    return ProviderResponse(
        text=text,
        input_tokens=usage.get("promptTokenCount", 0),
        output_tokens=usage.get("candidatesTokenCount", 0),
        model=model,
    )


def anthropic_complete(api_key: str, system: str, prompt: str, *, model: str, max_tokens: int = 2048, json_mode: bool = False) -> ProviderResponse:
    """Anthropic Messages API (documented REST wire format).

    RETAINED adapter — OpenAI is the default frontier provider. Re-enable Anthropic
    with FRONTIER_PROVIDER=anthropic + FRONTIER_MODEL=<claude model>. `json_mode` is
    handled by prompt instruction here (kept minimal); no thinking param is sent.
    """
    body: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        body["system"] = system
    data = _post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": _ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        },
        json=body,
    )
    parts = [b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"]
    usage = data.get("usage", {})
    return ProviderResponse(
        text="".join(parts),
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        model=model,
    )
