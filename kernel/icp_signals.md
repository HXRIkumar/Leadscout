# ICP signals — what "the problem is present" looks like from public data

> These are the observable, verbatim-quotable signals the Research Engine (A3) and
> Diagnosis (A4) look for. Each maps to a pain pattern in `data/pattern_library/`.
> Every signal used in a brief MUST carry a verbatim quote + source URL (SPEC §4.1).

## Tier 1 — direct support-load signals (strongest)

| Signal | Where it shows up publicly | Maps to pattern |
|---|---|---|
| Support/CX roles being hired | `/careers`, `/jobs`, job boards | `support-team-scaling-manually` |
| Public help center that is thin / stale / gappy | `/help`, `/docs`, `/support`, KB | `help-center-gaps` |
| Public complaints about slow/poor support | G2, Trustpilot, Reddit, forum (manual) | `slow-support-response` |
| Support widget present (Intercom/Zendesk/…) | homepage HTML, `/help` | `human-answered-repetitive-qs` |

## Tier 2 — corroborating growth/pressure signals

| Signal | Where it shows up publicly | Maps to pattern |
|---|---|---|
| Rapid customer/user growth language + small team | homepage, blog, about | `growth-outpacing-support` |
| Community forum with unanswered questions | Discourse, community subdomain | `community-self-support-gap` |
| Changelog/product velocity outpacing docs | `/changelog`, `/blog`, docs dates | `docs-lagging-product` |
| Funding event (fresh budget) | Form D, press, blog | `funded-can-afford` (corroborating only) |

## Anti-signals (push toward disqualification)

- Product headline is about AI/LLM/agents → disqualifier #1.
- No help/docs/support surface at all → disqualifier #2.
- "Agency", services pricing, > ~120 headcount → disqualifier #3.

## How signals become a diagnosis

1. Research Engine fetches public pages, extracts candidate signals **with verbatim
   quotes**, and drops any quote it cannot find verbatim in the fetched text.
2. Diagnosis matches verified signals against the pattern library to name the
   **bottleneck**, the **wedge** (a RAG deflection bot), and a **qualitative
   AI-readiness** read.
3. The cost estimator attaches a defensible dollar figure (A5).

Nothing enters a brief that isn't backed by a quote the operator can click through to.
