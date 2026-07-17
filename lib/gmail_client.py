import base64
import re
import urllib.parse
from lib.google_api import google_get

_GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"


def fetch_gemini_emails(token: str, query: str | None = None) -> list[dict]:
    """Fetch Gemini meeting notes emails from Gmail.

    Args:
        token: OAuth access token
        query: Gmail search query (uses config.GMAIL_QUERY if None)

    Returns:
        List of dicts with keys: id, subject, date, doc_url, meeting_name
    """
    from config import GMAIL_QUERY

    search_query = query if query is not None else GMAIL_QUERY
    encoded_q = urllib.parse.quote(search_query)
    search_url = f"{_GMAIL_API}/messages?q={encoded_q}&maxResults=50"
    search_result = google_get(search_url, token)

    messages = search_result.get("messages", [])
    if not messages:
        return []

    results = []
    for msg_stub in messages:
        msg_url = f"{_GMAIL_API}/messages/{msg_stub['id']}?format=full"
        msg = google_get(msg_url, token)
        parsed = _parse_email(msg)
        if parsed:
            results.append(parsed)

    return results


def _parse_email(msg: dict) -> dict | None:
    """Parse a single Gmail message into our output format.

    Returns None if the email doesn't have a doc URL.
    """
    headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
    subject = headers.get("Subject", "")
    date = headers.get("Date", "")

    body_html = _extract_body(msg["payload"])
    if not body_html:
        return None

    doc_url = extract_doc_url(body_html)
    if not doc_url:
        return None

    return {
        "id": msg["id"],
        "subject": subject,
        "date": date,
        "doc_url": doc_url,
        "meeting_name": extract_meeting_name(subject),
    }


def _extract_body(payload: dict) -> str | None:
    """Recursively extract HTML body from email payload.

    Gmail messages can be nested in parts, so we search recursively.
    """
    if payload.get("mimeType") == "text/html" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")

    for part in payload.get("parts", []):
        result = _extract_body(part)
        if result:
            return result
    return None


def extract_doc_url(html: str) -> str | None:
    """Extract a Google Docs URL from HTML email body.

    Returns the first docs.google.com URL found, or None.
    """
    matches = re.findall(r'href="(https://docs\.google\.com/document/d/[^"]+)"', html)
    return matches[0] if matches else None


def extract_meeting_name(subject: str) -> str:
    """Extract meeting name from email subject line.

    Expects format like:
    - Notes: "Meeting Name" Date
    - Notes: Meeting Name Date

    Returns the quoted part if present, otherwise the part after "Notes: ".
    """
    prefix = "Notes: "
    if not subject.startswith(prefix):
        return subject
    rest = subject[len(prefix):]
    match = re.match(r'"([^"]+)"', rest)
    if match:
        return match.group(1)
    return rest
