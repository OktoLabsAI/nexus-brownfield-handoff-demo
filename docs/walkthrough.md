# Walkthrough — clone to finished

End-to-end steps to run this demo on your own machine. Every coordination
call is a script in `scripts/`; every code-writing step has a matching
prompt in `docs/prompts/` to hand to a coding agent. You can also run the
coordination scripts standalone (no LLM at all) to see the mechanics without
any code getting written.

## 0. Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (for the target app's Postgres) — or your own Postgres if you'd
  rather skip `docker-compose.yml`

```bash
git clone <this-repo>
cd nexus-brownfield-handoff-demo-repo
python3 -m venv .venv && source .venv/bin/activate
pip install -r scripts/requirements.txt
cp .env.example .env
```

## 1. Bring up the target app's database

```bash
docker compose up -d
cd app
npm install
export DATABASE_URL=postgresql://realworld:realworld@localhost:5433/realworld
npx prisma migrate deploy   # applies the base RealWorld schema, before either agent's change
cd ..
```

`app/` has no `.env.example` of its own -- it reads `DATABASE_URL` straight
from the environment (see `app/src/prisma/schema.prisma`'s `datasource`
block), so exporting it as above is enough.

## 2. Bring up Nexus and register the two agent identities

```bash
export NEXUS_PROJECT_ROOT="$(pwd)"
bash scripts/00_setup_nexus.sh
python3 scripts/01_register_agents.py
```

Copy the printed `SCHEMA_AGENT_ID` / `SCHEMA_API_KEY` / `API_AGENT_ID` /
`API_API_KEY` into `.env`. Then:

```bash
export $(grep -v '^#' .env | xargs)
python3 scripts/02_bind_policy.py
```

Confirm the policy bound correctly (the script prints a verification call;
if it 404s, check the dashboard's agent detail page instead).

## 3. Stage 1 — propose the migration (gated)

Either run the script directly:

```bash
python3 scripts/03_schema_agent_propose.py
```

or hand `docs/prompts/01-schema-agent-propose.md` to a coding agent
connected as `schema-agent`. Either way, expect a `pending_approval`
response, not a created handoff.

## 4. Stage 2 — approve it

```bash
# find your workspace_id
curl -s http://127.0.0.1:8202/api/v1/workspaces | python3 -m json.tool

python3 scripts/04_list_and_approve.py --workspace <workspace_id>
# note the approval_id from the listing, then:
python3 scripts/04_list_and_approve.py --workspace <workspace_id> \
  --approval-id apr_... --decision approve --note "SQL looks right"
```

(Or use the dashboard's approvals queue — same effect.) The migration
handoff should now be `OPEN`. Note its `handoff_id`.

## 5. Stage 3 — the claim race

```bash
python3 scripts/05_claim_race.py --handoff-id <migration_handoff_id>
```

Expect exactly one `claimed` and one `rejected` in the output. Note which
agent won.

## 6. Stage 4 — API Agent's dependent task, denied early

```bash
python3 scripts/06_api_agent_dependent.py create --migration-handoff-id <migration_handoff_id>
```

Expect a `DEPENDENCY_NOT_MET`-style denial on the immediate claim attempt.
Note the printed `handoff_id` for API Agent's own task — you'll need it in
step 8.

## 7. Stage 5 — apply the migration for real, complete the handoff

Hand `docs/prompts/02-schema-agent-apply-migration.md` to whichever agent
won the race in step 5 (check the winner from that step's output — it's not
necessarily Schema Agent). It'll run `prisma migrate dev` for real and then
either call `handoff_complete` itself or you can finish with:

```bash
python3 scripts/07_complete_and_unblock.py --winner <schema|api> \
  --handoff-id <migration_handoff_id> \
  --result "Applied RateLimitEvent migration; see app/src/prisma/migrations/<ts>_add_rate_limit_event/migration.sql"
```

## 8. Stage 6 — unblock and build

```bash
python3 scripts/06_api_agent_dependent.py claim --handoff-id <api_agent_handoff_id>
```

Should now succeed. Then hand `docs/prompts/04-api-agent-build-endpoint.md`
to API Agent to actually write `admin.controller.ts` and its test.

## 9. Stage 7 — kill and recover

```bash
python3 scripts/08_kill_and_recover.py start --handoff-id <some_handoff_id>
# once it prints CLAIMED, actually kill this process (Ctrl+C)

# then, as a genuinely separate process:
python3 scripts/08_kill_and_recover.py recover --handoff-id <some_handoff_id> \
  --result "Recovered and finished: <what was actually done>"
```

Or drive this through two separate agent sessions using
`docs/prompts/05-recovery.md` for the second one.

## 10. Stage 8 — close out

```bash
python3 docs/prompts/closeout.py --api-key "$API_API_KEY" --project-root "$NEXUS_PROJECT_ROOT"
```

Prints claim latency, rejection count, and time-to-approval derived from the
real event log.

## A note on trust

At every "have an agent do X" step above, the corresponding prompt tells the
agent to verify its own coordination claims against real tool responses
rather than reporting what it expects to have happened. This isn't
boilerplate caution — a prior run of this exact demo caught an agent session
fabricating three `handoff_complete`/`handoff_get` responses in a row while
the underlying file work was genuinely done. If something in your run looks
too clean, don't take the agent's word for it — call `handoff_get`/
`event_get` yourself and check.
