#!/usr/bin/env python3
"""Stage 0 (part 2): register fresh `schema-agent` / `api-agent` identities
on the running Nexus instance and print the credentials to fill into `.env`.

This is what makes the demo re-runnable by anyone who forks the repo -- no
identity or API key is baked into source anywhere. Run this once per fresh
Nexus instance (or per re-run against a wiped workspace).

Auth: if OPERATOR_API_KEY is set in your environment, it's sent as a Bearer
token. Against the instance these scripts were built against, none of these
admin REST routes required it -- but that's a property of that one local
instance, not a guarantee for every Nexus install, so the header is sent
whenever the key is available rather than assumed unnecessary.

Usage:
    python3 scripts/01_register_agents.py --url http://127.0.0.1:8202
"""
from __future__ import annotations

import argparse
import json
import os

import httpx

AGENTS = [
    {"agent_id": "schema-agent", "role": "schema", "display_name": "Schema Agent"},
    {"agent_id": "api-agent", "role": "api", "display_name": "API Agent"},
]


def _auth_headers() -> dict:
    key = os.environ.get("OPERATOR_API_KEY")
    return {"Authorization": f"Bearer {key}"} if key else {}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8202")
    args = parser.parse_args()

    print(f"# Paste these into your .env\n")
    with httpx.Client(base_url=args.url, timeout=10, headers=_auth_headers()) as client:
        for agent in AGENTS:
            resp = client.post("/api/v1/agents", json=agent)
            if resp.status_code in (401, 403):
                raise SystemExit(
                    f"{resp.status_code} creating {agent['agent_id']} -- this instance "
                    "requires auth for admin REST calls. Set OPERATOR_API_KEY in your "
                    "environment (get it from your Nexus install's own setup output, "
                    "not from this repo) and re-run."
                )
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
