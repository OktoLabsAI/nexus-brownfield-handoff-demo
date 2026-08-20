# nexus-brownfield-handoff-demo

![Two agents. One coordination layer.](docs/images/banner.svg)

One migration. Two independent agents. A coordination layer that decides who gets to touch it, and when.

A small real feature, built on a real codebase, governed end-to-end by Okto Nexus.

[About Okto Nexus](#about-okto-nexus) · [The Problem](#the-problem) · [How It Works](#how-it-works) · [Nexus in Action](#nexus-in-action) · [Architecture](#architecture) · [Repository Structure](#repository-structure) · [Workspace & Demo Data](#workspace--demo-data) · [Roles](#roles) · [Tools Used](#tools-used) · [Prerequisites](#prerequisites) · [Quickstart](#quickstart) · [Running the Target App](#running-the-target-app-app) · [Handoff Stages](#handoff-stages) · [Where to Find Artifacts](#where-to-find-artifacts) · [Contributing & Licensing](#contributing--licensing) · [Conclusion](#conclusion)

## About Okto Nexus

Okto Nexus is a local-first coordination layer for teams running multiple AI coding agents - runs on your own machine, no account required. It doesn't write code or specs; it governs how agents claim work, hand it to each other, get gated by policy, and get approved by a human before anything risky ships.

Every agent shares one durable coordination bus: who owns a task, what needs sign-off, what's blocked until its dependencies clear. Agents talk to it over MCP; humans watch the same workspace in a web dashboard.

Independent of Okto Pulse - no shared code, config, or service. Pulse is just a design precedent.

## The Problem

Running more than one AI agent against the same codebase surfaces the same four failure modes every time - not because the agents are bad, but because nothing in a chat session was ever designed to coordinate with another chat session. This repo tests each one directly, not just describes it:

| Failure mode | Where it shows up here | Why it happens |
|---|---|---|
| Two agents claim the same task | Both Schema Agent and API Agent are eligible to claim the migration handoff | No atomic single-winner rule - two agents polling for work will occasionally grab the same item at the same instant, and both proceed believing they own it |
| Risky actions ship because nobody asked | Schema Agent's migration touches a live database | An agent that can act, will act - nothing pauses it for a human unless something structurally sits in the way; "the agent decided to" ends up being the entire audit trail |
| A dependency nobody enforces is a suggestion | API Agent building the admin endpoint before `RateLimitEvent` exists | A comment or a task description saying "do this after that" is just text - it doesn't stop an agent that's ready to work from building against a table that isn't there yet |
| Coordination context dies with the session | API Agent's session gets killed mid-build (stage 7) | A chat transcript isn't durable storage - kill the process and every decision, claim, and piece of in-progress state made inside it is gone with it |

Nexus's handoffs, approval policies, and dependency graph exist specifically to close these four gaps - structurally, not by asking agents to remember a rule.

## How It Works

**The feature.** `app/` is a fork of the RealWorld blogging API - users, articles, comments. This repo adds two dependent pieces:

- **`RateLimitEvent` table** - one migration. Records which endpoint got hit, from where, by whom. Nothing writes to it automatically; it's a tracking table, not enforcement. No request actually gets blocked.
- **`GET /api/admin/metrics`** - one endpoint. Reads that table for the last 60 seconds, reports hit counts, flags if over a hardcoded threshold.

That's it. Small on purpose - a schema change plus an endpoint that depends on it is the minimum shape needed to exercise Nexus's approval gate and dependency graph. The coordination is the point, not the feature.

**Schema Agent** proposes and applies the migration. **API Agent** builds the endpoint, dependent on it existing.

1. **Propose, intercepted.** Schema Agent calls `handoff_create`. A bound `require_approval` policy redirects it into the approvals queue instead of creating it.
2. **Human approves.** SQL and reasoning visible in the dashboard. Approval re-executes the call - handoff now `OPEN`, claimable.
3. **Both race for it.** Nexus's atomic claim guarantees exactly one winner. The winner applies the migration for real.
4. **The other task is structurally blocked.** API Agent's handoff has `depends_on` the migration. Any claim before it's `COMPLETED` is refused with `DEPENDENCY_NOT_MET`.
5. **Unblocked, API Agent builds** the endpoint for real, and completes its handoff.
6. **Durability.** A claimed-but-unfinished task survives a killed session - a fresh connection recovers everything from Nexus's own record.
7. **Close-out.** A script reads the event log for claim latency, rejection counts, time-to-approval.

## Nexus in Action

`demo-state/` is a real, bundled Nexus workspace snapshot from a completed run - not a mockup. It shows:

- **Approval queue** - migration proposal, `status: approved`, real SQL and reasoning attached
- **Claim race** - both agents' `handoff_claim` attempts, one accepted, one rejected with `HANDOFF_ALREADY_CLAIMED`
- **Dependency graph** - API Agent's handoff blocked until the migration completed
- **Full event timeline** - `handoff.created` → `approval.requested` → `approval.granted` → `handoff.claimed` → `handoff.unblocked` → `handoff.completed`

See [`demo-state/README.md`](demo-state/README.md) for how to view it - no login or key needed.

**Coordination graph** - schema-agent, api-agent, and operator nodes with their latest actions

![Coordination graph: schema-agent, api-agent, and operator nodes with their latest actions](docs/images/screenshots/graph.png)

**Handoffs board** - both handoffs `COMPLETED`, with the dependency between them shown

![Handoffs board: both handoffs COMPLETED, with the dependency between them shown](docs/images/screenshots/handoffs.png)

**Event timeline** - the full `handoff.created` → `approval.granted` → `handoff.claimed` → `handoff.completed` sequence

![Event timeline: the full handoff.created to approval.granted to handoff.claimed to handoff.completed sequence](docs/images/screenshots/events.png)

**Agent messages** - api-agent notifying schema-agent that the dependent handoff completed

![Agent messages: api-agent notifying schema-agent that the dependent handoff completed](docs/images/screenshots/messages.png)

## Architecture

```mermaid
flowchart TD
    A[Schema Agent: handoff_create<br/>subject + SQL in description] --> B{require_approval policy<br/>on handoff_create matches}
    B -->|intercepted| C[Pending in approvals queue<br/>SQL + reasoning visible]
    C -->|human approves| D[handoff_create replays:<br/>handoff now OPEN]
    C -->|human rejects| E2[Schema Agent notified, reworks]

    D --> F{handoff_claim race<br/>both agents, concurrent}
    F -->|winner| G[Winner applies migration for real]
    F -->|loser| R1[Loser: claim rejected]

    H[API Agent: handoff_create own task<br/>depends_on = migration handoff] --> I{handoff_claim attempt}
    I -->|migration not COMPLETED| J[Denied: DEPENDENCY_NOT_MET]
    G --> K[handoff_complete migration]
    K -->|handoff.unblocked event| I
    I -->|migration COMPLETED| L[API Agent claims + builds endpoint]

    L --> M[Session killed mid-build]
    M --> N[Fresh session reconnects]
    N --> O[handoff_get + event_get/event_cursor: replay history]
    O --> P[handoff_complete]

    P --> Q[Close-out: claim latency,<br/>rejection count, time-to-approval]

    style B fill:#b45309,stroke:#451a03,color:#ffffff
    style C fill:#b45309,stroke:#451a03,color:#ffffff
    style F fill:#b91c1c,stroke:#450a0a,color:#ffffff
    style G fill:#15803d,stroke:#052e16,color:#ffffff
    style I fill:#b91c1c,stroke:#450a0a,color:#ffffff
    style L fill:#15803d,stroke:#052e16,color:#ffffff
    style Q fill:#1d4ed8,stroke:#172554,color:#ffffff
```

1. **Propose → gate**: an ordinary call, silently redirected by a bound policy.
2. **Approve → open**: only a human turns a pending proposal into a claimable handoff.
3. **Race → single winner**: an atomic conditional update decides it, not a lock either agent has to know to take.
4. **Dependency → structural block**: unclaimable, not just unwise to claim, until `COMPLETED`.
5. **Recovery → the record, not the memory**: reconstructed entirely from `handoff_get`/`event_get`.

## Repository Structure

| Path | Purpose |
|---|---|
| `app/` | Forked Node/Express/Prisma backend (`gothinkster/node-express-realworld-example-app`) |
| `demo-state/` | Bundled Nexus workspace snapshot from a completed run |
| `docs/decisions/` | Fork conventions read before either agent touched the codebase |
| `docs/walkthrough.md` | Step-by-step guide from clone to closed-out run |
| `docs/prompts/` | Prompt for each stage, in order, plus the close-out script |
| `scripts/` | Deterministic clients for every coordination call |
| `docker-compose.yml` | Optional Postgres for the target app |
| `.env.example` | Every env var the scripts need |
| `.mcp.json.example` | Template MCP client config |
| `LICENSE` | Project license |

## Workspace & Demo Data

| Field | Value |
|---|---|
| Repo / demo name | `nexus-brownfield-handoff-demo` (informal - Nexus IDs workspaces by hashed `project_root`, not a display name) |
| Target application | `app/` (fork of `gothinkster/node-express-realworld-example-app`) |
| Agents | `schema-agent`, `api-agent` |
| Bundled snapshot | Approval approved, both handoffs `COMPLETED`, all 8 stages run |

## Roles

| Identity | Can do | Cannot do |
|---|---|---|
| Schema Agent | Proposes the migration, races to claim it, applies it | Cannot approve its own `handoff_create` |
| API Agent | Proposes its dependent task, races to claim the migration, builds the endpoint once unblocked | Cannot claim its own handoff until the migration is `COMPLETED` |
| Operator (human) | Attaches the policy, approves/rejects | No MCP identity beyond the reserved `operator` agent |

Two separate MCP connections, separate credentials - not one identity switching hats.

## Tools Used

| Tool | Used for |
|---|---|
| `handoff_create` | Propose the migration (policy-gated) and the dependent task |
| `handoff_claim` | The race; the dependent task's early-denied then later-allowed claim |
| `handoff_complete` | Closing out each task |
| `handoff_get` / `event_get` / `event_cursor` | Recovery; close-out timing |
| `artifact_put` | Optionally recording the applied SQL - not policy-gated |

Attaching policy and deciding approvals is dashboard/REST-only - never exposed to agents.

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.11+ | `pip install "okto-nexus[serve]"` |
| Node.js 18+ | Required by the target app |
| Docker (optional) | For `docker-compose.yml`'s Postgres |
| Two separate agent connections | Do not share credentials |
| `feature_dag` enabled | Required for `depends_on` - the setup script sets this |

## Quickstart

1. Install Okto Nexus:

```bash
pip install "okto-nexus[serve]"
```

2. Clone and install script dependencies:

```bash
git clone https://github.com/Infrasity-Labs/nexus-brownfiled-use-case.git
cd nexus-brownfiled-use-case
python3 -m venv .venv && source .venv/bin/activate
pip install -r scripts/requirements.txt
cp .env.example .env
```

3. Set up and run:

```bash
export NEXUS_PROJECT_ROOT="$(pwd)"
bash scripts/00_setup_nexus.sh
python3 scripts/01_register_agents.py   # copy the printed keys into .env
export $(grep -v '^#' .env | xargs)
python3 scripts/02_bind_policy.py
```

Then follow [`docs/walkthrough.md`](docs/walkthrough.md), stage by stage. To look at a finished run instead, see [`demo-state/README.md`](demo-state/README.md).

## Running the target app (`app/`)

1. Bring up Postgres:

```bash
docker compose up -d
```

2. Install and apply the schema:

```bash
cd app
npm install
export DATABASE_URL=postgresql://realworld:realworld@localhost:5433/realworld
npx prisma migrate deploy
```

3. Start the app:

```bash
npm start   # bare `nx serve` fails without a global nx install
```

See `app/FORK_NOTES.md` and `docs/decisions/0001-fork-conventions.md` for conventions read before either agent touched this codebase.

## Handoff Stages

| Stage | What happens | Script / prompt |
|---|---|---|
| 0. Setup | Install + start Nexus, register agents, bind policy | `scripts/00_setup_nexus.sh`, `01_register_agents.py`, `02_bind_policy.py` |
| 1. Propose (gated) | Migration `handoff_create` intercepted into approvals | `scripts/03_schema_agent_propose.py` / `docs/prompts/01-schema-agent-propose.md` |
| 2. Approve | Human approves; handoff `OPEN` | `scripts/04_list_and_approve.py` |
| 3. Claim race | Both agents `handoff_claim` concurrently; one wins | `scripts/05_claim_race.py` |
| 4. Early-claim denial | Dependent handoff refused with `DEPENDENCY_NOT_MET` | `scripts/06_api_agent_dependent.py create` / `docs/prompts/03-api-agent-dependent-task.md` |
| 5. Apply + complete | Migration applied for real, marked complete | `docs/prompts/02-schema-agent-apply-migration.md`, `scripts/07_complete_and_unblock.py` |
| 6. Unblock + build | API Agent claims + builds the endpoint | `scripts/06_api_agent_dependent.py claim` / `docs/prompts/04-api-agent-build-endpoint.md` |
| 7. Kill + recovery | Killed session's replacement recovers and finishes | `scripts/08_kill_and_recover.py` / `docs/prompts/05-recovery.md` |
| 8. Close-out | Claim latency, rejection count, time-to-approval | `docs/prompts/closeout.py` |

Run end to end against a live instance, both agents genuinely racing - real numbers in `demo-state/closeout-result.json`.

## Where to Find Artifacts

- `demo-state/nexus-home/nexus.db` - real workspace snapshot, open the dashboard directly
- `demo-state/closeout-result.json` - real close-out numbers
- `docs/walkthrough.md` - stage-by-stage instructions
- `docs/prompts/` - the actual prompt for each stage
- `docs/decisions/` - fork conventions read before either agent touched `app/` (`0001-fork-conventions.md`)
- `app/` - the forked backend where the migration and endpoint live

## Contributing & Licensing

To reproduce or iterate: fork this repo, run `scripts/01_register_agents.py` against your own Nexus instance, connect your own Schema Agent and API Agent.

Provided under the included `LICENSE` (Elastic License 2.0).

## Conclusion

Built on Okto Nexus, an OktoLabs product. Structural separation between proposing, approving, claiming, and executing - enforced by the coordination layer itself, not a prompt either agent has to remember to follow.

<br/>

---

<div align="center">
  <p>
    Built on <a href="https://github.com/OktoLabsAI/okto-nexus"><b>Okto Nexus</b></a>, open-source local-first agent coordination.
    <br/>
    <a href="https://github.com/OktoLabsAI/okto-nexus/blob/main/LICENSE">Source (Elastic License 2.0)</a> &nbsp;·&nbsp;
    <a href="https://docs.oktolabs.ai">Documentation</a> &nbsp;·&nbsp;
    <a href="https://oktolabs.ai">OktoLabs</a>
  </p>
</div>
