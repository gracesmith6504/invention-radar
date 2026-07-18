---
description: "Run the Invention Radar — analyze meeting transcripts for invention ideas"
---

# Invention Radar

Analyze recent meeting transcripts from Gmail and generate invention ideas.

## Usage
- `/invention-radar` — process all new meetings since last run
- `/invention-radar ignas` — focus on Ignas meetings only
- `/invention-radar today` — only today's meetings

## What This Does

1. Searches Gmail for new Gemini meeting notes (`from:gemini-notes@google.com`)
2. Reads the Google Doc transcripts (READ ONLY — never edits source docs)
3. Extracts problems, pain points, and opportunities
4. Generates invention ideas with Starting Point (MVP) and Ambitious Version
5. Scores ideas on 6 criteria and ranks them
6. Appends to the persistent Invention Radar Google Doc
7. Generates an HTML dashboard at `~/Desktop/invention-radar-dashboard.html`

## Security
- Source meeting docs are READ ONLY. The agent NEVER writes to any doc except the Radar doc.
- The Radar doc ID is hardcoded. Every write verifies the target doc ID.

## Steps

1. Read the user's argument (if any) to determine scope filter
2. Run the invention-radar Python agent:

```bash
cd ~/invention-radar
# Set scope filter based on user argument
FILTER_ARG="${ARGUMENTS:-}"

if [ -n "$FILTER_ARG" ]; then
  # Modify Gmail query for specific meeting filter
  export GMAIL_QUERY_OVERRIDE="from:gemini-notes@google.com subject:\"Notes:\" subject:\"$FILTER_ARG\" newer_than:7d"
fi

# Use local paths for state/radar/dashboard
export STATE_FILE="$HOME/invention-radar/state.json"
export RADAR_FILE="$HOME/invention-radar/radar.json"
export DASHBOARD_FILE="$HOME/Desktop/invention-radar-dashboard.html"

python3 agent.py
```

3. After the agent runs, open the dashboard:
```bash
open ~/Desktop/invention-radar-dashboard.html
```

4. Report summary: how many meetings processed, how many ideas generated, any high-scoring ones worth checking.
