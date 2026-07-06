# Region outreach rules (SPEC §4.6 / §13)

Binding on all outreach volumes. Encoded in `leadscout/outreach/compliance.py`
(`Region`, `REGION_RULES`, `region_for_country`). At ≤10 sends/day this is cheap
discipline; it also future-proofs sending infrastructure (B9).

| Region | Basis | May cold-email? | Hard requirements |
|---|---|---|---|
| **US** (`us_optout`) | CAN-SPAM (opt-out) | Yes | Accurate From/subject · physical postal address in footer · working opt-out honored ≤10 days |
| **UK** (`uk_lia`) | PECR corporate-subscriber + UK GDPR legitimate interest | Yes | Documented LIA (`compliance/LIA.md`) · opt-out in every mail · sole traders = consent-required |
| **EU LI-friendly** (`eu_lia`) | GDPR legitimate interest | Yes | Documented LIA · strictly role-relevant · instant opt-out honoring |
| **EU consent-only** (`consent_only`) | Consent | **No** | Excluded by default (seed list: DE, AT — verify per country before first send) |
| **Canada** (`ca_cpub`) | CASL conspicuous-publication exception | Yes | Business email published without a no-contact statement · message relates to their role · record basis on the contact |
| **AU / NZ / SG** (`apac_cpub`) | Conspicuous-publication regimes | Yes | Same conspicuous-publication discipline as Canada · record basis per contact |

## Global rules (every send)

1. Suppression list checked **before every send** (`is_suppressed`).
2. Every opt-out recorded permanently (`opt_outs` table).
3. One thread + **max 2 follow-ups** per lead (`pipeline.crm.MAX_FOLLOW_UPS`).
4. Identity always accurate.
5. `contact_source` recorded for every address (GDPR provenance) — mandatory.

## Unknown country

Defaults to `us_optout` (opt-out basis with full footer) — the safest broadly-legal
posture — but **verify the actual country before the first send**. Consent-only
states are never defaulted into.

## Never Build (SPEC §3.5)

Mass/generic automated outreach and automated LinkedIn scraping are permanently
excluded. LinkedIn is a manual, in-browser research/relationship surface only.
