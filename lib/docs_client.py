import re
from lib.google_api import google_get, google_post
import config


def extract_doc_id(doc_url: str) -> str:
    match = re.search(r"/document/d/([^/]+)", doc_url)
    if not match:
        raise ValueError(f"Cannot extract doc ID from: {doc_url}")
    return match.group(1)


def read_doc_text(doc_url: str, token: str) -> str:
    doc_id = extract_doc_id(doc_url)
    url = f"https://docs.googleapis.com/v1/documents/{doc_id}"
    doc = google_get(url, token)
    return extract_text_from_doc_json(doc)


def extract_text_from_doc_json(doc: dict) -> str:
    parts = []
    for element in doc.get("body", {}).get("content", []):
        paragraph = element.get("paragraph", {})
        for elem in paragraph.get("elements", []):
            text_run = elem.get("textRun", {})
            content = text_run.get("content", "")
            if content:
                parts.append(content)
    return "".join(parts)


def read_radar_doc(token: str) -> str:
    if not config.RADAR_DOC_ID:
        raise RuntimeError("RADAR_DOC_ID not configured")
    url = f"https://docs.googleapis.com/v1/documents/{config.RADAR_DOC_ID}"
    doc = google_get(url, token)
    return extract_text_from_doc_json(doc)


def append_to_radar(token: str, requests: list[dict]) -> dict:
    if not config.RADAR_DOC_ID:
        raise RuntimeError("RADAR_DOC_ID not configured")
    url = f"https://docs.googleapis.com/v1/documents/{config.RADAR_DOC_ID}:batchUpdate"
    return google_post(url, token, {"requests": requests})


def read_radar_annotations(radar_text: str) -> dict[str, str]:
    annotations = {}
    for line in radar_text.split("\n"):
        line = line.strip()
        if not line.startswith("## "):
            continue
        heading = line[3:].strip()

        if "⭐" in heading:
            name = heading.replace("⭐", "").strip()
            annotations[name] = "starred"
            continue

        # Fixed regex: \[([^\]]+)\] matches any text inside brackets, including spaces
        status_match = re.search(r"\[([^\]]+)\]", heading)
        if status_match:
            status = status_match.group(1)
            # Fixed cleanup regex similarly
            name = re.sub(r"\s*\[[^\]]+\]", "", heading).strip()
            if status in ("exploring", "building", "parked", "pitched to team"):
                annotations[name] = status
    return annotations
