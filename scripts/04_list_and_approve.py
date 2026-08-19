#!/usr/bin/env python3
"""Stage 2: list pending approvals and (optionally) decide one.

Approval decisions are an admin/dashboard action by design -- see
`docs/decisions/` and the guardrails docstring quoted in the README
("agents must not receive schemas that can mutate or inspect those
controls"). This script exercises the same REST surface the dashboard's
approve/reject buttons use, so the whole scenario is scriptable end to end
without a human clicking through a UI, but it deliberately requires an
explicit `--decision` flag -- nothing auto-approves.

Usage:
    # list what's pending
    python3 scripts/04_list_and_approve.py --url http://127.0.0.1:8202 --workspace <workspace_id>

    # approve one
    python3 scripts/04_list_and_approve.py --url http://127.0.0.1:8202 \\
        --workspace <workspace_id> --approval-id apr_... --decision approve \\
        --note "SQL looks right, FK is nullable so it won't break existing rows"

Confirmed live: `GET /api/v1/approvals?workspace=<id>` lists pending items;
`POST /api/v1/approvals/{id}/decision` with `{"decision": "approve"|"reject"}`
decides one. Get `<workspace_id>` from `GET /api/v1/workspaces` or the
dashboard URL.
"""
from __future__ import annotations

import argparse
import json

import httpx


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8202")
    parser.add_argument("--workspace", required=True, help="workspace_id from GET /api/v1/workspaces")
    parser.add_argument("--approval-id", default=None)
    parser.add_argument("--decision", choices=["approve", "reject"], default=None)
    parser.add_argument("--note", default=None)
    args = parser.parse_args()

    with httpx.Client(base_url=args.url, timeout=10) as client:
        if args.approval_id and args.decision:
            payload = {"decision": args.decision}
            if args.note:
                payload["note"] = args.note
            resp = client.post(f"/api/v1/approvals/{args.approval_id}/decision", json=payload)
            resp.raise_for_status()
            print(json.dumps(resp.json(), indent=2))
            return

        resp = client.get("/api/v1/approvals", params={"workspace": args.workspace})
        resp.raise_for_status()
        data = resp.json()
        print(json.dumps(data, indent=2))
        print(
            "\nRe-run with --approval-id <id> --decision approve|reject "
            "(and optionally --note) to act on one of the above."
        )


if __name__ == "__main__":
    main()
