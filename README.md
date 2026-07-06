# LeadScout v2

**An AI consulting intelligence platform** — a Proof & Trust engine wrapped around a
compounding intelligence store. The core loop: *one company in → evidence-verified
diagnosis + costed pain → tailored micro-demo out*, distributed through warm network,
public content, and low-volume 1:1 outreach.

See `SPEC.md` (authoritative) for the full architecture. This repo is the Week-1
build plus reserved seams for later phases.

## Niche (locked)

Support-deflection for seed–Series-A B2B SaaS (15–80 people, not AI-native) whose
support load is outpacing their small eng team. Offer: **~35% ticket deflection**,
**$2,500 / 3-week** pilot. Full kernel: `kernel/niche.yaml`.

## Quickstart

```bash
uv venv --python 3.12
uv pip install -e ".[dev]"
cp .env.example .env          # optional: add API keys to raise quality
uv run leadscout initdb
uv run leadscout kernel       # show the locked niche
uv run leadscout brief stripe.com   # evidence-verified diagnosis + cost
```

`brief <url>` works **fully offline with no API keys** (deterministic heuristic
extractor). Adding a free **Groq** key raises extraction quality; an **OpenAI** key
powers frontier reasoning (diagnosis + demo generation). Every claim in a brief
carries a verbatim quote + source URL and **fails closed** — anything not found
verbatim in the fetched text is dropped.

### LLM providers

| Tier | Provider (default) | Used for |
|---|---|---|
| Bulk (free) | **Groq** → **Gemini Flash-Lite** | outreach & content polish; free fallback for frontier |
| Frontier (paid, budget-capped) | **OpenAI** (`gpt-5-mini`) | signal extraction, diagnosis, demo generation, proposal/architecture reasoning |

The router is provider-agnostic. To switch the frontier provider back to Anthropic,
set `FRONTIER_PROVIDER=anthropic` and `FRONTIER_MODEL=<claude model>` — no code change.

## Commands

The full loop (Category A) is live:

| Command | What it does |
|---|---|
| `leadscout brief <url>` | Research → verify → diagnose → cost → `data/companies/<domain>/brief.md` (A3–A5) |
| `leadscout demo <domain>` | Build a runnable support-deflection RAG demo on the company's public docs (A6) |
| `leadscout draft <domain>` | 1:1 outreach draft anchored on a verified fact + region compliance footer (A7) |
| `leadscout post <domain>` | Repurpose a (redacted) brief/demo into niche posts + cadence log (A9) |
| `leadscout scout` / `add` / `companies` | Discovery Lite: candidate list (HN/YC + manual) (A2) |
| `leadscout search <query>` | Search-based discovery via web-search API (needs `SEARCH_API_KEY`) |
| `leadscout expand <domain>` | Suggest + verify similar in-niche companies (LLM, compliant) |
| `leadscout warm` / `warm-add` / `warm-import` | Warm-network reactivation + import (A8) |
| `leadscout promote` / `advance` / `pipeline` | CRM-lite: lead lifecycle + follow-ups digest (A10) |
| `leadscout rank` | Rank briefed companies by explainable opportunity score (B5) |
| `leadscout capture` | Sync the pattern library into the DB (A11 substrate) |
| `leadscout kernel` / `budget` / `initdb` | Show the kernel · budget counters · init the DB |

Category B/C modules are reserved seams, implemented at their phase-gate triggers
(SPEC §5.5) — see `docs/ROADMAP_PROGRESS.md`.

## Status

Week-1 core met + verified live; **all Category-A modules (A1–A11) functionally built.**
Progress + handoff in `docs/`: **start with `HANDOFF.md`**, then `NEXT_STEPS.md`,
`ROADMAP_PROGRESS.md`, `DECISIONS_NEEDED.md`, `BUILD_LOG.md`, `KNOWN_LIMITATIONS.md`.
