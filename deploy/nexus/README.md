# One-click Railway deploy (Okto Nexus)

Runs `okto-nexus serve` behind a small Caddy proxy on one public port. Nexus has its own
sign-in for people and its own API keys for agents, so there is no extra gate in front of it:

| Path | Protection |
|---|---|
| `/` (dashboard) | Operator sign-in with `UI_USER` / `UI_PASSWORD`, set on every boot |
| `/mcp` and the agent REST API | Agent API key: `Authorization: Bearer nxs_...` |
| `/healthz` | open, returns `ok` |

## Create the Railway template (once)
1. Railway → Workspace → Templates → **New Template**.
2. Add a service from this GitHub repo. Settings:
   - Variable `RAILWAY_DOCKERFILE_PATH` = `deploy/nexus/Dockerfile`
   - Enable public networking (HTTP). Healthcheck path `/healthz`.
   - Right-click service → **Attach Volume**, mount path `/data`.
3. Variables:
   - `UI_USER` = `demo`
   - `UI_PASSWORD` = `${{secret(24)}}` (Nexus needs at least 12 characters)
4. **Create Template**, copy the URL, then add this button to the README:
   `[![Deploy on Railway](https://railway.com/button.svg)](<template-url>)`

## After a visitor deploys
1. Open the generated domain and sign in with `UI_USER` / `UI_PASSWORD` (shown in the service Variables tab).
2. Create an agent in the dashboard and copy its key (shown once).
3. Point an MCP client at `https://<domain>/mcp` with `Authorization: Bearer <key>`.

The entrypoint turns on `feature_dag`, `feature_hitl` and `feature_verification`, the same flags the
demo's `scripts/00_setup_nexus.sh` enables. Semantic memory is off, so the image installs
`okto-nexus[serve-lite]` and skips the PyTorch stack (about 250 MB instead of 6 GB).

## Why the Caddyfile rewrites two things
Nexus ignores `X-Forwarded-*` headers, so two of its checks assume a direct connection. The proxy
bridges both, narrowly: an `Origin` of exactly `https://<this host>` becomes `http://<this host>` (other
origins are still rejected), and `/mcp` is sent with the loopback `Host` (agent keys still authenticate
every call). Details are in the comments in `Caddyfile`.

## Checked and not checked
Checked locally with Docker: the image builds; sign-in, wrong-password and cross-site rejection; MCP with an
agent key through the proxy; restart, redeploy on the same volume, and recovery after a hard kill (a stale
runtime lease makes the first start wait up to about 40 s). Not checked on Railway itself.

Not included: the Express/Prisma `app/` and its Postgres. The demo scripts need that app; add a second
service (`app/`) and a Railway Postgres plugin to host the full scenario. `app/Dockerfile` expects a prebuilt
`dist/api`, so it needs a multi-stage build first.
