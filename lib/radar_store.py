import json
import os
import re
import tempfile


def load_radar(path: str) -> dict:
    """Load radar.json or return empty default if file doesn't exist."""
    if not os.path.exists(path):
        return {"ideas": [], "trends": {}, "people": {}}
    with open(path) as f:
        return json.load(f)


def save_radar(data: dict, path: str) -> None:
    """Atomic write to radar.json using tempfile pattern."""
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


def add_ideas(data: dict, new_ideas: list[dict]) -> dict:
    """Add new ideas, deduplicating by ID (keep existing, skip new)."""
    existing_ids = {idea["id"] for idea in data["ideas"]}
    for idea in new_ideas:
        if idea["id"] not in existing_ids:
            data["ideas"].append(idea)
            existing_ids.add(idea["id"])
    return data


def generate_idea_id(title: str, date: str) -> str:
    """Create stable ID from date + slugified title."""
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug).strip("-")
    slug = re.sub(r"-+", "-", slug)
    return f"{date}-{slug}"


def update_annotations(data: dict, annotations: dict[str, str]) -> dict:
    """Sync status/stars from doc markers (annotation dict keyed by title)."""
    for idea in data["ideas"]:
        if idea["title"] in annotations:
            marker = annotations[idea["title"]]
            if marker == "starred":
                idea["starred"] = True
            else:
                idea["status"] = marker
    return data


def update_trends(data: dict) -> dict:
    """Recalculate trend data from idea tags."""
    tag_counts: dict[str, int] = {}
    for idea in data["ideas"]:
        for tag in idea.get("tags", []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    data["trends"] = {
        tag: {"mentions": count, "direction": "stable"}
        for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1])
    }
    return data


def get_starred(data: dict) -> list[dict]:
    """Return all starred/active ideas (starred=true or status in active_statuses)."""
    active_statuses = {"exploring", "building", "pitched to team"}
    return [
        idea
        for idea in data["ideas"]
        if idea.get("starred") or idea.get("status") in active_statuses
    ]
