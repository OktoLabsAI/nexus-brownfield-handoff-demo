# nexus-brownfield-handoff-demo

![Two agents. One coordination layer.](docs/images/banner.svg)

One migration. Two independent agents. A coordination layer that decides who gets to touch it, and when.

A real feature (API rate-limiting plus an admin metrics endpoint) built on a real existing codebase, governed end-to-end by Okto Nexus.

[About Okto Nexus](#about-okto-nexus) · [The Problem](#the-problem) · [How It Works](#how-it-works) · [Nexus in Action](#nexus-in-action) · [Architecture](#architecture) · [Repository Structure](#repository-structure) · [Workspace & Demo Data](#workspace--demo-data) · [Roles](#roles) · [Tools Used](#tools-used) · [Prerequisites](#prerequisites) · [Quickstart](#quickstart) · [Running the Target App](#running-the-target-app-app) · [Handoff Stages](#handoff-stages) · [Where to Find Artifacts](#where-to-find-artifacts) · [Contributing & Licensing](#contributing--licensing) · [Conclusion](#conclusion)

## About Okto Nexus

Okto Nexus is a local-first coordination layer for teams running multiple AI coding agents, running on your own machine with no account required. It doesn't write code or specs. It governs how agents claim work, hand it to each other, get gated by policy, and get approved by a human before anything risky ships.

In plain terms: instead of two agents stepping on each other, or a human manually relaying context between chat windows, Nexus gives every agent a shared, durable coordination bus with structural rules — who owns a task, what needs a human sign-off, and what's excluded until its dependencies are done. Agents interact with all of this through MCP; humans can watch the exact same workspace in a web dashboard.

Nexus is architecturally and operationally independent of Okto Pulse — no import, network call, config flag, or service reference connects the two. Pulse is only a design precedent Nexus's visual style and a few naming conventions were mirrored from.

## The Problem

AI agents are good at doing work. They're not naturally good at *not doing the same work twice*, *not touching something risky without asking*, or *remembering what happened after a session dies*.

Four specific failure modes this repo is built to test directly, not just describe:

- **Two agents can claim the same task.** Without a single-winner rule, both proceed, and now there are two conflicting implementations of the same thing.
- **Risky actions ship because nobody was asked.** A schema change, a delete, a deploy — if nothing pauses it for a human, "the agent decided to" is the whole audit trail.
- **A dependency nobody enforces is a suggestion.** A rule that only warns doesn't stop an agent from building against a schema that doesn't exist yet.
- **Coordination context dies with the session.** Kill an agent mid-task and whoever picks it up next is starting from zero.

Nexus is built with handoffs, approval policies, and a dependency graph specifically meant to close these gaps. This repo doesn't take that at face value; it pushes on each one directly, on a real feature, and reports what actually happened.

## How It Works

This repo adds rate-limiting to an existing backend API, plus an admin endpoint that reports rate-limit metrics, using two independent AI agents connected to the same Nexus workspace: **Schema Agent** (proposes and applies the database migration) and **API Agent** (builds the admin endpoint, dependent on the migration existing).

1. **Schema Agent proposes, but is intercepted.** It calls `handoff_create` with the migration SQL in the description. An operator has attached a `require_approval` policy to Schema Agent's `handoff_create` calls, so this doesn't create the handoff — Nexus parks it in the approvals queue instead. The agent never chooses to "ask for approval"; it just tries to act, and Nexus decides to hold it.
2. **A human approves it.** The pending proposal sits in the dashboard with the full SQL and Schema Agent's reasoning visible. Approval re-executes the original call — the handoff now exists, `OPEN`, claimable.
3. **Both agents race for it.** Nexus's atomic claim guarantees exactly one winner; the loser gets a clean, typed rejection, not a crash or a silent no-op. The winner applies the migration for real against the target app.
4. **API Agent's own task is structurally blocked, not policed.** Its handoff for the admin endpoint is created with `depends_on` set to the migration handoff. Any claim attempt before that dependency is `COMPLETED` is refused with `DEPENDENCY_NOT_MET` — no human, and no policy check, has to catch this by hand.
5. **Once unblocked, API Agent builds the endpoint** — for real, following the existing codebase's route and auth conventions — and completes its handoff.
6. **Durability under failure.** A claimed-but-unfinished task survives a killed session: a fresh connection with zero prior context recovers exactly what was claimed and what already happened, purely from Nexus's own record, and finishes the work.
7. **Close-out.** A small script reads the event log directly to report claim latency, rejection counts, and time-to-approval for the run.

## Nexus in Action

`demo-state/` in this repo is not a mockup — it's a real, bundled Nexus workspace snapshot from a completed run of this exact scenario. Point Nexus at it and open the dashboard (see [Quickstart](#quickstart)) and you're looking at:

- **The approval queue** — the migration proposal, `status: approved`, the real SQL and Schema Agent's reasoning still attached
- **The claim race** — both agents' `handoff_claim` attempts on the same handoff, one accepted, one rejected with `HANDOFF_ALREADY_CLAIMED`
- **The dependency graph** — API Agent's handoff showing `depends_on` the migration, blocked until it completed
- **The full event timeline** — `handoff.created` → `approval.requested` → `approval.granted` → `handoff.claimed` → `handoff.unblocked` → `handoff.completed`, in order, with real timestamps

No login, no API key, nothing to configure — Nexus's local dashboard doesn't gate reads on `127.0.0.1`.

## Architecture

Two agent identities, Schema Agent and API Agent, both connected to the same Nexus workspace over MCP, with a policy and a dependency structurally separating what each can do without a human.

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

**Reading the flow**

1. **Propose → gate**: Schema Agent's `handoff_create` is not a request for approval — it's an ordinary call that a bound policy silently redirects into the approvals queue.
2. **Approve → open**: only a human decision turns the pending proposal into a real, claimable handoff. Rejecting sends Schema Agent a notice, not a silent drop.
3. **Race → single winner**: an atomic conditional update, not a lock either agent has to know to take, decides the claim.
4. **Dependency → structural block**: API Agent's handoff is unclaimable — not just unwise to claim — until the migration handoff is `COMPLETED`. This is enforced by the coordination layer itself, not by a rule an agent has to remember to check.
5. **Recovery → the record, not the memory**: a killed session's replacement reconstructs state entirely from `handoff_get`/`event_get`, never from anything held in a chat transcript.

## Repository Structure

| Path | Purpose |
|---|---|
| `README.md` | This document |
| `app/` | Forked Node/Express/Prisma backend (`gothinkster/node-express-realworld-example-app`) |
| `app/FORK_NOTES.md` | Fork setup notes |
| `demo-state/` | Bundled Nexus workspace snapshot (`nexus-home/nexus.db`) from a completed run — see `demo-state/README.md` |
| `docs/decisions/` | Fork conventions read before either agent touched the codebase (Prisma/PostgreSQL, JWT auth, `nx`-based build) |
| `docs/walkthrough.md` | Step-by-step guide from clone to closed-out run |
| `docs/prompts/` | The actual prompts for each stage, in order, plus the close-out script |
| `scripts/` | Deterministic clients for every coordination call — setup, propose, approve, claim race, dependency denial, complete, kill + recover |
| `docker-compose.yml` | Optional compose for the target app's Postgres |
| `.env.example` | Every env var the scripts need |
| `.mcp.json.example` | Template MCP client config for connecting as `schema-agent` / `api-agent` |
| `LICENSE` | Project license |

## Workspace & Demo Data

| Field | Value |
|---|---|
| Workspace name | `nexus-brownfield-handoff-demo` |
| Target application | `app/` (fork of `gothinkster/node-express-realworld-example-app`) |
| Agents | `schema-agent`, `api-agent` |
| Bundled snapshot checkpoint | Approval: approved, Migration handoff: `COMPLETED`, Dependent handoff: `COMPLETED`, all 8 stages executed |

This snapshot is intended to let you look at the finished pipeline immediately, and to exercise the target app once you apply its migrations.

## Roles

Nexus enforces role separation through policy and target scoping, not just instructions either agent could ignore.

| Identity | Can do | Cannot do |
|---|---|---|
| Schema Agent | Proposes the migration (SQL in the handoff description), races to claim it once approved, applies it | Cannot approve its own `handoff_create` — that's a human-only decision once the policy intercepts it |
| API Agent | Proposes its own dependent task, races to claim the migration, builds the endpoint once unblocked | Cannot claim its own handoff while the migration handoff isn't `COMPLETED` |
| Operator (human, dashboard/REST) | Attaches the `require_approval` policy; approves/rejects pending proposals | Has no MCP identity of its own beyond the reserved `operator` agent |

This repo uses two agent identities specifically, each a separate MCP connection with its own credentials, not a shared identity switching hats — that would defeat the separation at the connection level, not just the permission level.

## Tools Used

The real MCP tools this workflow runs on:

| Tool | Used for |
|---|---|
| `handoff_create` | Schema Agent proposes the migration (gated by policy); API Agent proposes its dependent task |
| `handoff_claim` | Both agents race on the migration; API Agent's early (denied) and later (allowed) claim on its own task |
| `handoff_complete` | Closing out each task |
| `handoff_get` / `event_get` / `event_cursor` | Recovering state after a session interruption; close-out timing |
| `artifact_put` | Optionally recording applied SQL as an artifact — not policy-gated (`require_approval` only attaches to `handoff_create`/`message_create`, confirmed live) |

Policy and guardrail administration (attaching `require_approval`, approving/rejecting) is dashboard/REST-only — deliberately not exposed to agents, so an agent can never grant its own exception.

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.11+ | Required by Okto Nexus (`pip install "okto-nexus[serve]"`) |
| Node.js 18+ | Required by the target app |
| Docker (optional) | For `docker-compose.yml`'s Postgres, or point `DATABASE_URL` at your own |
| Two separate agent connections | Schema Agent, API Agent; do not share credentials |
| `feature_dag` enabled | Required for `depends_on` to be enforced — the setup script sets this |

## Quickstart

1. Install Okto Nexus:

```bash
pip install "okto-nexus[serve]"
```

2. Clone this repo and install the script dependencies:

```bash
git clone https://github.com/Infrasity-Labs/nexus-brownfiled-use-case.git
cd nexus-brownfiled-use-case
python3 -m venv .venv && source .venv/bin/activate
pip install -r scripts/requirements.txt
cp .env.example .env
```

3. Look at the finished run first — no setup required:

```bash
okto-nexus serve --port 8210 --project-root "$(pwd)" --home demo-state/nexus-home
```

Open **http://127.0.0.1:8210** and browse the real approval, the claim race, and the full event history. See [`demo-state/README.md`](demo-state/README.md).

4. To run it yourself against a fresh workspace instead:

```bash
export NEXUS_PROJECT_ROOT="$(pwd)"
bash scripts/00_setup_nexus.sh
python3 scripts/01_register_agents.py   # copy the printed keys into .env
export $(grep -v '^#' .env | xargs)
python3 scripts/02_bind_policy.py
```

From here, follow [`docs/walkthrough.md`](docs/walkthrough.md) for what to do next, stage by stage.

## Running the target app (`app/`)

The `app/` service is an `nx`-managed Node/Express backend running against PostgreSQL via Prisma.

1. Bring up Postgres:

```bash
docker compose up -d
# or point DATABASE_URL at a Postgres you already have running
```

2. Install dependencies and apply the schema:

```bash
cd app
npm install
export DATABASE_URL=postgresql://realworld:realworld@localhost:5433/realworld
npx prisma migrate deploy
```

3. Start the app:

```bash
nx serve
```

See `app/FORK_NOTES.md` and `docs/decisions/0001-fork-conventions.md` for fork-specific setup and conventions read before either agent touched this codebase.

## Handoff Stages

This is the actual execution plan the demo runs on: 8 stages, each backed by a deterministic script and, where code gets written, a matching agent prompt.

| Stage | What happens | Script / prompt |
|---|---|---|
| 0. Setup | Install + start Nexus, register agents, bind the approval policy | `scripts/00_setup_nexus.sh`, `01_register_agents.py`, `02_bind_policy.py` |
| 1. Propose (gated) | Schema Agent calls `handoff_create` for the migration, SQL in the description — intercepted into the approvals queue | `scripts/03_schema_agent_propose.py` / `docs/prompts/01-schema-agent-propose.md` |
| 2. Approve | Human approves; the migration handoff is now `OPEN` | `scripts/04_list_and_approve.py` |
| 3. Claim race | Both agents attempt `handoff_claim` concurrently; exactly one wins | `scripts/05_claim_race.py` |
| 4. Early-claim denial | API Agent's dependent handoff is refused with `DEPENDENCY_NOT_MET` until the migration completes | `scripts/06_api_agent_dependent.py create` / `docs/prompts/03-api-agent-dependent-task.md` |
| 5. Apply + complete | The migration is applied for real, then marked complete | `docs/prompts/02-schema-agent-apply-migration.md`, `scripts/07_complete_and_unblock.py` |
| 6. Unblock + build | API Agent claims its now-unblocked handoff and builds the admin metrics endpoint | `scripts/06_api_agent_dependent.py claim` / `docs/prompts/04-api-agent-build-endpoint.md` |
| 7. Session kill + recovery | A killed session's replacement recovers full state from Nexus and finishes the task | `scripts/08_kill_and_recover.py` / `docs/prompts/05-recovery.md` |
| 8. Close-out | Reports claim latency, rejection count, and time-to-approval from the real event log | `docs/prompts/closeout.py` |

**Path to completion**

1. The migration handoff is approved, claimed exactly once, applied for real, and completed.
2. The dependent handoff was genuinely refused before that completion, and genuinely accepted after.
3. The endpoint is built and its handoff completed — including once by a session that never shared memory with the one that claimed it.
4. Close-out reports real numbers pulled from the event log, not asserted ones.

This exact plan has been run against a live instance, end to end, with both agents genuinely racing for the migration claim via concurrent `handoff_claim` calls — fresh Postgres, fresh agents, no simulation. The real numbers from that run are in `demo-state/closeout-result.json`, and the run itself is what `demo-state/` bundles.

## Where to Find Artifacts

- `demo-state/nexus-home/nexus.db`: real Nexus workspace snapshot from a completed run — open the dashboard, no setup needed.
- `demo-state/closeout-result.json`: the real close-out numbers from that run.
- `docs/walkthrough.md`: what to do after cloning, stage by stage.
- `docs/prompts/`: the actual prompt for each stage, in the order you'll use them.
- `docs/decisions/`: this is a *brownfield* demo, not a greenfield one, so before either agent touched `app/`, its actual auth scheme and migration tooling were read and recorded as a decision (`0001-fork-conventions.md`) — Prisma against PostgreSQL, JWT auth via `jsonwebtoken`/`express-jwt`, not assumed from the upstream project's docs.
- `app/`: the forked Node/Express backend where the migration and admin endpoint are implemented. See `app/FORK_NOTES.md`.

## Contributing & Licensing

If you want to reproduce the demo or iterate on the scenario: fork this repo, run `scripts/01_register_agents.py` against your own Nexus instance, and connect your Schema Agent and API Agent identities.

This repository is provided under the terms of the included `LICENSE` (Elastic License 2.0) file.

## Conclusion

Built on Okto Nexus, an OktoLabs product. Structural separation between proposing, approving, claiming, and executing — enforced by the coordination layer itself, not a prompt either agent has to remember to follow.
