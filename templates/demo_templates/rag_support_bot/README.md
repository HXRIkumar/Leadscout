# Demo template — `rag_support_bot` (the kernel archetype)

The first template family (A6), matching `kernel/niche.yaml:offer.archetype`.
Scaffolded per-company in Week 2 by `leadscout/demo/scaffold.py`, customized to the
target's public help center + docs. **A human reviews everything before it's sent.**

## Intended shape (Week 2 build)

```
<company>/
  ingest.py        # pull the company's public help center + docs (reuses research.fetch)
  index.py         # chunk + embed the docs into a local vector store
  answer.py        # retrieve + LLM answer over their content (llm router)
  eval.py          # run their real top-20 questions, measure deflection rate
  app.py           # minimal shareable UI (the demo surface)
  loom_script.md   # auto-drafted walkthrough script
  README.md        # how to run + what it proves
```

## Principles

- Build only from the company's **public** data (never fabricate their private data).
- Keep it small and real — a working slice beats a polished mock.
- Every demo hardens this template (delivery IP, moat #7). demo #10 takes an hour.

> Status: template family reserved. Kernel archetype is locked to this family, so the
> Week-2 generator has a fixed target. See SPEC §3.1 A6 and prompts/demo_builder.md.
