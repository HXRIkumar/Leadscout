# Decisions Needed (business input)

> Autonomous-build policy: I did **not** block on any of these. For each I made the
> recommendation I believe is best, implemented using it, and recorded it here.
> Review, override where you disagree; most are cheap to change.

Legend: **Change cost** = how expensive it is to reverse later.

---

## D1 — Pilot price ($2,500)
- **Question:** What is the pilot price for the support-deflection wedge?
- **Recommendation (implemented):** **$2,500**, 3 weeks.
- **Alternatives considered:** $500–$1,000 (low-friction, "yes" is easy, but signals
  cheap/hobbyist and underprices funded buyers); $3,000+ (top of SPEC §14 pilot band,
  more friction on a first cold relationship).
- **Why this default:** These are *post-raise* companies (seed–Series A); $2,500 is a
  <5% bet against ~$58k/yr of deflectable support load (A5), high enough to signal
  seriousness and filter tire-kickers, low enough to be a fast "yes."
- **Change cost:** Cheap — one line in `kernel/niche.yaml`.

## D2 — Primary buyer (Founder/CTO vs Head of Support)
- **Question:** Who is the economic buyer we address the offer to?
- **Recommendation (implemented):** **Founder/CTO** as economic buyer; **Head of
  Support/CX** as champion. Outreach is framed as "free your eng team from building this."
- **Alternatives:** Lead with Head of Support (owns the pain, but often lacks budget
  authority at 15–80-person cos and may see a bot as a threat to headcount).
- **Why this default:** At this size the founder/CTO owns the build-vs-buy /
  eng-bandwidth tradeoff, which is exactly the wedge. Champion path stays open.
- **Change cost:** Cheap — messaging + `niche.yaml:icp.buyer`.

## D3 — Geography / compliance scope
- **Question:** "International, English-operating" is broad. Which regions do we
  actually cold-contact, given per-region compliance (SPEC §4.6)?
- **Recommendation (implemented):** Start with **US, UK, CA, AU, IE, NZ, SG** (the
  regions with defined compliance rules in `compliance/region_rules.md`). English-
  operating startups elsewhere allowed for *research/warm*; EU consent-only states
  (DE, AT seed list) excluded from cold outreach by default.
- **Alternatives:** Truly global cold outreach (legal risk, undefined rules) — rejected.
- **Why:** Matches V1's compliant region set; keeps the moat (reputation) safe.
- **Change cost:** Moderate — add region rules + re-verify per country before first send.

## D4 — Warm-network seed (NEEDS YOUR INPUT — genuinely can't fill)
- **Question:** Who do you actually know, and which communities are you active in?
  This decides whether warm intros exist on day one (SPEC §2.4 warm-first channel).
- **Recommendation:** Import LinkedIn 1st-degree connections + past colleagues/clients
  + any founder/operator communities you're in, into the `contacts` table (A8) with a
  warmth rating. I've built the schema (`contacts`, `interactions`) and reserved A8;
  I **cannot** populate it — this is personal knowledge.
- **Why not blocking:** A8 is a Week 2–3 module; Week 1 (`brief`) does not need it.
- **Change cost:** N/A — it's data entry you do when you wake up. See `NEXT_STEPS.md`.

## D5 — Cost-model defaults (deflectable 35%, $55k/rep, $8/ticket)
- **Question:** Are the A5 cost-of-problem defaults defensible?
- **Recommendation (implemented):** deflectable_fraction=0.35, loaded_cost/rep=$55k,
  cost/ticket=$8, fallback support_headcount=3. All in `kernel/niche.yaml`.
- **Alternatives:** Higher deflection (50%+) sells harder but is less defensible on a
  call; region-specific salary bands (more accurate, more complexity — deferred).
- **Why:** Conservative numbers you can defend without flinching; the estimator
  overrides them per-company from public evidence when available.
- **Change cost:** Cheap — `niche.yaml`, tune from real engagement data (feeds C2).

## D6 — Headline promise framing ("35% deflection" vs "$X saved")
- **Question:** Lead with the % deflected or the $ saved?
- **Recommendation (implemented):** Headline = **"35% of repetitive support tickets
  deflected"**; the $ figure is computed per-company by A5 and shown in the brief.
- **Why:** A single portable % travels well in content/outreach; the personalized $
  number lands in the 1:1 brief where it's backed by their own evidence.
- **Change cost:** Cheap.

## D7 — Frontier provider = OpenAI (RESOLVED by operator, 2026-07-06)
- **Question:** Which frontier provider powers premium reasoning (diagnosis, demo
  generation, proposal/architecture)?
- **Decision (implemented):** **OpenAI**, default model **`gpt-5-mini`**.
- **Rationale (operator):** Already has a paid OpenAI account; no paid Anthropic
  account; uses Claude Code for development, so paying for the Anthropic API would
  duplicate capability without clear added ROI.
- **Model choice:** `gpt-5-mini` is a lightweight GPT-5 reasoning model — right-sized
  for the diagnosis/demo workload and cheap ($0.25/$2 per 1M tok in/out) against the
  ₹1,000/mo cap. Use `gpt-5` for maximum quality, `gpt-5-nano` for cheapest.
- **Reversibility:** Trivial and code-free — set `FRONTIER_PROVIDER=anthropic` +
  `FRONTIER_MODEL=<claude model>`. The Anthropic adapter + budget prices are retained.
- **Change cost:** Cheap (env vars only).

## D8 — Data-source compliance boundary (RESOLVED by engineering, 2026-07-07)
- **Question:** The "lead-gen upgrade" goal lists LinkedIn, G2, Capterra, Crunchbase,
  Reddit, Product Hunt as data sources. Which do we automate?
- **Decision (implemented):** Split by compliance.
  - **Automate (compliant):** company sites, official docs, careers, pricing,
    blog/changelog, **RSS/Atom feeds**, official **GitHub REST API**, **SEC EDGAR**,
    HN (official APIs), YC (public index), sitemaps, and a **keyed web-search API**
    (Brave/SerpAPI) when a key is present. Tech-stack fingerprinting from a site's own
    public HTML is compliant.
  - **Never automate (manual link-outs only):** **LinkedIn** (SPEC §3.5 Never Build —
    ToS + hiQ precedent + Proxycurl shutdown), **G2 / Capterra** (ToS bar commercial
    scraping), **Reddit** (commercial API is paid/gated), **Crunchbase** (ToS/paid API),
    **Product Hunt** (API is non-commercial-use only). These are surfaced as
    pre-filled manual-research URLs the operator opens by hand (V1 §7.7 pattern).
- **Why:** the platform's moat is *reputation*; a ToS ban or litigation would be
  catastrophic and is explicitly a Never-Build. Compliant sources + manual link-outs
  deliver the same intelligence without the risk.
- **Reversibility:** if the operator later licenses an official API (e.g. Crunchbase
  paid, Reddit commercial), add it as a normal compliant adapter — the source
  interface is additive. Change cost: cheap per source.

---

_No item here blocked the build. D4 is the only one still requiring your personal
knowledge (D7, D8 resolved). Bulk tiers (Groq/Gemini) remain the free primary path;
OpenAI is used only for the ~30-50 curated frontier calls._
