#!/usr/bin/env python3
"""Stage 0 (part 2): register fresh `schema-agent` / `api-agent` identities
on the running Nexus instance and print the credentials to fill into `.env`.

This is what makes the demo re-runnable by anyone who forks the repo -- no
identity or API key is baked into source anywhere. Run this once per fresh
Nexus instance (or per re-run against a wiped workspace).

Usage:
    python3 scripts/01_register_agents.py --url http://127.0.0.1:8202
"""
from __future__ import annotations

import argparse
import json

import httpx

AGENTS = [
    {"agent_id": "schema-agent", "role": "schema", "display_name": "Schema Agent"},
    {"agent_id": "api-agent", "role": "api", "display_name": "API Agent"},
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8202")
    args = parser.parse_args()

    print(f"# Paste these into your .env\n")
    with httpx.Client(base_url=args.url, timeout=10) as client:
        for agent in AGENTS:
            resp = client.post("/api/v1/agents", json=agent)
            resp.raise_for_status()
            data = resp.json()["data"] if "data" in resp.json() else resp.json()
            api_key = data.get("api_key") or data.get("key")
            prefix = "SCHEMA" if agent["agent_id"] == "schema-agent" else "API"
            print(f"{prefix}_AGENT_ID={agent['agent_id']}")
            print(f"{prefix}_API_KEY={api_key}")
            print()

    print(
        "# If an agent_id already exists on this instance, the call above will\n"
        "# fail -- either wipe the workspace first or pick different agent_ids\n"
        "# and update the rest of the scripts/prompts to match."
    )


if __name__ == "__main__":
    main()
