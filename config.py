import os

RADAR_DOC_ID = os.environ.get("RADAR_DOC_ID", "")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")

GMAIL_QUERY = os.environ.get("GMAIL_QUERY_OVERRIDE", os.environ.get("GMAIL_QUERY", 'from:gemini-notes@google.com subject:"Notes:" newer_than:7d'))

SCORE_THRESHOLD = 7.0

LLM_MODEL = os.environ.get("LLM_MODEL", "claude-sonnet-4-6")
LLM_BASE_URL = os.environ.get("ANTHROPIC_BASE_URL", "https://inference.local")
LLM_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "not-needed-openshell-injects")

JIRA_URL = os.environ.get("JIRA_URL", "https://redhat.atlassian.net")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL", "")
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN", "")

STATE_FILE = os.environ.get("STATE_FILE", "/sandbox/state.json")
RADAR_FILE = os.environ.get("RADAR_FILE", "/sandbox/radar.json")
DASHBOARD_FILE = os.environ.get("DASHBOARD_FILE", "/sandbox/dashboard.html")
DASHBOARD_DRIVE_FOLDER_ID = os.environ.get("DASHBOARD_DRIVE_FOLDER_ID", "")

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REFRESH_TOKEN = os.environ.get("GOOGLE_REFRESH_TOKEN", "")

MAX_PARALLEL_PERSONAS = 4

PERSONAS = [
    {
        "name": "logistics coordinator",
        "prompt": "You are a logistics coordinator who automates warehouse workflows. You think in terms of throughput, bottlenecks, and eliminating manual handoffs.",
    },
    {
        "name": "ER nurse",
        "prompt": "You are an emergency room nurse who's seen dozens of hospital IT systems fail. You focus on reliability under pressure and what breaks when people are stressed.",
    },
    {
        "name": "game designer",
        "prompt": "You are a game designer who specializes in feedback loops and motivation. You think about what makes people want to keep doing something vs abandon it.",
    },
    {
        "name": "farmer-coder",
        "prompt": "You are a farmer who uses IoT sensors and writes Python for crop monitoring. You think practically about what works in the field with limited connectivity and budget.",
    },
]

SCORING_CRITERIA = [
    "frustration_intensity",
    "nobody_owns_this",
    "cross_meeting",
    "repeat_frequency",
    "demo_ability",
]
