#!/usr/bin/env python3
"""Stage 6 + 7: API Agent claims its (now-unblocked) handoff, starts work,
gets killed mid-task, and a fresh session recovers.

Two modes, meant to be run as genuinely separate processes (not just
separate functions in one run) so "recover" can't cheat by reading in-memory
state from "start":

  start     Claims the handoff, prints a marker, then this process should be
            killed for real -- e.g. run it, and once you see "CLAIMED, now
            kill me (Ctrl+C or `kill <pid>`)", actually kill it. Don't let it
            reach handoff_complete.

  recover   Run as a brand-new process/connection with zero shared state.
            Calls handoff_get to see the still-CLAIMED handoff, then
            event_get/event_cursor to replay what happened, then finishes
            the task for real and calls handoff_complete.

Usage:
    python3 scripts/08_kill_and_recover.py start --handoff-id hof_...
    # ^ kill this process before it completes

    python3 scripts/08_kill_and_recover.py recover --handoff-id hof_... \\
        --result "Built admin.controller.ts + admin.metrics.spec.ts, verified against RateLimitEvent"
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.nexus_client import NexusAgent  # noqa: E402


async def cmd_start(handoff_id: str) -> None:
    agent = NexusAgent.from_env("API")
    async with agent.session() as session:
        result = await agent.call(session, "handoff_claim", {"handoff_id": handoff_id})
        print(json.dumps(result, indent=2))
        print(
            f"\nCLAIMED at {time.strftime('%X')}. Now simulate building for a "
            "few seconds, then kill this process (Ctrl+C) before it reaches "
            "handoff_complete. This process will now just sleep."
        )
        # Deliberately never calls handoff_complete -- the point is to die mid-task.
        while True:
            await asyncio.sleep(3600)


async def cmd_recover(handoff_id: str, result: str) -> None:
    agent = NexusAgent.from_env("API")
    async with agent.session() as session:
        print("== handoff_get (confirm it's still CLAIMED, by whom, since when) ==")
        current = await agent.call(session, "handoff_get", {"handoff_id": handoff_id})
        print(json.dumps(current, indent=2))

        print("\n== event_cursor + event_get (replay what happened on this handoff) ==")
        cursor = None
        events: list[dict] = []
        while True:
            page = await agent.call(
                session,
                "event_get",
                {
                    "stream": "handoff",
                    "cursor": cursor,
                    "limit": 100,
                    "filters": {"handoff_id": handoff_id},
                },
            )
            data = page.get("data", page)
            events.extend(data.get("events", []))
            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")
        print(json.dumps(events, indent=2))

        print(f"\n== finishing the task for real, then handoff_complete ==")
        completed = await agent.call(
            session, "handoff_complete", {"handoff_id": handoff_id, "result": result}
        )
        print(json.dumps(completed, indent=2))
        print(
            "\nRecovery done: this process never shared memory with the killed "
            "one -- everything above came from Nexus's own durable record."
        )


async def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_start = sub.add_parser("start")
    p_start.add_argument("--handoff-id", required=True)

    p_recover = sub.add_parser("recover")
    p_recover.add_argument("--handoff-id", required=True)
    p_recover.add_argument("--result", required=True)

    args = parser.parse_args()
    if args.cmd == "start":
        await cmd_start(args.handoff_id)
    else:
        await cmd_recover(args.handoff_id, args.result)


if __name__ == "__main__":
    asyncio.run(main())
