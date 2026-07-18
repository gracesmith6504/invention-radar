import json
import os
import tempfile
from datetime import datetime, timezone, timedelta


def load_state(path: str) -> dict:
    if not os.path.exists(path):
        return {"last_run": None, "processed_emails": {}}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        print(f"Warning: corrupt {path}, starting fresh")
        return {"last_run": None, "processed_emails": {}}


def save_state(data: dict, path: str) -> None:
    data["last_run"] = datetime.now(timezone.utc).isoformat()
    dir_name = os.path.dirname(path) or "."
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def is_processed(state_data: dict, email_id: str) -> bool:
    return email_id in state_data.get("processed_emails", {})


def mark_processed(state_data: dict, email_id: str, meeting: str) -> dict:
    state_data.setdefault("processed_emails", {})[email_id] = {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "meeting": meeting,
    }
    return state_data


def prune_old_entries(state_data: dict, days: int = 30) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    emails = state_data.get("processed_emails", {})
    state_data["processed_emails"] = {
        eid: info
        for eid, info in emails.items()
        if datetime.strptime(info["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc) > cutoff
    }
    return state_data
