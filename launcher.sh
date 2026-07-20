#!/bin/bash
set -euo pipefail

AGENT_IMAGE="${AGENT_IMAGE:-quay.io/rh-ee-grasmith/meeting-miner:latest}"
SANDBOX_NAME="meeting-miner-$(date +%s)"
POLICY_FILE="/tmp/policy.yaml"

export OPENSHELL_GATEWAY_ENDPOINT="${OPENSHELL_GATEWAY_ENDPOINT:-http://openshell.openshell.svc.cluster.local:8080}"

sed "s/__RADAR_DOC_ID__/${RADAR_DOC_ID}/" /app/policy-template.yaml > "$POLICY_FILE"

echo "[launcher] Starting sandbox: $SANDBOX_NAME"
echo "[launcher] Agent image: $AGENT_IMAGE"
echo "[launcher] Gateway: $OPENSHELL_GATEWAY_ENDPOINT"

openshell sandbox create \
  --from="$AGENT_IMAGE" \
  --name="$SANDBOX_NAME" \
  --policy="$POLICY_FILE" \
  --provider="${INFERENCE_PROVIDER:-vertex-prod}" \
  --no-keep \
  --env="RADAR_DOC_ID=${RADAR_DOC_ID}" \
  --env="GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}" \
  --env="GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}" \
  --env="GOOGLE_REFRESH_TOKEN=${GOOGLE_REFRESH_TOKEN}" \
  --env="SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL:-}" \
  --env="JIRA_EMAIL=${JIRA_EMAIL:-}" \
  --env="JIRA_API_TOKEN=${JIRA_API_TOKEN:-}" \
  --env="ANTHROPIC_BASE_URL=${ANTHROPIC_BASE_URL:-https://inference.local}" \
  --env="ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-not-needed}" \
  --env="LLM_MODEL=${LLM_MODEL:-claude-sonnet-4-6}" \
  --env="STATE_FILE=/sandbox/state.json" \
  --env="RADAR_FILE=/sandbox/radar.json" \
  --env="DASHBOARD_FILE=/sandbox/dashboard.html" \
  --env="DASHBOARD_DRIVE_FOLDER_ID=${DASHBOARD_DRIVE_FOLDER_ID:-}" \
  -- /opt/app-root/bin/python3 /app/agent.py

echo "[launcher] Sandbox $SANDBOX_NAME completed and destroyed"
