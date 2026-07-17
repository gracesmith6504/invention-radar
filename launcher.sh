#!/bin/bash
set -euo pipefail

AGENT_IMAGE="${AGENT_IMAGE:-quay.io/grasmith/invention-radar:latest}"
SANDBOX_NAME="invention-radar-$(date +%s)"
POLICY_FILE="/tmp/policy.yaml"

# Inject Radar doc ID into policy template
sed "s/__RADAR_DOC_ID__/${RADAR_DOC_ID}/" /app/policy-template.yaml > "$POLICY_FILE"

echo "[launcher] Starting sandbox: $SANDBOX_NAME"
echo "[launcher] Agent image: $AGENT_IMAGE"

openshell sandbox create \
  --from="$AGENT_IMAGE" \
  --name="$SANDBOX_NAME" \
  --policy="$POLICY_FILE" \
  --no-keep \
  --env="RADAR_DOC_ID=${RADAR_DOC_ID}" \
  --env="GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}" \
  --env="GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}" \
  --env="GOOGLE_REFRESH_TOKEN=${GOOGLE_REFRESH_TOKEN}" \
  --env="SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL}" \
  --env="OPENAI_BASE_URL=${OPENAI_BASE_URL:-https://inference.local/v1}" \
  --env="OPENAI_API_KEY=${OPENAI_API_KEY:-not-needed}" \
  --env="LLM_MODEL=${LLM_MODEL:-google/gemini-2.5-flash}" \
  --env="STATE_FILE=/sandbox/state.json" \
  --env="RADAR_FILE=/sandbox/radar.json" \
  --env="DASHBOARD_FILE=/sandbox/dashboard.html" \
  -- python3 agent.py

echo "[launcher] Sandbox $SANDBOX_NAME completed and destroyed"
