# Suppression policy (SPEC §13)

The suppression list is the global gate checked **before every send**.

## Rules

1. **Any opt-out is permanent.** On any "stop / unsubscribe / do not contact",
   add an `opt_outs` row (email and/or domain) with `permanent = true`, immediately.
2. **Checked pre-send.** `outreach.compliance.is_suppressed(email, domain)` and
   `may_contact(region, email, domain)` run before any message is sent.
3. **Domain-level suppression** applies to the whole company, not just one address.
4. **No re-adds.** A suppressed contact/domain is never re-surfaced for outreach.
5. **Bounces & complaints** are treated as opt-outs.

## Data captured per opt-out

`email`, `domain`, `date`, `permanent`, `reason` (see the `opt_outs` table).

## Provenance (paired requirement)

Every contacted address must carry a `contact_source` (how it was found) — GDPR
provenance. A contact without a recorded source is not sendable.
