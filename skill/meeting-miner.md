---
description: "Run Meeting Miner — analyze meeting transcripts for invention ideas"
---

# Meeting Miner

Analyze recent meeting transcripts from Gmail and generate invention ideas.

## Usage
- `/meeting-miner` — process all new meetings since last run
- `/meeting-miner scrum` — focus on scrum meetings only
- `/meeting-miner today` — only today's meetings

## What This Does

1. Searches Gmail for new Gemini meeting notes (`from:gemini-notes@google.com`)
2. Reads the Google Doc transcripts (READ ONLY — never edits source docs)
3. Extracts problems, pain points, and opportunities
4. Generates invention ideas with Starting Point (MVP) and Ambitious Version
5. Scores ideas on 5 criteria + team impact bonus and ranks them
6. Appends to the persistent Radar Google Doc
7. Generates an HTML dashboard at `~/Desktop/meeting-miner-dashboard.html`

## Security
- Source meeting docs are READ ONLY. The agent NEVER writes to any doc except the Radar doc.
- The Radar doc ID is hardcoded. Every write verifies the target doc ID.

## Steps

1. Read the user's argument (if any) to determine scope filter
2. Run the meeting-miner Python agent:

```bash
cd ~/idea-finder
# Set scope filter based on user argument
FILTER_ARG="${ARGUMENTS:-}"

if [ -n "$FILTER_ARG" ]; then
  # Modify Gmail query for specific meeting filter
  export GMAIL_QUERY_OVERRIDE="from:gemini-notes@google.com subject:\"Notes:\" subject:\"$FILTER_ARG\" newer_than:7d"
fi

# Use local paths for state/radar/dashboard
export STATE_FILE="$HOME/meeting-miner/state.json"
export RADAR_FILE="$HOME/meeting-miner/radar.json"
export DASHBOARD_FILE="$HOME/Desktop/meeting-miner-dashboard.html"

python3 agent.py
```

3. After the agent runs, open the dashboard:
```bash
open ~/Desktop/meeting-miner-dashboard.html
```

4. Report summary: how many meetings processed, how many ideas generated, any high-scoring ones worth checking.
