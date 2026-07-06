# Next Steps

**All Category-A modules (A1–A11) are functionally built.** What remains is (1)
turning them on with keys + your data, (2) operating the loop on real prospects, and
(3) trigger-gated Category B/C work. Status matrix: `ROADMAP_PROGRESS.md`.

## Do first (fast wins on wake-up)

1. **Add API keys** to `.env` (copy `.env.example`) — a free **Groq** key alone turns
   on LLM extraction/diagnosis, demo answers, and outreach/content polish (all on the
   free bulk tier). Optional: Gemini (fallback), Anthropic (frontier diagnosis only,
   ₹1,000/mo cap). Verify the provider model IDs (see `KNOWN_LIMITATIONS.md #2`).
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
