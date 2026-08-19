#!/usr/bin/env python3
"""Stage 1: Schema Agent proposes the migration handoff.

Schema Agent puts the actual migration SQL directly in the handoff's
`description` and calls `handoff_create`. Because of the policy bound in
02_bind_policy.py, Nexus intercepts this call automatically -- the agent
never "asks for approval"; it just tries to create the handoff, and Nexus
decides to hold it. The response comes back as a pending_approval envelope
instead of a created handoff.

IMPORTANT -- target scoping: `target` is a required field on `handoff_create`
(confirmed against the real tool schema) -- there's no "leave it unset"
option. This uses `{"strategy": "broadcast"}` so BOTH schema-agent and
api-agent are eligible claimants once it's approved -- that's what makes
05_claim_race.py in the next stage an actual, concurrent race between the
two of them, not a claim by whichever one happens to be eligible.

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

# This is the actual migration already sitting in
# app/src/prisma/migrations/20260817131700_add_rate_limit_event/migration.sql
# -- kept identical here on purpose. The approval queue is supposed to show a
# human the real SQL that's about to run; an earlier draft of this script had
# a placeholder table shape here that didn't match the file actually applied,
# which would have made the "human reviews the real SQL" story a lie.
MIGRATION_SQL = (
    Path(__file__).parent.parent
    / "app/src/prisma/migrations/20260817131700_add_rate_limit_event/migration.sql"
).read_text()


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
                "target": {"strategy": "broadcast"},
                "visibility": "public",
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
