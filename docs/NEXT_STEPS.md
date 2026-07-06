# Next Steps

**All Category-A modules (A1–A11) are functionally built.** What remains is (1)
turning them on with keys + your data, (2) operating the loop on real prospects, and
(3) trigger-gated Category B/C work. Status matrix: `ROADMAP_PROGRESS.md`.

## Do first (fast wins on wake-up)

1. **Add API keys** to `.env` (copy `.env.example`). A free **Groq** key turns on bulk
   LLM extraction + outreach/content polish (free tier). An **OpenAI** key powers the
   frontier tier — diagnosis + demo generation (default `gpt-5-mini`, ₹1,000/mo cap).
   Optional: Gemini (free bulk fallback). Anthropic is retained but off by default
   (set `FRONTIER_PROVIDER=anthropic` to re-enable). Verify model IDs (`KNOWN_LIMITATIONS.md #2`).
2. **Review `kernel/niche.yaml` + `DECISIONS_NEEDED.md`** (D1–D3, D5 are yours to
   confirm/override — all cheap to change).
3. **Fill D4 — your warm network** → `leadscout warm-import contacts.csv`
   (columns: name,company,source,warmth,channel). This is the one thing only you can
   do; it gates the highest-converting channel. Then `leadscout warm`.

## Run the loop (the actual Week 2–3 activity, per SPEC §5.5)

The code is built; the milestones are now about *doing*, not building:
1. `leadscout scout` (live HN/YC) and/or `leadscout add <domain>` — build a curated
   30–50 list of in-niche companies.
2. `leadscout brief <domain>` on each → read the diagnosis; keep the good ones.
3. `leadscout demo <domain>` on the best → review the generated demo folder, record the
   Loom (script is drafted), tighten the bot.
4. `leadscout draft <domain> --country <cc> --name <first>` → edit, send **manually**.
   Log it: `leadscout promote <domain> --source ...` then `leadscout advance <id> contacted`.
5. `leadscout post <domain>` → publish 1–2 redacted posts.
6. `leadscout pipeline` daily for follow-ups; `leadscout warm` for reactivations.
Target (SPEC §5.4): ≥5 discovery calls, ≥1 signed pilot by week 8.

## Engineering polish (optional, no business input)

- **A6 hardening**: swap BM25 for a local vector store if recall matters; wire the demo
  into a real widget for the pilot; better question derivation.
- **A2**: live-test HN/YC adapters (they're best-effort/fail-closed); the YC Algolia
  key scrape may need a tweak. Add a careers-page pre-qualifier (careers.py exists).
- **B7 browser fallback**: single Playwright function for JS-only sites (`[browser]`
  extra is declared). Only if blocked sites materially matter.
- **A3 polish**: real company naming from `<title>`/OG; strip list-marker artifacts
  from evidence quotes.
- **Migrations**: add Alembic before any non-additive schema change / Postgres.

## Phase-gated (Category B/C — do NOT build ahead of trigger, SPEC §5.5)

- **First signed pilot** → B2 Proposal Generator (`proposals` table ready), B3 Case
  Study Engine, B1 Dashboard, B4 Call Assistant, B6 EDGAR monitor, B8.
- **~5 clients + 3 case studies** → C1 Win/Loss, C2 Pricing, C3 Pattern Discovery,
  B5 Scoring (seed present), C6 Portfolio.
- **~20 clients** → C4 Relationship Intelligence, team features, B9 sending infra.
- Capture is already running (outcomes/interactions/patterns tables + `capture` sync),
  so the data these need accumulates from day 1.

## Testing conventions

Fixture-based (`respx` mocks httpx); no live calls in tests. Add a smoke test per new
adapter/agent (SPEC §15). `uv run pytest -q` · `uv run ruff check leadscout tests`.

## Lead-gen upgrade — status & remaining roadmap (Session 4, 2026-07-07)

**Shipped this session (each: tested + live-verified + committed):**
1. Consultant-grade diagnosis (summary, pains, AI/automation opportunities, ROI, complexity, recommended project, outreach angle, proposal outline)
2. Tech-stack / support-widget detection from public HTML
3. Opportunity scoring + `leadscout rank`
4. Manual-research link-outs (decision makers + restricted sources, compliant)
5. Documentation-quality scoring
6. GitHub enrichment (official API)
7. Search-based discovery adapter (`leadscout search`, Brave, keyed)

**Remaining — with honest impact / blocker:**
| Item | Status | Note |
|---|---|---|
| Search-based discovery | **built** (`leadscout search`), needs SEARCH_API_KEY (D9) | activates on key |
| Similar-company / competitor expansion | **built** (`leadscout expand`) | LLM-suggest → niche prefilter → domain-reachability verify; candidates verified by `brief` |
| Product-launch detection (RSS/Atom) | **built** (`research/feeds.py`) | dated `docs_lagging` signals from the site's own feed, verbatim-verified |
| Funding detection | **built** (`funding_event` extraction from site text) | SEC EDGAR (B6) remains reserved — official-API funding is structured data that doesn't fit the verbatim-quote model; add at Phase-2 trigger as a distinct fact type |
| LinkedIn / G2 / Capterra / Crunchbase / Reddit / Product Hunt (automated) | **never** (D8) | ToS / SPEC §3.5; shipped as manual link-outs instead |
| C1 win/loss · C2 pricing · C3 patterns · C5 learned scoring | reserved | **need outcome data** — unlocked only by *operating* (run briefs → send → record wins/losses) |

**Highest-leverage next action is operating, not building:** run `leadscout brief` on
real prospects → `demo`/`draft` the best → record outcomes. That outcome data is the
only thing that unlocks the genuinely next-most-valuable work (win/loss, price-to-win,
cross-engagement pattern discovery) per the SPEC's trigger model.
