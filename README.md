# Meeting Miner

An AI agent that reads your meeting transcripts, extracts problems and opportunities, and generates ranked invention ideas — each with a Starting Point (MVP) and an Ambitious Version.

## How it works

1. Searches Gmail for Gemini meeting notes
2. Reads the linked Google Doc transcripts (read-only — never edits source docs)
3. Runs a 5-step LLM pipeline: signal extraction, parallel persona ideation, cross-meeting synthesis, scoring, and startup lens
4. Appends ranked ideas to a persistent Google Doc
5. Generates an interactive HTML dashboard (hosted on the cluster via a Route, also uploaded to Google Drive)
6. Sends Slack DMs for high-scoring ideas

## Two modes

**Automated** — runs as an OpenShell CronJob on OpenShift (weekdays at 5pm Irish time), using Sonnet via Vertex AI.

**Manual** — run `/meeting-miner` in Claude Code to trigger on demand. Supports filtering: `/meeting-miner scrum` or `/meeting-miner today`.

## Scoring

Each idea is scored 1-10 on five core criteria, with an optional team impact bonus:

| Criterion | What it measures |
|---|---|
| `frustration_intensity` | How painful is this problem based on speaker language? |
| `nobody_owns_this` | Is anyone already working on it? (cross-checked with Jira) |
| `cross_meeting` | Does it link signals from multiple meetings? |
| `repeat_frequency` | Has this come up before? |
| `demo_ability` | Could you show it working in 5 minutes? |

**Bonus:** `team_impact` adds +0.5 ("some") or +1.0 ("high") if the Agent Ops team would actually use it day-to-day. Nudges rankings without dominating them.

## Security

- Source meeting docs are **read-only**. The agent never writes to any doc except the Radar doc.
- The Radar doc ID is hardcoded in the L7 network policy — writes to any other doc are blocked at the network level.
- Runs inside an OpenShell sandbox with filesystem, process, and network isolation.

## Setup

### Prerequisites

- Python 3.12+
- Google Workspace OAuth credentials (client ID, secret, refresh token)
- A Google Doc to use as the Radar output
- (Optional) Slack incoming webhook URL
- (Optional) OpenShift cluster with OpenShell for automated mode

### Environment variables

```bash
export GOOGLE_CLIENT_ID="..."
export GOOGLE_CLIENT_SECRET="..."
export GOOGLE_REFRESH_TOKEN="..."
export RADAR_DOC_ID="<your-radar-doc-id>"

# LLM endpoint (Anthropic SDK — inference.local when running in OpenShell)
export ANTHROPIC_BASE_URL="https://inference.local"
export ANTHROPIC_API_KEY="not-needed-openshell-injects"
export LLM_MODEL="claude-sonnet-4-6"

# Jira (used to cross-check nobody_owns_this scoring)
export JIRA_EMAIL="your-email@redhat.com"
export JIRA_API_TOKEN="..."

# Optional
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
export DASHBOARD_DRIVE_FOLDER_ID="<google-drive-folder-id>"
export STATE_FILE="./state.json"
export RADAR_FILE="./radar.json"
export DASHBOARD_FILE="./dashboard.html"
```

### Run locally

```bash
pip install -r requirements.txt
python3 agent.py
```

### Run tests

```bash
python3 tests/test_state.py
python3 tests/test_gmail_client.py
python3 tests/test_docs_client.py
python3 tests/test_radar_store.py
python3 tests/test_analyzer.py
python3 tests/test_doc_renderer.py
python3 tests/test_web_renderer.py
python3 tests/test_slack_notify.py
python3 tests/test_agent.py
```

### Deploy to OpenShift

```bash
# Build and push images (--platform required on ARM Macs)
podman build --platform linux/amd64 -t quay.io/rh-ee-grasmith/meeting-miner:latest -f Containerfile .
podman build --platform linux/amd64 -t quay.io/rh-ee-grasmith/meeting-miner-launcher:latest -f launcher/Containerfile .
podman push quay.io/rh-ee-grasmith/meeting-miner:latest
podman push quay.io/rh-ee-grasmith/meeting-miner-launcher:latest

# Apply manifests in order
oc apply -f manifests/02-scc-binding.yaml
oc apply -f manifests/03-rbac.yaml
oc apply -f manifests/03-network-policy.yaml
oc apply -f manifests/04-configmap.yaml
oc apply -f manifests/07-dashboard.yaml

# Create secrets (fill in real values)
oc create secret generic meeting-miner-secrets -n openshell \
  --from-literal=RADAR_DOC_ID="$RADAR_DOC_ID" \
  --from-literal=GOOGLE_CLIENT_ID="$GOOGLE_CLIENT_ID" \
  --from-literal=GOOGLE_CLIENT_SECRET="$GOOGLE_CLIENT_SECRET" \
  --from-literal=GOOGLE_REFRESH_TOKEN="$GOOGLE_REFRESH_TOKEN" \
  --from-literal=SLACK_WEBHOOK_URL="$SLACK_WEBHOOK_URL" \
  --from-literal=JIRA_EMAIL="$JIRA_EMAIL" \
  --from-literal=JIRA_API_TOKEN="$JIRA_API_TOKEN"

# Apply CronJob
oc apply -f manifests/05-cronjob.yaml

# Test with a manual run
oc create job --from=cronjob/meeting-miner meeting-miner-test -n openshell
oc logs -f job/meeting-miner-test -n openshell
```

## Project structure

```
agent.py              Main orchestrator — ties all modules together
config.py             Configuration from environment variables
state.py              Idempotent email tracking with atomic writes
lib/
  auth.py             Google OAuth2 token refresh
  google_api.py       GET/POST/PATCH helpers for Google APIs + Drive upload
  gmail_client.py     Gmail search and email parsing
  docs_client.py      Google Docs read/write and annotation extraction
  radar_store.py      Structured data layer (radar.json) with dedup
  analyzer.py         5-step LLM prompt pipeline with parallel personas
  jira_lookup.py      Cross-checks ideas against Jira for nobody_owns_this
  doc_renderer.py     Google Doc text rendering
  web_renderer.py     Static HTML dashboard
  slack_notify.py     Slack webhook notifications
launcher/
  Containerfile       UBI9 minimal + openshell CLI + oc client launcher image
Containerfile         UBI9 Python 3.12 agent container image
launcher.sh           OpenShell sandbox launcher + dashboard ConfigMap update
policy.yaml           L7 network policy template
manifests/            OpenShift/Kubernetes deployment manifests
  07-dashboard.yaml   Dashboard hosting (ConfigMap + Deployment + Service + Route)
skill/                Claude Code skill for manual mode
tests/                Unit tests
```
