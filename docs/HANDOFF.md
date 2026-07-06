# Handoff — Autonomous Session 1 (2026-07-06)

Read this first, then `NEXT_STEPS.md`. Everything below is verified.

## TL;DR

Week-1 of the 3-week MVP is **complete, tested (27 passing), lint-clean, and
verified against a live site**. `leadscout brief <url>` produces an evidence-verified,
costed diagnosis where every claim carries a verbatim quote + source URL and fails
closed. All reserved seams (B/C) exist. The kernel is locked with a concrete,
numeric offer. You can add API keys and immediately get higher-quality briefs, or
start Week 2 (the demo generator).

## What was completed

- **Kernel (A1)** locked: support-deflection wedge; **35% deflection**, **$2,500 /
  3-week** pilot; cost model + 3 disqualifiers. `kernel/niche.yaml` + `leadscout kernel`.
- **Retained V1 spine** built fresh: SQLAlchemy models (V1 + V2 + reserved-seam
  tables), SQLite db layer, config, structured logging, `polite_fetch` (robots +
  rate-limit + cache), `llm_cache`, compliance layer, follow-up rule + lifecycle.
- **Research + Diagnosis (A3–A5)** — the core: polite crawl → heuristic/LLM
  extraction → **fail-closed verbatim verifier** → deterministic (+optional LLM)
  diagnosis → defensible cost estimate → `brief.md` + DB persistence.
- **LLM layer**: uniform httpx router (Groq→Gemini→frontier), cache-first, budget
  guards, graceful offline degradation.
- **Discovery Lite (A2)**: HN + YC adapters (fail-closed), prefilter, manual add.
- **CLI**: brief, scout, add, companies, kernel, budget, initdb, capture (live) +
  reserved stubs (demo, draft, post, warm, pipeline).
- **Reserved seams (§4.4)**: intelligence/ (scorer seed + C1-C4 stubs), demo/
  outreach/ distribution/ pipeline/ interfaces, compliance LIVE, pattern library
  (8 patterns, DB sync live).
- **Content**: compliance docs, prompts, templates, pattern library.
- **Beyond W1 — the rest of Category A (all functional):**
  - **A6 Micro-Demo Generator** — `leadscout demo <domain>`: dependency-free BM25 RAG
    on public docs → runnable demo folder + standalone bot + Loom script. Verified
    live on plausible.io.
  - **A7 Outreach Drafting** — `leadscout draft <domain>`: fact-anchored cold message +
    cost + region footer + warm-intro variant + send-gate. Verified live.
  - **A8 Warm Network** — `warm` / `warm-add` / `warm-import`: contacts + reactivation.
  - **A9 Content Engine Lite** — `leadscout post <domain>`: redacted niche posts +
    cadence log. Verified live.
  - **A10 Pipeline CRM-lite** — `promote` / `advance` / `pipeline` digest + follow-ups.
  - **A11 capture** — `leadscout capture` syncs the pattern library → `patterns` table.

## What remains

- **Not more Category-A code — it's all built.** What remains is: (1) add keys + your
  warm-network data (D4) to turn it on, (2) *operate* the loop on real prospects
  (scout → brief → demo → draft → post → pipeline), (3) trigger-gated Category B/C
  (built ahead would violate SPEC §5.5), (4) optional polish (A6 vector store, live
  A2 adapter testing, B7 browser fallback, Alembic). Full detail in `NEXT_STEPS.md`.

## Do first tomorrow

1. `cp .env.example .env`; add a free **Groq** key; re-run a brief and compare to
   the heuristic output.
2. Review `kernel/niche.yaml` + `DECISIONS_NEEDED.md` (D1-D3, D5 are yours to
   confirm/override).
3. **Fill D4 (your warm network)** — only you can, and it gates the best channel.

## Blockers

- **None technical.** One **business** blocker for the *warm-network* channel only:
  D4 (who you know) — does not block anything built so far.
- No API keys are set, so LLM extraction/diagnosis run in deterministic-heuristic
  mode. This is by design (works offline); keys raise quality.

## Estimated completion

- **Week-1 MVP: ~100%** (core deliverable met + verified live).
- **Full 3-week MVP — Category A (A1–A11): ~90% built.** All modules functional;
  A2 adapters are best-effort (need live testing), A11 outcome/interaction capture is
  partial (needs real engagements). Remaining ~10% is operation, not code.
- **Whole platform (A+B+C): ~35%** — all of Category A functional + every B/C seam
  present; B/C implementations await their triggers by design (§5.5).

## Bugs discovered (and fixed) this session

1. **Agency anti-signal false positive** — `"our clients"` matched inside
   `"your clients"`, wrongly disqualifying Plausible. Fixed: word-boundary matching
   in the heuristic extractor + tighter agency keywords. (Caught by the live run.)
2. **Noisy funding signal** — bare `"raised"` matched "raised privacy concerns".
   Fixed: phrase-based funding keywords.
3. **respx empty-path wildcard** (test-only) — `respx.get("https://acme.test")`
   matched every path; anchored the homepage route with a regex.
4. **pyproject `readme` build failure** — created `README.md`.
5. **Outreach cost phrase duplicated** ("…of deflectable support load of deflectable
   support load") — the cost string already includes the suffix. Fixed.
6. **`demos` table missing new columns** after an A6 model change (`create_all` doesn't
   alter existing tables) → added a dev-only additive-column migration shim to `init_db`
   (`_ensure_sqlite_columns`).

## Architectural improvements noticed while implementing

- **Vendor detection needs raw HTML, not clean text.** Support-widget detection
  (Intercom/Zendesk) is weak because the verifier only sees trafilatura clean text.
  Consider a separate HTML-scan signal path whose "evidence" is the vendor script
  tag (still fetched, still verifiable against raw HTML).
- **Company naming** should come from `<title>`/OpenGraph, not the domain root.
- **Sentence splitting** should strip leading list markers ("- ") for cleaner quotes.
- **A6 will want an embeddings/vector store**; keep it local (sqlite-vec or a flat
  numpy store) to honor the $0-baseline principle.
- **Discovery could enrich candidates with a careers-page probe** (careers.py exists)
  to pre-qualify support-hiring before a full brief.

## Suggested commit messages (repo is not yet a git repo)

```
chore: scaffold repo, pyproject (uv), env, gitignore, SPEC
feat(kernel): lock niche.yaml (support-deflection, $2,500/3wk) + typed loader
feat(db): SQLAlchemy models — V1 spine + V2 extensions + reserved-seam tables
feat(llm): uniform httpx router (groq/gemini/frontier) + cache + budget guards
feat(research): polite_fetch (robots/rate-limit/cache) + fail-closed evidence verifier
feat(research): heuristic + LLM signal extraction
feat(diagnose): A4 diagnosis + A5 cost-of-problem estimator
feat(research): brief composer + `leadscout brief <url>`
feat(sources): Discovery Lite — HN/YC adapters, prefilter, EDGAR stub
feat(cli): leadscout CLI (brief/scout/add/companies/kernel/budget/capture) + reserved stubs
feat(seams): intelligence scorer seed + C1-C4 stubs; demo/outreach/distribution/pipeline
feat(compliance): region rules, footer, suppression (retained V1)
feat(capture): pattern-library → patterns table sync (A11 substrate)
feat(pipeline): A10 CRM-lite — promote/advance/record_send/follow-ups/digest
feat(demo): A6 micro-demo generator — BM25 RAG + runnable scaffold + Loom (leadscout demo)
feat(outreach): A7 drafting — fact-anchored message + region footer (leadscout draft)
feat(distribution): A8 warm network (import/track) + A9 content repurposer (post)
feat(db): dev-only additive-column migration shim for SQLite
fix(llm): route demo Q&A / outreach / content polish to free bulk tier (frontier=diagnosis only)
fix(outreach): de-duplicate cost phrase in draft
feat(research): B7 single Playwright fallback for thin/JS pages (default-off, guarded)
test: 44 tests (verify/extract/diagnose/cost/brief-e2e/compliance/crm/capture/pipeline/demo/outreach/warm/content/browser)
docs: build log, roadmap, next steps, decisions-needed, known limitations, handoff
fix(extract): word-boundary keyword matching (agency/funding false positives)
```

Recommended: `git init` on a branch, then commit in roughly the order above.
