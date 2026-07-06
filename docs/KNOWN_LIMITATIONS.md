# Known Limitations & Technical Debt

Intentional shortcuts and rough edges from the Week-1 build. None block the W1
deliverable; each has a note on when/how to address it.

## Engineering decisions worth revisiting

1. **Uniform httpx LLM layer (not per-vendor SDKs).** `leadscout/llm/providers.py`
   calls Groq/Gemini/OpenAI/Anthropic over one httpx interface. Rationale: the
   primary path is Groq/Gemini free tiers, the SPEC mandates a "deliberately boring,
   cheap" tool, and one HTTP shape is simpler than four SDKs. The `claude-api` skill
   prefers the official Anthropic SDK. The Anthropic call uses the correct documented
   Messages API wire format. **Swapping to the official SDK later is isolated to that
   one file.** Not yet exercised against real keys (none configured this session).

2. **Provider model IDs are best-effort defaults.** `GROQ_MODEL=llama-3.1-8b-instant`,
   `GEMINI_MODEL=gemini-flash-lite-latest`, `OPENAI_MODEL=gpt-4o-mini`, frontier
   `claude-haiku-4-5-20251001`. Verify against current provider docs before first
   paid use. Frontier defaults to Haiku 4.5 for the ₹1,000/mo cap (D5); bump to
   Sonnet/Opus if diagnosis quality needs it (config `FRONTIER_MODEL`).

3. **Discovery adapters are fragile by design (A2).** HN depends on Algolia+Firebase
   shape; YC depends on scraping a rotating Algolia key from the site (often fails →
   returns []). Both fail closed. Manual `leadscout add <domain>` is the reliable
   path. Not yet run against live HN/YC in this session (offline-safe).

4. **Heuristic extractor precision.** Keyword + word-boundary matching. Good recall,
   moderate precision — some quotes carry markdown list artifacts (e.g. leading
   "- "). Corroborating signals (funding/docs/growth) are noisier than Tier-1. LLM
   extraction (add a Groq key) raises precision. Anti-signal disqualification fires
   on a single match ≥0.6 confidence; keywords were tightened after a live false
   positive but remain heuristic — spot-check disqualifications.

5. **Company name derivation is crude** (`brief._company_name` = domain root
   capitalized). Real naming (from `<title>`/homepage) is A3 polish.

6. **Sentence splitter is regex-based** — occasionally splits awkwardly on lists.
   Fine for evidence quotes (they stay verbatim); cosmetic only.

7. **No incremental re-crawl policy.** `brief` re-uses the on-disk fetch cache; pass
   `--no-cache` to force fresh. No staleness TTL yet.

8. **Browser fallback (B7) not written.** JS-only sites yield thin text (trafilatura
   → tag-strip fallback). Single Playwright fallback is reserved; `playwright` is in
   the optional `[browser]` extra.

9. **Persistence on re-brief** clears and rewrites a domain's signals each run (last
   run wins) and appends a new `briefs` row (history kept). Artifacts are add-only.

10. **Demo "deflection rate" is a BM25 retrieval proxy** (share of tested questions
    with a top score above threshold), NOT measured live-ticket deflection. The brief
    and Loom script say so explicitly. Real deflection is what the 3-week pilot
    measures. The demo retriever is keyword BM25 (no embeddings) — good, not SOTA;
    swap in a local vector store in A6 hardening if recall matters.

11. **Dev migration shim.** `init_db` adds missing (nullable) columns to existing
    SQLite tables (`_ensure_sqlite_columns`) so additive model changes don't require a
    DB wipe. It does NOT handle drops/renames/type changes. Add Alembic before Postgres
    or any non-additive change.

12. **A7/A9 deterministic output is a first draft.** With no LLM keys, outreach and
    posts use templates — serviceable but generic; the operator edits before sending
    anyway. With a (free) Groq key they're polished on the bulk tier. Demo Q&A is
    extractive without keys (returns the top passage), LLM-generated with keys.

13. **Demo questions from tiny doc sets can be thin.** `derive_questions` pulls real
    "…?" sentences from the docs, falling back to a generic support set. Sites with
    little public help text yield fewer/weaker questions (and lower coverage).

## Environment notes

- Built/tested on Python **3.12** via `uv` (system Python is 3.14; 3.12 avoids
  lxml/trafilatura wheel gaps). `requires-python = ">=3.12"`.
- Live runs write to `data/` (git-ignored). `data/pattern_library/` IS tracked
  (proprietary source of truth).
- A commit-validation git hook (pro-workflow) is active in the environment and can
  mis-fire on non-git bash commands — unrelated to this repo.
