"""Reserved intelligence seams (SPEC §3.2/§3.3, §4.4).

These modules are architecturally present now (Protocols + schema) but implemented
only at their stated triggers. Category C cannot exist until capture (A10/A11) has
accumulated data — the capture substrate is built now, the mining arrives later.

- scorer.py   B5  — Lead scoring (V1 formula preserved as seed; disabled in flow)
- winloss.py  C1  — Win/loss analysis (>=5-10 closed outcomes)
- pricing.py  C2  — Price-to-win model (After 10 clients)
- patterns.py C3  — Cross-engagement pattern discovery (After 10 clients)
- relgraph.py C4  — Relationship intelligence (After 10 / 50 clients)
"""
