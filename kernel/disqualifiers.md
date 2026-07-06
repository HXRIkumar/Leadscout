# Disqualifiers — who we deliberately do NOT pursue

> Mirrors `niche.yaml:disqualifiers`. A company hitting any of these is dropped in
> Discovery Lite (A2) prefilter with the reason recorded — never silently.

## 1. AI-native product companies
The core product is an LLM app / AI is the product. Their founders build LLM
systems themselves; selling them a RAG bot means competing with the buyer's own
skillset. **This is the single most important exclusion** — it is what keeps the
offer sharp and non-competitive.

*Heuristic signals:* homepage headline centers on "AI", "LLM", "GPT", "copilot",
"agents" as the product; YC tag `AI`/`ML`; job posts for ML/research engineers as
core roles.

## 2. No public support surface to deflect
If there is no help center, no support/CX hiring, and no public support complaints,
the problem we solve is not visibly present. Without a support surface there is
nothing to train a deflection bot on and nothing to anchor a diagnosis.

*Heuristic signals:* no `/help`, `/docs`, `/support`, `/faq`; no support widget;
no support/CX roles; tiny or invisible customer base.

## 3. Wrong shape of company
- **Agencies / consultancies / dev-shops** — competitors, not clients.
- **> ~120 employees** — outside the size band; likely has internal capacity.
- **Visible in-house ML-platform team** — they will build internally.

*Heuristic signals:* "agency", "consultancy", "we build software for", services
pricing; headcount estimate > 120; a staffed ML/AI platform team.

## Notes
- Disqualification is **soft data**, not deletion: the reason is stored so the
  pattern library and future re-tuning can learn from it.
- Compliance exclusions (consent-only regions) are handled separately in
  `compliance/region_rules.md`, not here.
