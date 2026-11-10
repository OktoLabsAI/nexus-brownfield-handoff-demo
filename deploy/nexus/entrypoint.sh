#!/bin/sh
set -eu
: "${PORT:=8080}"
: "${UI_USER:=demo}"
: "${UI_PASSWORD:?Set UI_PASSWORD (12 or more characters)}"
export PORT UI_USER
if [ "${#UI_PASSWORD}" -lt 12 ]; then
  echo "UI_PASSWORD must be at least 12 characters" >&2
  exit 1
fi
mkdir -p "$NEXUS_HOME" /workspace

NEXUS_PID=
CADDY_PID=
# Nexus holds a runtime lease and only releases it on a clean stop, so forward the stop signal
# to it and wait for it instead of exec'ing into Caddy.
shutdown() {
  kill -TERM $CADDY_PID $NEXUS_PID 2>/dev/null || true
  wait $NEXUS_PID 2>/dev/null || true
  exit 0
}
trap shutdown TERM INT

start_nexus() {
  # A restart or redeploy reuses the volume, so the previous run's lock is still there and its PID
  # can match a live process in the new container. This script is the only thing that starts Nexus.
  rm -f "$NEXUS_HOME/nexus.serve.lock"
  # Listen on loopback only; Caddy is the public entrypoint.
  okto-nexus serve --host 127.0.0.1 --port 8202 --project-root /workspace --home "$NEXUS_HOME" &
  NEXUS_PID=$!
  for i in $(seq 1 60); do
    curl -fsS http://127.0.0.1:8202/healthz >/dev/null 2>&1 && return 0
    kill -0 $NEXUS_PID 2>/dev/null || return 1
    sleep 2
  done
  return 1
}

# After a crash or hard kill the previous instance's runtime lease lasts about 40 s and Nexus
# refuses to start until it expires, so retry for about a minute before giving up.
attempt=1
until start_nexus; do
  if [ "$attempt" -ge 4 ]; then echo "Nexus did not start" >&2; exit 1; fi
  echo "Nexus exited during startup; retrying in 15 s (attempt $attempt of 4)" >&2
  attempt=$((attempt + 1))
  kill $NEXUS_PID 2>/dev/null || true
  sleep 15 &
  wait $!
done

# Calls from 127.0.0.1 without forwarded headers count as the local operator.
# Same flags the demo's 00_setup_nexus.sh enables.
curl -fsS -X PATCH http://127.0.0.1:8202/api/v1/settings \
  -H 'Content-Type: application/json' -H 'X-Nexus-UI: 1' \
  -d '{"feature_dag": true, "feature_hitl": true, "feature_verification": true}' >/dev/null
# Dashboard login for remote browsers. Runs on every boot, so the password follows the env var.
python -c 'import json,os;print(json.dumps({"username": os.environ["UI_USER"], "password": os.environ["UI_PASSWORD"]}))' \
  | curl -fsS -X POST http://127.0.0.1:8202/api/v1/operator-auth/account \
    -H 'Content-Type: application/json' -H 'X-Nexus-UI: 1' -d @- >/dev/null

caddy run --config /app/Caddyfile --adapter caddyfile &
CADDY_PID=$!
wait $NEXUS_PID
echo "Nexus exited" >&2
kill $CADDY_PID 2>/dev/null || true
exit 1
