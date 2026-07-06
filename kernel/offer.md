# Offer — one costed problem, one number

> This is the human-readable companion to `niche.yaml`. The YAML is what the code
> reads; this file is what you say on a call. Keep them in sync.

## The wedge (chosen 2026-07-06)

**Support deflection.** Of the three candidate problems (support / documents /
workflow), support deflection is the only one that is *both* **legible from public
data** (help-center size, support hiring, public complaints) *and* **demo-able from
public data alone** (a RAG bot trained on their own help center). The other two
require insider information you only get on a call — they are upsells, not the wedge.

## The one-liner

> "You're answering the same 30 support questions by hand. I'll build you an
> assistant, trained on your own docs, that deflects about **35%** of those
> tickets — and I'll prove it on your real top-20 questions in **3 weeks** for
> **$2,500**."

## The offer, as numbers

| Field | Value |
|---|---|
| Headline promise | **35% of repetitive support tickets deflected** |
| Demo archetype | `rag_support_bot` |
| Pilot price | **$2,500** |
| Pilot length | **3 weeks** |
| Pilot deliverable | Working assistant on their help center + docs, measured deflection on their real top-20 questions, deployed to a shareable test surface, production rollout plan |

## How the number is defended (A5 cost-of-problem)

The pilot price is trivially justified against the cost of the problem:

```
annual_support_cost_at_risk = support_headcount × loaded_annual_cost_per_rep × deflectable_fraction
                            = 3 × $55,000 × 0.35   (defaults)
                            ≈ $57,750 / year of support load
```

A $2,500 pilot against ~$58k/yr of deflectable load is a <5% bet for the buyer.
The estimator overrides `support_headcount` (and the whole formula) whenever public
evidence gives a better number (e.g. "we're hiring 5 support engineers", or a
publicly stated ticket volume triggers the alternate per-ticket formula).

## Entry motion (SPEC §14)

Paid pilot ($2,500) → scoped build ($5k–$20k, `RAG support chatbot` band) →
15–25%/yr maintenance retainer. Compliance-heavy buyers (+20–50%) and CRM/helpdesk
integration (+$10k–$50k) are upsells, not part of the wedge.

## What this offer is NOT

- Not "AI consulting" (generalist).
- Not document processing or workflow automation (those are post-pilot upsells).
- Not for AI-native companies (they build it themselves — see `disqualifiers.md`).
