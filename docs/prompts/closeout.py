#!/usr/bin/env python3
"""Close-out script for nexus-brownfield-handoff-demo (Stage 8).

There is no built-in Nexus tool for claim latency / rejection rate /
time-to-approval -- confirmed against the real MCP tool list and the REST
surface (no `get_workspace_metrics` anywhere). This script derives those
numbers itself from the real event log via `event_get`, which is the
documented, correct way to get them.

Usage:
    python3 closeout.py --url http://127.0.0.1:8202 --api-key nxs_...

Requires the `mcp` package (mcp<2 -- see the README's install note).
"""
from __future__ import annotations

import argparse
import asyncio
import json
from collections import defaultdict
from datetime import datetime

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


def _parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


async def fetch_all_events(url: str, agent_id: str, project_root: str) -> list[dict]:
    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            events: list[dict] = []
            cursor = None
            while True:
                result = await session.call_tool(
                    "event_get",
                    {
                        "agent_id": agent_id,
                        "project_root": project_root,
                        "stream": "workspace",
                        "cursor": cursor,
                        "limit": 100,
                    },
                )
                data = json.loads(result.content[0].text)["data"]
                events.extend(data["events"])
                if not data.get("has_more"):
                    break
                cursor = data["next_cursor"]

            # handoff-stream events (created/claimed/completed/rejected/unblocked)
            # live on a separate stream from workspace-level ones (session/approval).
            cursor = None
            while True:
                result = await session.call_tool(
                    "event_get",
                    {
                        "agent_id": agent_id,
                        "project_root": project_root,
                        "stream": "handoff",
                        "cursor": cursor,
                        "limit": 100,
                    },
                )
                data = json.loads(result.content[0].text)["data"]
                events.extend(data["events"])
                if not data.get("has_more"):
                    break
                cursor = data["next_cursor"]

            return events


def summarize(events: list[dict]) -> dict:
    by_type = defaultdict(list)
    for e in events:
        by_type[e["type"]].append(e)

    created = {e.get("payload", {}).get("handoff_id") or e.get("handoff_id"): e for e in by_type.get("handoff.created", [])}
    claimed = by_type.get("handoff.claimed", [])
    rejected = by_type.get("handoff.rejected", [])
    completed = by_type.get("handoff.completed", [])
    approval_requested = {e["approval_id"]: e for e in by_type.get("approval.requested", [])}
    approval_granted = by_type.get("approval.granted", [])

    # Claim latency: time from handoff.created to its first handoff.claimed.
    claim_latencies = []
    for c in claimed:
        hid = c.get("handoff_id") or c.get("payload", {}).get("handoff_id")
        src = created.get(hid)
        if src:
            dt = (_parse_iso(c["created_at"]) - _parse_iso(src["created_at"])).total_seconds()
            claim_latencies.append(dt)

    # Time-to-approval: approval.requested -> approval.granted, matched by approval_id.
    approval_times = []
    for g in approval_granted:
        aid = g["approval_id"]
        req = approval_requested.get(aid)
        if req:
            dt = (_parse_iso(g["created_at"]) - _parse_iso(req["created_at"])).total_seconds()
            approval_times.append(dt)

    return {
        "handoffs_created": len(by_type.get("handoff.created", [])),
        "handoffs_claimed": len(claimed),
        "handoffs_rejected": len(rejected),
        "handoffs_completed": len(completed),
        "claim_latency_seconds": claim_latencies,
        "avg_claim_latency_seconds": sum(claim_latencies) / len(claim_latencies) if claim_latencies else None,
        "time_to_approval_seconds": approval_times,
        "avg_time_to_approval_seconds": sum(approval_times) / len(approval_times) if approval_times else None,
        "rejection_count": len(rejected),
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8202")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--agent-id", default="api-agent")
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()

    mcp_url = f"{args.url}/mcp?api_key={args.api_key}"
    events = await fetch_all_events(mcp_url, args.agent_id, args.project_root)
    summary = summarize(events)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
