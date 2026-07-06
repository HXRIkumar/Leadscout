"""LeadScout CLI (SPEC §4.1).

Binary: `leadscout`. Week-1 live commands: brief, scout, add, companies, kernel,
budget, initdb. Later-phase commands (demo, draft, post, warm, pipeline, capture)
are present as reserved stubs so the UX shape is stable from day 1.
"""

from __future__ import annotations

import json as _json

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(add_completion=False, help="LeadScout v2 — consulting intelligence platform.")
console = Console()


@app.command()
def initdb() -> None:
    """Create the SQLite database and all tables (idempotent)."""
    from .db import init_db
    init_db()
    console.print("[green]Database initialized.[/green]")


@app.command()
def kernel() -> None:
    """Show the loaded niche & offer kernel (A1)."""
    from .kernel import KernelNotFound, load_kernel
    try:
        k = load_kernel()
    except KernelNotFound as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None
    t = Table(title="Niche & Offer Kernel", show_header=False, box=None)
    t.add_row("[bold]Vertical[/bold]", k.icp.vertical.strip())
    t.add_row("[bold]Stage / size[/bold]", f"{k.icp.stage} · {k.icp.size}")
    t.add_row("[bold]Geography[/bold]", ", ".join(k.icp.geography))
    t.add_row("[bold]Buyer[/bold]", k.icp.buyer)
    t.add_row("[bold]Problem[/bold]", k.problem.name.strip())
    t.add_row("[bold]Offer[/bold]", f"{k.offer.headline_number} · {k.offer.pilot.price} / {k.offer.pilot.weeks} weeks")
    t.add_row("[bold]Archetype[/bold]", k.offer.archetype)
    console.print(t)


@app.command()
def brief(
    url: str = typer.Argument(..., help="Company URL or domain, e.g. example.com"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Bypass the fetch cache"),
    no_llm: bool = typer.Option(False, "--no-llm", help="Force deterministic (no LLM) path"),
) -> None:
    """brief <url> — evidence-verified diagnosis + costed pain (Week-1 deliverable)."""
    from .research.brief import build_brief
    res = build_brief(url, use_cache=not no_cache, use_llm=not no_llm)
    dx, cost = res.diagnosis, res.cost

    header = f"[bold]{res.company_name}[/bold]  ([cyan]{res.domain}[/cyan])"
    if dx.disqualified:
        body = f"[red]⛔ DISQUALIFIED[/red] — {dx.disqualify_reason}"
    else:
        body = (
            f"[bold]Bottleneck[/bold]\n{dx.bottleneck}\n\n"
            f"[bold]Wedge[/bold]\n{dx.wedge}\n\n"
            f"[bold]AI-readiness[/bold]: {dx.readiness_qualitative} — {dx.readiness_reason}\n"
            f"[bold]Cost of problem[/bold]: {cost.headline}\n"
            f"[dim]{cost.method}[/dim]"
        )
    console.print(Panel(f"{header}\n\n{body}", title="Diagnosis", expand=False))

    pos = [s for s in res.signals if not s.is_anti_signal]
    console.print(f"\n[bold]Verified evidence[/bold] ({len(pos)} claim(s), "
                  f"{res.runlog.signals_rejected_unverified if res.runlog else 0} rejected):")
    for s in pos[:8]:
        console.print(f"  • [green]{s.signal_type}[/green] ({s.confidence:.0%}): “{s.evidence_quote[:120]}”")
        console.print(f"    [dim]{s.source_url}[/dim]")
    if not pos:
        console.print("  [yellow]No positive signals passed verification.[/yellow]")

    console.print(f"\n[bold]Brief written:[/bold] {res.brief_path}")


@app.command()
def scout(
    limit: int = typer.Option(50, help="Max candidates per source"),
    as_json: bool = typer.Option(False, "--json", help="Emit candidates as JSON"),
) -> None:
    """scout — Discovery Lite: assemble/refresh a hand-fit candidate list (A2)."""
    from .sources import discover
    cands = discover(limit=limit)
    if as_json:
        console.print_json(_json.dumps([c.__dict__ for c in cands]))
        return
    if not cands:
        console.print("[yellow]No candidates (adapters may be offline or keys rotated). "
                      "Add manually: leadscout add <domain>[/yellow]")
        return
    t = Table(title=f"Discovery Lite — {len(cands)} candidates")
    t.add_column("domain", style="cyan")
    t.add_column("name")
    t.add_column("source")
    for c in cands:
        t.add_row(c.domain, c.name[:40], c.source)
    console.print(t)


@app.command()
def add(
    domain: str = typer.Argument(..., help="Domain to add to the candidate list"),
    name: str = typer.Option("", help="Company name"),
    desc: str = typer.Option("", help="Short description"),
) -> None:
    """Manually add an in-niche company (A2: HN/YC + manual adds)."""
    from .sources.discovery import add_manual
    c = add_manual(domain, name or None, desc)
    console.print(f"[green]Added[/green] {c.domain} ({c.name})")


@app.command()
def companies(all_: bool = typer.Option(False, "--all", help="Include disqualified")) -> None:
    """List candidate companies in the pipeline."""
    from .sources.discovery import list_candidates
    rows = list_candidates(include_disqualified=all_)
    t = Table(title=f"Companies ({len(rows)})")
    t.add_column("domain", style="cyan")
    t.add_column("name")
    t.add_column("sources")
    t.add_column("disqualified")
    for r in rows:
        t.add_row(r.domain, (r.name or "")[:40], r.sources_seen or "", r.disqualified_reason or "")
    console.print(t)


@app.command()
def budget() -> None:
    """Show budget guard counters (frontier ₹, Groq/day, Hunter/mo)."""
    from .llm.budget import BudgetGuard
    snap = BudgetGuard().snapshot()
    t = Table(title="Budget", show_header=True)
    t.add_column("meter")
    t.add_column("used")
    t.add_column("cap")
    t.add_row("frontier (INR/mo)", str(snap["frontier_inr"]), str(snap["frontier_cap_inr"]))
    t.add_row("groq (req/day)", str(snap["groq_today"]), str(snap["groq_cap"]))
    t.add_row("hunter (calls/mo)", str(snap["hunter_month"]), str(snap["hunter_cap"]))
    console.print(t)


# --- Loop commands: demo -> draft -> post -> warm -> pipeline / capture -------


@app.command()
def demo(
    domain: str = typer.Argument(..., help="Company domain to build a support-deflection demo for"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Bypass the fetch cache"),
    no_llm: bool = typer.Option(False, "--no-llm", help="Force extractive answers (no LLM)"),
) -> None:
    """demo <domain> — scaffold a tailored, runnable support-deflection micro-demo (A6)."""
    from .demo import scaffold_demo
    res = scaffold_demo(domain, use_cache=not no_cache, use_llm=not no_llm)
    if res.n_chunks == 0:
        console.print("[yellow]No public help/docs content found to train on. "
                      "Run `leadscout brief` first, or the site may be JS-only.[/yellow]")
        return
    console.print(Panel(
        f"[bold]{res.domain}[/bold] — {res.template_family}\n\n"
        f"Trained on [bold]{res.n_chunks}[/bold] passages · "
        f"tested [bold]{res.n_questions}[/bold] questions · "
        f"confident coverage [bold]{res.deflection_rate*100:.0f}%[/bold] (BM25 proxy)\n\n"
        f"Demo folder: {res.demo_path}\n"
        f"Try it: [dim]python {res.demo_path}/answer.py \"How do I get started?\"[/dim]",
        title="Micro-demo scaffolded", expand=False,
    ))
    for a in [a for a in res.rag.answers if a.deflectable][:3]:
        console.print(f"  • [green]Q[/green] {a.question}")
        console.print(f"    [dim]{a.answer[:110]}…[/dim]")


@app.command()
def draft(
    domain: str = typer.Argument(..., help="Company domain (must have a brief already)"),
    country: str = typer.Option("", help="Contact country (drives compliance region)"),
    name: str = typer.Option("", help="Contact first name"),
    no_llm: bool = typer.Option(False, "--no-llm", help="Deterministic draft (no LLM polish)"),
) -> None:
    """draft <domain> — 1:1 outreach draft anchored on a verified fact (A7). Sent manually."""
    from .outreach.compliance import region_for_country
    from .outreach.draft import NoBriefError, draft_message
    region = region_for_country(country or None)
    try:
        res = draft_message(domain, region=region, contact_name=name, use_llm=not no_llm)
    except NoBriefError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None
    tag = "[green]sendable[/green]" if res.sendable else f"[red]BLOCKED: {res.block_reason}[/red]"
    console.print(Panel(res.cold_message, title=f"Cold draft — {res.domain} · region {res.region.value} · {tag}", expand=False))
    console.print(Panel(res.warm_intro, title="Warm-intro-request variant", expand=False))
    if not country:
        console.print("[yellow]No --country given; defaulted to US (opt-out). Verify region before sending.[/yellow]")


@app.command()
def post(
    domain: str = typer.Argument(..., help="Company domain (must have a brief)"),
    no_llm: bool = typer.Option(False, "--no-llm", help="Deterministic posts (no LLM polish)"),
) -> None:
    """post <domain> — repurpose a (redacted) brief/demo into niche posts (A9)."""
    from .distribution.content import NoBriefError, repurpose_brief
    try:
        res = repurpose_brief(domain, use_llm=not no_llm)
    except NoBriefError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None
    for i, p in enumerate(res.posts, 1):
        console.print(Panel(p, title=f"Post draft {i} (redacted)", expand=False))
    console.print(f"[dim]Logged to {res.log_path}[/dim]")


@app.command()
def warm() -> None:
    """warm — reactivation-due contacts, warmest first (A8)."""
    from .distribution.warm import reactivation_due
    due = reactivation_due()
    if not due:
        console.print("[yellow]No contacts due (or none imported). "
                      "Add with `leadscout warm-add` / `leadscout warm-import <csv>`.[/yellow]")
        return
    t = Table(title=f"Reactivation due ({len(due)})")
    t.add_column("id")
    t.add_column("name")
    t.add_column("company")
    t.add_column("warmth")
    t.add_column("last touch")
    for c in due:
        t.add_row(str(c.id), c.name[:30], (c.company or "")[:30], c.warmth or "", str(c.last_touch or "never"))
    console.print(t)


@app.command(name="warm-add")
def warm_add(
    name: str = typer.Argument(..., help="Contact name"),
    company: str = typer.Option("", help="Company"),
    source: str = typer.Option("", help="How you know them (provenance)"),
    warmth: str = typer.Option("warm", help="hot | warm | cold"),
) -> None:
    """Add one warm contact (A8)."""
    from .distribution.warm import add_contact
    cid = add_contact(name, company=company or None, source=source or None, warmth=warmth)
    console.print(f"[green]Contact #{cid}[/green] {name} added ({warmth}).")


@app.command(name="warm-import")
def warm_import(path: str = typer.Argument(..., help="CSV: name,company,source,warmth,channel")) -> None:
    """Import warm contacts from a CSV (A8)."""
    from .distribution.warm import import_csv
    n = import_csv(path)
    console.print(f"[green]Imported {n} contacts[/green] from {path}.")


@app.command()
def pipeline() -> None:
    """pipeline — CRM-lite digest: follow-ups due + funnel counts (A10)."""
    from rich.markdown import Markdown

    from .pipeline.digest import build_digest
    console.print(Markdown(build_digest()))


@app.command()
def promote(
    domain: str = typer.Argument(..., help="Company domain to promote to a lead"),
    contact: str = typer.Option("", help="Contact name"),
    email: str = typer.Option("", help="Contact email"),
    source: str = typer.Option("", help="Contact source (GDPR provenance — required to send)"),
) -> None:
    """Promote a researched company to a lead (A10)."""
    from .pipeline.crm import promote_to_lead
    lead_id = promote_to_lead(domain, contact_name=contact or None, contact_email=email or None,
                              contact_source=source or None)
    console.print(f"[green]Lead #{lead_id}[/green] for {domain} (status: shortlisted)")


@app.command()
def advance(
    lead_id: int = typer.Argument(..., help="Lead id"),
    status: str = typer.Argument(..., help="Target status (e.g. contacted, replied, call_booked, won, lost)"),
    note: str = typer.Option("", help="Optional note"),
) -> None:
    """Advance a lead's lifecycle status (validated transitions, A10)."""
    from .pipeline.crm import advance as _advance
    try:
        new = _advance(lead_id, status, note or None)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None
    console.print(f"[green]Lead #{lead_id} -> {new}[/green]")


@app.command()
def capture() -> None:
    """capture — sync the pattern library into the DB (A11 substrate; rest Week 3)."""
    from .capture import sync_pattern_library
    n = sync_pattern_library()
    console.print(f"[green]Synced {n} patterns[/green] from data/pattern_library/ into the `patterns` table.")


if __name__ == "__main__":
    app()
