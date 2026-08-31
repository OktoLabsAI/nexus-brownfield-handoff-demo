#!/usr/bin/env python3
"""Stage 5: the claim-race winner applies the migration for real, then
completes the migration handoff. Completion is what fires `handoff.unblocked`
and clears API Agent's dependency (stage 4/6).

Before running this, actually apply the migration against the target DB:

    cd app
    npx prisma migrate dev --name add_rate_limit_event

Then run this script with the winning agent's identity and the result text
describing what was actually done -- don't complete a handoff with a result
string that doesn't match real on-disk changes. (See the README's note on
the fabrication finding from the original run: this is the exact call a
session could lie about, so if you're driving this from an AI coding agent
rather than running the script directly, verify the migration file exists
on disk before trusting a "done" claim.)

Usage:
    python3 scripts/07_complete_and_unblock.py \\
        --winner schema \\
        --handoff-id hof_... \\
        --result "Applied RateLimitEvent migration; see app/src/prisma/migrations/<ts>_add_rate_limit_event/migration.sql"
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.nexus_client import NexusAgent  # noqa: E402


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--winner", choices=["schema", "api"], required=True)
    parser.add_argument("--handoff-id", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--record-artifact", action="store_true", help="also artifact_put the migration SQL")
    parser.add_argument("--sql-file", default=None)
    args = parser.parse_args()

    prefix = "SCHEMA" if args.winner == "schema" else "API"
    agent = NexusAgent.from_env(prefix)
    async with agent.session() as session:
        if args.record_artifact:
            if not args.sql_file:
                raise SystemExit("--record-artifact requires --sql-file")
            sql = Path(args.sql_file).read_text()
            artifact = await agent.call(
                session,
                "artifact_put",
                {"artifact_type": "text", "name": "migration.sql", "content": sql},
            )
            print("== artifact_put ==")
            print(json.dumps(artifact, indent=2))

        result = await agent.call(
            session, "handoff_complete", {"handoff_id": args.handoff_id, "result": args.result}
        )
        print("== handoff_complete ==")
        print(json.dumps(result, indent=2))
        print("\nThis should have fired handoff.unblocked -- API Agent can now claim its dependent handoff.")


if __name__ == "__main__":
    asyncio.run(main())
