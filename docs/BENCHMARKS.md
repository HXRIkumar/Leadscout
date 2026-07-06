# Benchmarks

Recorded results from live runs (real APIs: OpenAI `gpt-5-mini` frontier, Groq bulk
fallback). Evidence-verified counts are post-fail-closed (verbatim + anti-signal gate).
Cost is the shared ₹1,000/mo frontier budget.

## Extraction recall — heuristic vs LLM (plausible.io)

| Mode | Verified claims | Rejected (fail-closed) | Notes |
|---|---:|---:|---|
| Heuristic only (`--no-llm`) | 3 | — | keyword-anchored; high precision, low recall |
| LLM (Groq bulk) | 10 | 1 | far higher recall; some loose labels |
| LLM (OpenAI frontier extraction) | 10 | 3 | precision tier; anti-signal gate drops 2 mislabels |

## Diagnosis quality — v1 vs v2 (consultant-grade), plausible.io, `gpt-5-mini`

| Field | v1 | v2 (consultant-grade) |
|---|---|---|
| bottleneck / wedge / readiness | ✅ | ✅ |
| business summary | ✗ | ✅ "team of 10, best month ever April 2026…" |
| pain points | ✗ | ✅ 3, each evidence-tied |
| AI + automation opportunities | ✗ | ✅ |
| estimated ROI | ✗ | ✅ "35% of $57,750/yr = $20,212/yr; $2,500 pilot ≈ 8.1× first-year ROI" |
| implementation complexity | ✗ | ✅ `low` |
| recommended project | implicit | ✅ `rag_support_bot` |
| outreach angle | ✗ | ✅ cites "April 2026 best month ever" |
| proposal outline | ✗ | ✅ 6 sections |

## Cost (live)

| Run | Frontier spend | Notes |
|---|---:|---|
| Provider smoke (OpenAI + Groq) | ₹0.02 | 2 calls |
| 2 briefs + 12-Q&A demo (Session 3) | ₹1.32 total | `gpt-5-mini` ≈ $0.016 |
| Per consultant brief (extraction+diagnosis on frontier) | ≈ ₹0.5–0.8 | ~30–50/mo ⇒ well under ₹1,000 cap |

## Tech-stack / support-widget detection (live)

| Site | Server HTML | Detected |
|---|---|---|
| gorgias.com | 274 KB | ✅ Gorgias (`gorgias.chat`) |
| helpscout.com | 974 KB | ✗ (beacon JS-injected — needs browser fallback) |

Precision: high (specific vendor fingerprints, verbatim-verified). Recall: bounded to
server-rendered loaders; JS-injected widgets need `USE_BROWSER_FALLBACK` (B7).

## Test suite

| Checkpoint | Tests | Lint |
|---|---:|---|
| Initial build | 25 | clean |
| + A10/A11/A6/A7/A8/A9/B7 | 44 | clean |
| + OpenAI switch + anti-signal gate + router tests | 53 | clean |
| + consultant-grade diagnosis | 54 | clean |
| + tech-stack / widget detection | 57 | clean |
| + opportunity scoring + ranking | 60 | clean |
| + manual research link-outs | 62 | clean |
| + documentation-quality scoring | 64 | clean |

_Method: runs are cache-first; live briefs use the on-disk fetch cache to stay polite
(≥2s/domain, robots-honored). Numbers above are from plausible.io and tailscale.com,
the two live test targets._
