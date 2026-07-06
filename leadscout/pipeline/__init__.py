"""A10 — Pipeline CRM-lite + follow-up. RESERVED (Week 3).

Custom SQLite (overrules the CPO doc's Notion/HubSpot, SPEC §3.1 A10): every
Category C module mines this store, so the moat substrate must be owned, not rented.
The lifecycle state machine and follow-up rule (retained V1) are defined now in
crm.py; the digest + interactive flow are Week 3.
"""

from .crm import (  # noqa: F401
    FOLLOW_UP_BUSINESS_DAYS,
    LIFECYCLE_TRANSITIONS,
    MAX_FOLLOW_UPS,
    next_status,
)
