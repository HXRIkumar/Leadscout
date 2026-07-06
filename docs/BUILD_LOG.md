# Build Log

Append-only milestone log. Autonomous overnight session, 2026-07-06.

## 2026-07-06 — Session 1 (autonomous)

**Kernel interview → locked `kernel/niche.yaml`.**
- Forced the offer to a single costed problem: **support deflection** (chosen over
  document processing / workflow automation — the only wedge legible AND demo-able
  from public data alone).
- Offer as numbers: **35% ticket deflection**, **$2,500 / 3-week** pilot,
  archetype `rag_support_bot`. Cost model + 3 disqualifiers concrete.
- Business assumptions (price, buyer, geography, cost defaults, warm-network)
  recorded in `DECISIONS_NEEDED.md` (D1–D6).

**Repo scaffold (§4.2).** Full package tree, `pyproject.toml` (uv/hatchling),
`.env.example`, `.gitignore`, `README.md`, `SPEC.md` (= v2 spec).

**Retained V1 spine (§6), built fresh to V1's locked decisions:**
- SQLAlchemy 2.x models — V1 tables + V2 extensions + reserved-seam tables
  (`scores`, `proposals`, `outcomes`, …) created empty from day 1 (§4.4).
- `db.py` (SQLite engine/session, idempotent `init_db`), `config.py`
  (pydantic-settings), `logging.py` (RunLog counters), `kernel.py` (typed loader).
- `polite_fetch()` — robots-binding, ≥2s/domain, on-disk fetch cache, trafilatura
  clean text. `llm_cache` (sha256). Compliance layer (regions/footer/suppression).
  Follow-up rule + lifecycle state machine.

**LLM layer (§4.1).** Uniform httpx providers (Groq→Gemini→frontier), router with
cache-first + budget guards (frontier ₹/mo, Groq/day, Hunter/mo), graceful
degradation to heuristics when no keys (`NoLLMAvailable`). Consulted the `claude-api`
skill for the Anthropic wire format + model IDs.

**Discovery Lite (A2).** Adapter interface + HN "Who is hiring" + YC directory
(both best-effort, fail-closed) + EDGAR reserved stub + careers probe + discovery
orchestrator with deterministic prefilter.

**Research Engine + Diagnosis (A3–A5) — the Week-1 core.**
- Extraction: `HeuristicExtractor` (offline, word-boundary keyword matching) +
  `LLMExtractor` (router), both feeding the shared verifier.
- **Anti-hallucination verifier (fail-closed):** every quote must appear verbatim
  (whitespace-normalized) in fetched text or it's dropped + logged.
- Diagnosis (A4): deterministic bottleneck/wedge/readiness + disqualification on
  anti-signals, optional LLM refinement (facts stay fixed).
- Cost estimator (A5): defensible $/yr from the kernel model; infers support
  headcount from evidence when present.
- `brief.py` composer → `data/companies/<domain>/brief.md`, persists company /
  artifacts / verified signals / brief.

**CLI (§4.1).** `leadscout`: brief, scout, add, companies, kernel, budget, initdb +
reserved stubs (demo, draft, post, warm, pipeline, capture).

**Reserved seams (§4.4).** `intelligence/` (scorer B5 with V1 formula seed;
winloss C1, pricing C2, patterns C3, relgraph C4 stubs); demo/outreach/distribution/
pipeline packages with interfaces + trigger docstrings; compliance layer live;
pattern library seeded (8 patterns, stable IDs).

**Content.** compliance/{LIA, region_rules, suppression_policy}, pattern_library
(8 + README), templates (demo families, call_notes, email/content/proposal), prompts
(researcher, diagnostician, writer, demo_builder).

**Verification.**
- `pytest`: **25 passing** (verify fail-closed, extract/diagnose/cost, brief e2e via
  respx, compliance, lifecycle, prefilter, kernel, scorer).
- `ruff`: clean.
- **Live run** `leadscout brief plausible.io`: crawled real pages, verified evidence
  (0 rejected), produced a brief. Caught + fixed a real bug (agency keyword
  `"our clients"` false-matched inside `"your clients"` → word-boundary matching +
  tighter keywords). Re-run: correct honest low-readiness diagnosis.

**Milestone W1 (SPEC §5.2): MET.** `brief <url>` produces an evidence-verified
diagnosis with a defensible cost number, every claim carrying a verbatim quote +
source URL, failing closed — offline and live.

**Bonus (past W1, pure deterministic infra, no business input needed):**
- **A11 capture sync** — `leadscout capture` upserts the pattern library into the
  `patterns` table (synced 8 live).
- **A10 Pipeline CRM-lite functional** — `promote` (company→lead), `advance`
  (validated lifecycle transitions), `record_send` (+4-business-day follow-up),
  `follow_ups_due`, funnel counts, `leadscout pipeline` digest. Verified live.
- Deliberately **did not** build A6 (demo generator — needs a target company,
  embeddings, and operator review) or A8 (needs D4 warm-network data): those need
  Hari's input, per the SPEC's anti-overbuild rules (§5.5).

### Session 1 (continued) — full Category-A build

After review, continued past Week 1 (the remaining Category-A modules are pure
engineering that operate on already-fetched public data — no business input needed):

- **A6 Micro-Demo Generator** (centerpiece): dependency-free BM25 RAG (`demo/rag.py`)
  over a company's public docs + `demo/scaffold.py` emitting a runnable demo folder
  (knowledge_base.json, standalone `answer.py`, questions.json, loom_script.md,
  README). `leadscout demo <domain>`. **Verified live on plausible.io** — the portable
  bot answers from real docs with citations, zero setup.
- **A7 Outreach Drafting**: `outreach/draft.py` — cold message anchored on the top
  verified signal + cost + region compliance footer, warm-intro variant, send-gate.
  `leadscout draft <domain>`. Verified live.
- **A8 Warm Network**: `distribution/warm.py` — add/import/track contacts, reactivation
  cadence. `warm`, `warm-add`, `warm-import`.
- **A9 Content Engine Lite**: `distribution/content.py` — redacted niche posts from a
  brief/demo + cadence log. `leadscout post <domain>`. Verified live.
- Cost routing corrected: demo Q&A / outreach polish / content polish run on the free
  bulk tier; frontier reserved for diagnosis (§4.5).
- Added a dev-only SQLite additive-column migration shim in `init_db` (caught by an
  A6 schema change: new `demos.domain`/`deflection_rate` columns on an existing table).

Also added **B7's single Playwright fallback** (`research/browser.py`, default-off,
dependency-guarded) for thin/JS-only pages — the one B-module the spec scopes for "now".

**Final state (Session 1):** **44 tests passing, ruff clean, ~4.2k LOC.** Every
Category-A module (A1-A11) functional (four newest verified live) + B7 single fallback.
Remaining seams (B/C) are correctly trigger-gated. Genuine stopping point: remaining
work needs API keys, the operator's warm-network data (D4), live discovery testing, or
trigger events (a signed pilot, ≥5-10 outcomes) — none buildable without your input.

## 2026-07-06 — Session 2: frontier provider → OpenAI (D7)

Operator switched the frontier provider from Anthropic to **OpenAI** (has paid OpenAI,
no paid Anthropic, uses Claude Code for dev — avoids duplicate spend). Provider-agnostic
router made this a config change, not a rewrite:

- `config.py`: `frontier_provider` default `openai`, `frontier_model` default `gpt-5-mini`.
- `providers.py`: `OPENAI_MODEL=gpt-5-mini`; added `_is_reasoning_model` so GPT-5/o-series
  calls omit `temperature` (reasoning models reject non-default temp); reframed the
  Anthropic adapter as retained/optional.
- `router.py`: OpenAI frontier candidate now honors `FRONTIER_MODEL`; `FRONTIER_TASKS`
  broadened to `{diagnosis, demo, proposal, architecture}`.
- Routing correction (supersedes Session 1's demo→free note): **demo generation now
  routes to the frontier** (cheap on gpt-5-mini, budget-guarded); outreach & content
  polish stay on the free bulk tier ($0 marginal, per §4.1).
- `budget.py`: provider-agnostic price table (GPT-5 family + OpenAI first, Anthropic
  retained); conservative default for unlisted models (no more Opus-specific default).
- Docs (README, NEXT_STEPS, KNOWN_LIMITATIONS, DECISIONS_NEEDED D7) updated.
- **No Claude-specific runtime dependency remains** — Anthropic is a retained,
  env-selectable adapter only. Nothing in the pipeline requires a Claude model.
- `.env.example` set to OpenAI; the operator's local `.env` must be updated by hand
  (secret-scan guard blocks tool edits) — change `FRONTIER_PROVIDER=openai` +
  `FRONTIER_MODEL=gpt-5-mini`.

Tests still 44/44, ruff clean.

## 2026-07-07 — Session 3: live-key testing + extraction→frontier routing

**Live real-API test** (operator added keys): OpenAI `gpt-5-mini` + Groq both 200 OK;
real briefs on plausible.io + tailscale.com + a 12-Q&A demo. Full session cost:
frontier ₹1.32 / ₹1000. Findings + fixes:
- **Bug (found live, fixed):** Groq mislabeled an "open source" quote as `ai_native`,
  wrongly disqualifying a prospect. Added an anti-signal keyword gate in
  `verify_signals` (`anti_signal_confirmed`) + 2 regression tests. (Shipped in 2188f4b.)
- **Routing change (operator-directed):** moved **signal extraction to the frontier
  tier** (`gpt-5-mini`) for max precision — one line: `"extraction"` moved from
  `BULK_TASKS` to `FRONTIER_TASKS`. Groq/Gemini remain the free budget/error fallback.
  Outreach + content polish kept on the free tier via a new `"polish"` bulk task
  (draft.py, content.py). Budget guard confirmed: extraction now increments the
  frontier ₹ meter and is gated by `frontier_ok()` (warn 80% / trip 100%).
- **Test-isolation fix:** the real `.env` file leaked keys into tests (pydantic reads
  the file, not just env vars). conftest now sets `Settings.model_config["env_file"]=None`
  so tests control keys via env vars only.

Tests 53/53, ruff clean.

## 2026-07-07 — Session 4: consultant-grade upgrade (goal: lead-gen platform)

Operator set a broad "consultant-grade lead-gen platform" goal. Compliance boundary
recorded (D8): automate compliant sources only; LinkedIn/G2/Capterra/Crunchbase/Reddit
stay manual link-outs (SPEC §3.5 Never Build + ToS). Working through improvements:

**Improvement #1 — consultant-grade diagnosis (A4).** `Diagnosis` expanded with
business_summary, pain_points, ai_opportunities, automation_opportunities,
estimated_roi (cites the A5 cost number), implementation_complexity, recommended_project,
outreach_angle, proposal_outline (B2 preview). Deterministic-first (works offline),
LLM-enriched (`gpt-5-mini`), every field grounded in verified signals only. Cost is now
computed before diagnosis so ROI is quantified. Brief renders a "Consultant analysis"
section. New diagnostician prompt (v2). Live-verified on plausible.io (ROI 8.1×,
evidence-cited). +1 regression test. Benchmarks recorded in docs/BENCHMARKS.md.

Tests 54/54, ruff clean.

**Improvement #2 — tech-stack / support-widget detection (A2/A3).**
`research/techstack.py` fingerprints support/helpdesk widgets (Intercom, Zendesk,
Gorgias, Help Scout, Front, Freshchat, Drift, Crisp, Tidio, Olark, HubSpot) from a
site's own public HTML — a strong, specific Tier-1 support signal. Evidence is the
vendor fingerprint, verbatim in the HTML, so it passes the same fail-closed verifier.
Integrated into the brief pipeline (verified against an HTML corpus, merged + deduped).
Live-verified: Gorgias detected on gorgias.com; recall caveat recorded (JS-injected
widgets need the B7 browser fallback). +3 tests.

Tests 57/57, ruff clean.

**Improvement #3 — opportunity scoring + ranking (B5 activated).**
`intelligence.scorer.opportunity_score` wires the reserved V1 fixed-weight formula
into the flow (operator-directed for the lead-gen goal): explainable 0-100 score with
factor breakdown + §14 value band by archetype; disqualified → 0. Each `brief` run now
persists a `Score` row and renders an "Opportunity score" section. New `leadscout rank`
command orders briefed companies by score (latest per domain), hides disqualified.
Live: plausible.io 73 > tailscale.com 68, both high readiness. +3 tests.

Tests 60/60, ruff clean.
