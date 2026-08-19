#!/usr/bin/env python3
"""Stage 4: API Agent's own handoff, gated by `depends_on` -- not by a policy
check. Requires `feature_dag=true` (set in 00_setup_nexus.sh).

Two modes:

  create      Create API Agent's "build admin metrics endpoint" handoff with
              depends_on=[<migration_handoff_id>], then immediately attempt
              to claim it. Expected: DEPENDENCY_NOT_MET, because the
              migration handoff isn't COMPLETED yet. The new handoff should
              also be absent from `handoff_list_available` for api-agent.

  claim       Attempt the claim again, presumably after the migration
              handoff has been completed (07_complete_and_unblock.py). This
              should now succeed.

Usage:
    python3 scripts/06_api_agent_dependent.py create --migration-handoff-id hof_...
    python3 scripts/06_api_agent_dependent.py claim --handoff-id hof_...
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.nexus_client import NexusAgent  # noqa: E402


async def cmd_create(migration_handoff_id: str) -> None:
    agent = NexusAgent.from_env("API")
    async with agent.session() as session:
        created = await agent.call(
            session,
            "handoff_create",
            {
                "subject": "Build GET /api/admin/metrics rate-limit reporting endpoint",
                "description": (
                    "Reads RateLimitEvent to report per-route request counts and "
                    "blocked counts. Depends on the RateLimitEvent table existing, "
                    "so this can't be claimed until the migration handoff completes."
                ),
                "depends_on": [migration_handoff_id],
            },
        )
        print("== handoff_create ==")
        print(json.dumps(created, indent=2))
        handoff_id = created.get("data", created).get("handoff_id") or created.get("handoff_id")

        print("\n== immediate handoff_list_available (should NOT include the new handoff) ==")
        available = await agent.call(session, "handoff_list_available", {})
        print(json.dumps(available, indent=2))

        print("\n== early handoff_claim attempt (expect DEPENDENCY_NOT_MET) ==")
        try:
            claim = await agent.call(session, "handoff_claim", {"handoff_id": handoff_id})
            print(json.dumps(claim, indent=2))
            print("\nWARNING: expected this to be denied -- check the migration handoff's actual status.")
        except RuntimeError as e:
            print(f"Denied as expected: {e}")
        print(f"\nSave this handoff_id for later: {handoff_id}")


async def cmd_claim(handoff_id: str) -> None:
    agent = NexusAgent.from_env("API")
    async with agent.session() as session:
        result = await agent.call(session, "handoff_claim", {"handoff_id": handoff_id})
        print(json.dumps(result, indent=2))


async def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_create = sub.add_parser("create")
    p_create.add_argument("--migration-handoff-id", required=True)

    p_claim = sub.add_parser("claim")
    p_claim.add_argument("--handoff-id", required=True)

    args = parser.parse_args()
    if args.cmd == "create":
        await cmd_create(args.migration_handoff_id)
    else:
        await cmd_claim(args.handoff_id)


if __name__ == "__main__":
    asyncio.run(main())
