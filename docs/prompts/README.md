# Agent prompts

The `scripts/` directory handles every *coordination-layer* call
(`handoff_create`, `handoff_claim`, `handoff_complete`, `event_get`, policy
setup, approval decisions) deterministically - no LLM in that loop, on
purpose. See the main README's note on the fabrication finding: an agent
session self-reporting "I called handoff_complete" is not proof it happened,
so the calls that matter for the demo's own claims are scripted, not
prompted.

What *is* prompted is the actual engineering work - writing the Prisma
migration, writing the endpoint, writing tests - because that's the part
Nexus isn't meant to do either. These files are the prompts for whichever
coding agent you point at `app/` (Claude Code, Cursor, etc.), one per stage,
meant to be given verbatim (or lightly adapted) to that agent's session.

Each prompt tells the agent which script to run before/after it for the
coordination step, and - critically - tells it to verify its own coordination
claims against a real `handoff_get`/`event_get` call rather than trusting
its own memory of having made one.

| File | Stage | Agent |
|---|---|---|
| `01-schema-agent-propose.md` | 1 | Schema Agent |
| `02-schema-agent-apply-migration.md` | 5 | Schema Agent (or whichever agent wins the claim race) |
| `03-api-agent-dependent-task.md` | 4 | API Agent |
| `04-api-agent-build-endpoint.md` | 6 | API Agent |
| `05-recovery.md` | 7 | API Agent (fresh session) |
| `closeout.py` | 8 | n/a - deterministic script, not a prompt |
