"""Technology-stack detection from a site's own public HTML (compliant).

Fingerprints support/helpdesk widget vendors (Intercom, Zendesk, Gorgias, …) from
the fetched raw HTML — a strong, specific Tier-1 support signal for the niche
("they run Intercom, so humans field repetitive questions"). Evidence is the
vendor's own fingerprint string, verbatim in the page HTML, so it passes the same
fail-closed verifier as every other claim (SPEC §4.1).

Operates only on pages we already fetched compliantly — no new network calls.
"""

from __future__ import annotations

from ..research.fetch import FetchResult
from .extract import RAG, SignalCandidate

# vendor -> fingerprint substrings (each >= 12 chars so it survives the verifier).
SUPPORT_WIDGETS: dict[str, list[str]] = {
    "Intercom": ["widget.intercom.io", "intercomcdn.com", "intercomsettings"],
    "Zendesk": ["static.zdassets.com", "ekr.zdassets.com", "zendesk.com/embeddable"],
    "Gorgias": ["gorgias.chat", "config.gorgias"],
    "Help Scout": ["beacon-v2.helpscout.net"],
    "Front": ["chat.frontapp.com"],
    "Freshchat": ["wchat.freshchat.com", "freshchat.com"],
    "Drift": ["js.driftt.com"],
    "Crisp": ["client.crisp.chat"],
    "Tidio": ["code.tidio.co"],
    "Olark": ["static.olark.com"],
    "HubSpot Service": ["js.hs-scripts.com"],
}


def detect_widgets(results: list[FetchResult]) -> list[SignalCandidate]:
    """Emit one support_widget SignalCandidate per detected vendor (deduped)."""
    out: list[SignalCandidate] = []
    seen: set[str] = set()
    for r in results:
        html = r.html or ""
        low = html.lower()
        for vendor, fps in SUPPORT_WIDGETS.items():
            if vendor in seen:
                continue
            for fp in fps:
                idx = low.find(fp)
                if idx == -1:
                    continue
                snippet = html[idx: idx + len(fp)]  # verbatim, original-case
                out.append(SignalCandidate(
                    signal_type="support_widget",
                    evidence_quote=snippet,
                    source_url=r.url,
                    confidence=0.85,
                    mapped_project=RAG,
                    meta={"vendor": vendor},
                ))
                seen.add(vendor)
                break
    return out
