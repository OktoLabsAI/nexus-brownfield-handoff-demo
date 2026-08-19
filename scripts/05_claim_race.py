#!/usr/bin/env python3
"""Stage 3: the actual claim race.

Both agents call `handoff_claim` on the now-approved migration handoff
concurrently, via `asyncio.gather` -- not sequentially -- so this is a real
race against Nexus's atomic conditional UPDATE, not two calls that happen to
run one after the other. Nexus guarantees exactly one winner; the loser gets
a clean, typed rejection (not a crash, not a silent no-op).

This only produces a genuine race if the migration handoff has no `target`
restriction (see 03_schema_agent_propose.py's docstring) -- if it's scoped
to one role, there's only one eligible claimant and this script will just
show that agent winning uncontested.

Usage:
    python3 scripts/05_claim_race.py --handoff-id hof_...
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.nexus_client import NexusAgent  # noqa: E402


async def attempt_claim(prefix: str, handoff_id: str) -> dict:
    agent = NexusAgent.from_env(prefix)
    async with agent.session() as session:
        try:
            result = await agent.call(session, "handoff_claim", {"handoff_id": handoff_id})
            return {"agent": agent.agent_id, "outcome": "claimed", "result": result}
        except RuntimeError as e:
            return {"agent": agent.agent_id, "outcome": "rejected", "error": str(e)}


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--handoff-id", required=True)
    args = parser.parse_args()

    results = await asyncio.gather(
        attempt_claim("SCHEMA", args.handoff_id),
        attempt_claim("API", args.handoff_id),
    )
    print(json.dumps(results, indent=2))

    winners = [r for r in results if r["outcome"] == "claimed"]
    if len(winners) == 1:
        print(f"\nExactly one winner: {winners[0]['agent']}. Race resolved correctly.")
    elif len(winners) == 0:
        print("\nNo winner -- handoff may not have been OPEN yet (check it was approved first).")
    else:
        print("\nWARNING: more than one winner -- this would be a real bug if it happens.")


if __name__ == "__main__":
    asyncio.run(main())
