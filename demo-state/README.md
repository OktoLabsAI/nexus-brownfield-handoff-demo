# Quick look — see the finished run without doing anything

This directory is a real, bundled snapshot of a Nexus workspace after every
stage in the main README's table actually ran — the gated proposal, the
human approval, a genuinely concurrent claim race, the dependency denial,
the completed migration, the recovered session, all of it. Point Nexus at
it and open the dashboard; you're looking at the real history, not a mockup.

## See it

```bash
pip install "okto-nexus[serve]"   # if you haven't already
okto-nexus serve --port 8210 \
  --project-root /absolute/path/to/this/repo \
  --home demo-state/nexus-home
```

Open **http://127.0.0.1:8210** in a browser. No login, no API key — Nexus's
local dashboard/REST surface doesn't require one on `127.0.0.1`. You should
see:

- Two agents: `schema-agent`, `api-agent`
- One approval, `status: approved`, with the real migration SQL and the
  reviewer's note
- Two handoffs, both `COMPLETED`, with the claim race's real winner and the
  loser's `HANDOFF_ALREADY_CLAIMED` outcome in the event history
- The dependency graph showing the second handoff was blocked until the
  first completed
- Full event timeline — `handoff.created` → `approval.requested` →
  `approval.granted` → `handoff.claimed` → `handoff.unblocked` → `handoff.completed`

`closeout-result.json` in this folder is the real close-out numbers from
this exact run (claim latency, time-to-approval), for reference —
`docs/prompts/closeout.py` regenerates the same shape from whatever's live.

Port `8210` here is deliberately different from `scripts/00_setup_nexus.sh`'s
default `8202`, so you can have this "quick look" instance and a
from-scratch run (see the main README) up at the same time without a
collision.

## What this ISN'T for

This bundled `nexus.db` has two agent identities with real API keys already
issued to them — but Nexus never stores plaintext keys, only their hashes,
so there's no key here for anyone (including us) to hand you back. That's
deliberate, not an oversight: baking a working credential into a public repo
is a bad idea even when, as here, it would only ever unlock a disposable
local SQLite file. If you want to actually **act** as an agent — call
`handoff_claim`, drive the scenario further, connect an MCP client — use the
"Run it yourself" flow in the main README instead: it registers brand-new
agent identities on a fresh instance and gives you keys nobody else has ever
seen. `.mcp.json.example` at the repo root shows the config shape once you
have those.

## Seeing real data in the admin endpoint

`GET /api/admin/metrics` only reports activity from the last 60 seconds —
see the comment in `admin.controller.ts`. A static data dump would always be
stale by the time you restored it, so instead:

```bash
psql "$DATABASE_URL" -f demo-state/seed-recent-rate-limit-events.sql
# then, within the next ~60 seconds:
curl -H "Authorization: Token <a real JWT>" http://localhost:3000/api/admin/metrics
```

This requires the app's schema to already exist (`npx prisma migrate deploy`
in `app/`, per the main README) and the app server itself running
(`nx serve`) to actually hit the endpoint.
