#!/usr/bin/env python3
"""Stage 0 (part 3): create a `require_approval` policy on `handoff_create`
and bind it to `schema-agent` as a global, latest-mode policy.

Confirmed live against a real Nexus instance that `require_approval` only
accepts `handoff_create` / `message_create` as its action -- NOT
`artifact_put` -- which is why the gate in this demo sits on Schema Agent
proposing the migration handoff, not on any later artifact write.

Auth: if OPERATOR_API_KEY is set in your environment, it's sent as a Bearer
token -- see 01_register_agents.py's docstring for why this isn't assumed
unnecessary just because the instance these scripts were built against
didn't require it.

Usage:
    python3 scripts/02_bind_policy.py --url http://127.0.0.1:8202
"""
from __future__ import annotations

import argparse
import os

import httpx


def _auth_headers() -> dict:
    key = os.environ.get("OPERATOR_API_KEY")
    return {"Authorization": f"Bearer {key}"} if key else {}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8202")
    parser.add_argument("--agent-id", default="schema-agent")
    args = parser.parse_args()

    with httpx.Client(base_url=args.url, timeout=10, headers=_auth_headers()) as client:
        print("== Creating policy header ==")
        resp = client.post(
            "/api/v1/policies",
            json={"name": "require-approval-on-migration-handoffs"},
        )
        resp.raise_for_status()
        policy = resp.json()["data"] if "data" in resp.json() else resp.json()
        policy_id = policy["policy_id"]
        print(f"   policy_id = {policy_id}")

        print("== Publishing version: require_approval on handoff_create ==")
        resp = client.post(
            f"/api/v1/policies/{policy_id}/versions",
            json={
                "governance": [
                    {"action": "handoff_create", "limit_kind": "require_approval"}
                ]
            },
        )
        resp.raise_for_status()
        print("   published.")

        print(f"== Binding to {args.agent_id} as a global, latest-mode policy ==")
        resp = client.put(
            f"/api/v1/agents/{args.agent_id}/policies",
            json={"globals": [{"policy_id": policy_id, "mode": "latest"}]},
        )
        resp.raise_for_status()
        print("   bound.")

        print("\n== Verifying ==")
        try:
            resp = client.get(f"/api/v1/agents/{args.agent_id}/policies")
            resp.raise_for_status()
            print(resp.json())
        except httpx.HTTPStatusError:
            print(
                "   (verification GET path may differ by Nexus version -- "
                f"check the dashboard's agent detail page for {args.agent_id}, "
                "or /api/v1/docs on your instance, if this 404s)"
            )


if __name__ == "__main__":
    main()
