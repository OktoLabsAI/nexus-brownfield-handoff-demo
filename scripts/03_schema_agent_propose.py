#!/usr/bin/env python3
"""Stage 1: Schema Agent proposes the migration handoff.

Schema Agent puts the actual migration SQL directly in the handoff's
`description` and calls `handoff_create`. Because of the policy bound in
02_bind_policy.py, Nexus intercepts this call automatically -- the agent
never "asks for approval"; it just tries to create the handoff, and Nexus
decides to hold it. The response comes back as a pending_approval envelope
instead of a created handoff.

IMPORTANT -- target scoping: this is deliberately created with an
unrestricted target (no `target` filter) so that BOTH schema-agent and
api-agent are eligible claimants once it's approved. In the original run of
this demo, the migration handoff was scoped to `target: {strategy: role,
role: api}`, which meant only api-agent could ever claim it -- collapsing
the claim race in stage 3 to a single eligible agent. Leaving target unset
here is what makes 05_claim_race.py an actual race.

Usage:
    python3 scripts/03_schema_agent_propose.py
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.nexus_client import NexusAgent  # noqa: E402

MIGRATION_SQL = """\
-- AlterTable / CreateTable, following this fork's Prisma migration style
-- (see docs/decisions/0001-fork-conventions.md). Generate the real version
-- with `npx prisma migrate dev --name add_rate_limit_event` inside app/ --
-- this literal is what goes in the handoff description for the approval
-- queue to show a human, not a substitute for actually running prisma.
CREATE TABLE "RateLimitEvent" (
    "id" TEXT NOT NULL,
    "userId" TEXT,
    "route" TEXT NOT NULL,
    "windowStart" TIMESTAMP(3) NOT NULL,
    "requestCount" INTEGER NOT NULL DEFAULT 1,
    "blocked" BOOLEAN NOT NULL DEFAULT false,
    CONSTRAINT "RateLimitEvent_pkey" PRIMARY KEY ("id")
);

ALTER TABLE "RateLimitEvent" ADD CONSTRAINT "RateLimitEvent_userId_fkey"
    FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE SET NULL ON UPDATE CASCADE;
"""


async def main() -> None:
    agent = NexusAgent.from_env("SCHEMA")
    async with agent.session() as session:
        result = await agent.call(
            session,
            "handoff_create",
            {
                "subject": "Add RateLimitEvent table for API rate-limiting",
                "description": (
                    "Adds a RateLimitEvent Prisma model + migration to support "
                    "per-user, per-route rate limiting. Reasoning: rate-limit "
                    "counters need to survive process restarts and be queryable "
                    "by the admin metrics endpoint (see the dependent handoff), "
                    "so this belongs in Postgres, not in-memory.\n\n"
                    "-- migration.sql --\n" + MIGRATION_SQL
                ),
                # No `target` -- deliberately unrestricted, see module docstring.
            },
        )
        print(json.dumps(result, indent=2))
        print(
            "\nIf `status` above is `pending_approval`, this worked correctly -- "
            "the policy caught it. Go approve it with scripts/04_list_and_approve.py "
            "(or the dashboard) before running the claim race."
        )


if __name__ == "__main__":
    asyncio.run(main())
