#!/usr/bin/env bash
# Stage 0 (part 1): install and start a local Nexus instance for this demo,
# then flip on the three feature flags the scenario depends on.
#
# Does NOT register agents or bind policy -- that's 01_register_agents.py and
# 02_bind_policy.py, kept separate so you can re-run just the flags without
# re-installing, or vice versa.
set -euo pipefail

PORT="${NEXUS_PORT:-8202}"
PROJECT_ROOT="${NEXUS_PROJECT_ROOT:?Set NEXUS_PROJECT_ROOT to the absolute path of this repo clone}"

echo "== Installing okto-nexus (serve extra) =="
pip install "okto-nexus[serve]"

echo "== Starting okto-nexus serve on port ${PORT} (backgrounded) =="
# --home scopes this instance's data to the repo clone itself
# (.nexus-data/, gitignored) instead of the default ~/.okto_nexus, which is
# SHARED across every Nexus instance on this machine. Without this, running
# this script on a machine that already has another Nexus demo/workspace
# set up mixes this demo's agents and handoffs into that shared data --
# confirmed the hard way while validating these scripts against a machine
# that already had an unrelated Nexus instance running.
nohup okto-nexus serve --port "${PORT}" --project-root "${PROJECT_ROOT}" \
  --home "${PROJECT_ROOT}/.nexus-data" \
  > "${PROJECT_ROOT}/.nexus-server.log" 2>&1 &
NEXUS_PID=$!
echo "   started pid ${NEXUS_PID}, data in .nexus-data/, logging to .nexus-server.log"

echo "== Waiting for it to come up =="
for i in $(seq 1 30); do
  if curl -sS -o /dev/null "http://127.0.0.1:${PORT}/api/v1/settings"; then
    echo "   up."
    break
  fi
  sleep 1
done

echo "== Enabling feature_dag / feature_hitl / feature_verification =="
curl -sS -X PATCH "http://127.0.0.1:${PORT}/api/v1/settings" \
  -H "Content-Type: application/json" \
  -d '{"feature_dag": true, "feature_hitl": true, "feature_verification": true}' \
  | python3 -m json.tool

echo
echo "Nexus is up on http://127.0.0.1:${PORT} (pid ${NEXUS_PID})."
echo "Next: scripts/01_register_agents.py"
