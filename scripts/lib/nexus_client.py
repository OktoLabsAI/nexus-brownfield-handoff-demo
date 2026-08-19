"""Shared MCP client helper for the nexus-brownfield-handoff-demo scripts.

All coordination-layer scripts in this repo (propose, approve, claim, complete,
recover, closeout) go through this module instead of hand-rolling their own
`sse_client`/`streamablehttp_client` plumbing. Centralizing it means:

- One place to fix transport issues (Nexus's MCP endpoint speaks streamable
  HTTP, not SSE -- an earlier draft of these scripts used `sse_client` and
  that is wrong for current `okto-nexus` versions).
- No hardcoded API keys or handoff IDs anywhere in this repo. Every script
  reads its identity from environment variables (see `.env.example`), so
  forking this repo and running it never requires editing secrets into
  source files.
- A single `call_tool` wrapper that raises on error content instead of
  silently returning it, so a script that expects a real result doesn't
  proceed on a swallowed failure.

Usage pattern in every script:

    from lib.nexus_client import NexusAgent

    async def main():
        agent = NexusAgent.from_env("SCHEMA_AGENT")   # reads SCHEMA_AGENT_API_KEY
        async with agent.session() as session:
            result = await agent.call(session, "handoff_create", {...})
"""
from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


@dataclass
class NexusAgent:
    agent_id: str
    api_key: str
    base_url: str
    project_root: str

    @classmethod
    def from_env(cls, prefix: str) -> "NexusAgent":
        """Build a NexusAgent from `<PREFIX>_AGENT_ID` / `<PREFIX>_API_KEY`,
        plus the shared `NEXUS_URL` / `NEXUS_PROJECT_ROOT`.

        Example: NexusAgent.from_env("SCHEMA") reads SCHEMA_AGENT_ID and
        SCHEMA_API_KEY.
        """
        agent_id = _require_env(f"{prefix}_AGENT_ID")
        api_key = _require_env(f"{prefix}_API_KEY")
        base_url = os.environ.get("NEXUS_URL", "http://127.0.0.1:8202")
        project_root = _require_env("NEXUS_PROJECT_ROOT")
        return cls(agent_id=agent_id, api_key=api_key, base_url=base_url, project_root=project_root)

    @property
    def mcp_url(self) -> str:
        return f"{self.base_url}/mcp?api_key={self.api_key}"

    @asynccontextmanager
    async def session(self):
        async with streamablehttp_client(self.mcp_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session

    async def call(self, session: ClientSession, tool: str, arguments: dict) -> dict:
        """Call an MCP tool with project_root/agent_id auto-filled, parse the
        JSON result, and raise if the call itself errored."""
        payload = {"project_root": self.project_root, "agent_id": self.agent_id, **arguments}
        result = await session.call_tool(tool, payload)
        text = result.content[0].text if result.content else "{}"
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = {"raw": text}
        if getattr(result, "isError", False):
            raise RuntimeError(f"{tool} failed: {data}")
        return data


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(
            f"Missing required environment variable: {name}\n"
            f"Copy .env.example to .env, fill it in, and `export $(grep -v '^#' .env | xargs)` "
            f"(or use a tool like direnv/dotenv) before running these scripts."
        )
    return value
