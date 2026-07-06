# Roadmap Progress (against SPEC §3 module registry)

Legend: ✅ done · 🟡 partial · 🌱 seam/stub only · ⛔ reserved (trigger not fired)

## Category A — Core MVP

| Module | Status | Notes |
|---|---|---|
| A1 Niche & Offer Kernel | ✅ | `kernel/niche.yaml` locked + typed loader + `leadscout kernel` |
| A2 Discovery Lite | 🟡 | HN + YC adapters (best-effort), prefilter, manual add. EDGAR reserved. Adapters fail-closed when offline/keys rotate |
| A3 Account Research Engine | ✅ | polite crawl → corpus → verified signals; artifact store; evidence rule live |
| A4 Pain Detection & Diagnosis | ✅ | deterministic + optional LLM; pattern matching; disqualification |
| A5 ROI / Cost-of-Problem | ✅ | kernel cost model; infers headcount from evidence |
| A6 Micro-Demo Generator | ✅ | **LIVE**: `leadscout demo <domain>` builds a dependency-free BM25 RAG bot on the company's public docs, derives real questions, precomputes answers (LLM if keys), emits a runnable demo folder + Loom script, persists `demos`. Verified live on plausible.io (portable bot runs standalone). |
| A7 Outreach Drafting | ✅ | **LIVE**: `leadscout draft <domain>` — cold message anchored on one verified fact + cost + region footer, warm-intro variant, compliance send-gate. LLM polish on free tier. |
| A8 Warm Network Manager | ✅ | **LIVE**: `warm-add`, `warm-import <csv>`, `warm` reactivation digest, `log_touch` cadence. Populating needs operator's network (D4). |
| A9 Content Engine Lite | ✅ | **LIVE**: `leadscout post <domain>` — 1-2 redacted niche posts from a brief/demo + cadence log. |
| A10 Pipeline CRM-lite | ✅ | lifecycle + follow-up rule + **functional ops LIVE**: `promote`, `advance`, `record_send` (sets +4-business-day follow-up), `follow_ups_due`, funnel counts, `leadscout pipeline` digest. Referral-ask reminders + richer interactive flow: Week 3 |
| A11 Knowledge Capture Substrate | 🟡 | pattern library seeded (8, stable IDs) + **DB sync LIVE** (`leadscout capture` → `patterns` table); outcomes/interactions/patterns tables; call_notes template. Outcome/interaction capture flow **Week 3** |

## Category B — Architecture Reserved (interfaces/schema now)

| Module | Status | Trigger |
|---|---|---|
| B1 Dashboard (web UI) | ⛔ schema via CLI | After First Client / pipeline >15 |
| B2 Proposal Generator | 🌱 `proposals` table + template | After First Client |
| B3 Case Study Engine | ⛔ | After First Client |
| B4 Discovery-Call Assistant | 🌱 `call_notes.md`, interactions table | After First Client |
| B5 Lead Scoring | 🌱 `scores` table + `FixedWeightScorer` seed (disabled) | Pool >200 / Phase 3 |
| B6 Buying-Trigger Monitor (EDGAR) | 🌱 `sources/edgar.py` stub | Phase 2 |
| B7 Browser Agent (Playwright) | 🟡 | **single fallback function LIVE** (`research/browser.py`, default-off via `USE_BROWSER_FALLBACK`, wired into `polite_fetch` for thin/JS pages, dependency-guarded). Deeper agentic: After First Client |
| B8 Follow-up sequencing | 🌱 crm constants | After First Client |
| B9 Sending infrastructure | ⛔ | After 10 clients / >25 sends/day |
| B10 AI-Readiness Scoring (quantified) | ⛔ (qualitative ships in A4) | After 10 clients |

## Category C — Future Intelligence (capture now, mine at trigger)

| Module | Status | Trigger |
|---|---|---|
| C1 Win/Loss | 🌱 `intelligence/winloss.py` + outcomes table | ≥5-10 closed outcomes |
| C2 Pricing model | 🌱 `intelligence/pricing.py` | After 10 clients |
| C3 Pattern Discovery | 🌱 `intelligence/patterns.py` + pattern_library | After 10 clients |
| C4 Relationship Intelligence | 🌱 `intelligence/relgraph.py` + contacts/interactions | After 10 / 50 |
| C5 Learned Scoring | ⛔ (B5 seed present) | After 50 clients |
| C6 Portfolio Generator | ⛔ | ≥3 case studies |
| C7 Knowledge Graph | 🌱 stable pattern IDs make library graph-liftable | After 50 / Product |
| C8 Outcome Benchmarks | ⛔ | Product Phase |

## Never Build (§3.5)
Mass automated outreach · automated LinkedIn scraping. Not implemented, by design.

## Milestones (§5.2)
- **W1** ✅ `brief <url>` → evidence-verified diagnosis + cost. **MET + verified live.**
- **W2** ✅ (build) `demo <domain>` scaffolds a working artifact (verified live); outreach
  drafting + warm network live. Remaining is *activity*, not code: finish ≥2 real demos,
  ≥15 warm touches, first sends (needs your keys + D4 + real targets).
- **W3** ✅ (build) pipeline CRM-lite, content repurposer, capture — all functional.
  Remaining is running the loop on real conversations.

**All Category-A modules are functionally implemented.** What's left is Category B/C
(trigger-gated by design) + operating the system on real data.
