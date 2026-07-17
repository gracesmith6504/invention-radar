import json
import urllib.request
import urllib.parse
from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN

_TOKEN_URL = "https://oauth2.googleapis.com/token"
_cached_token = None


def get_access_token() -> str:
    global _cached_token
    if _cached_token:
        return _cached_token

    if not all([GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN]):
        raise RuntimeError("Google OAuth credentials not configured — set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN env vars")

    data = urllib.parse.urlencode({
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "refresh_token": GOOGLE_REFRESH_TOKEN,
        "grant_type": "refresh_token",
    }).encode()

    req = urllib.request.Request(_TOKEN_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())

    _cached_token = result["access_token"]
    return _cached_token


def clear_token_cache():
    global _cached_token
    _cached_token = None
