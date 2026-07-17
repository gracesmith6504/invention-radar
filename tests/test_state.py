import json
import os
import sys
import tempfile
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from state import load_state, save_state, is_processed, mark_processed, prune_old_entries


def test_load_state_missing_file():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "state.json")
        result = load_state(path)
        assert result == {"last_run": None, "processed_emails": {}}


def test_load_state_existing_file():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "state.json")
        data = {"last_run": "2026-07-16T17:00:00Z", "processed_emails": {"abc": {"date": "2026-07-16", "meeting": "Test"}}}
        with open(path, "w") as f:
            json.dump(data, f)
        result = load_state(path)
        assert result["last_run"] == "2026-07-16T17:00:00Z"
        assert "abc" in result["processed_emails"]


def test_save_state_atomic():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "state.json")
        data = {"last_run": "2026-07-17T17:00:00Z", "processed_emails": {}}
        save_state(data, path)
        with open(path) as f:
            loaded = json.load(f)
        # Fix: verify that last_run is a valid ISO timestamp, not None
        assert loaded["last_run"] is not None
        assert "T" in loaded["last_run"]  # valid ISO format


def test_is_processed():
    data = {"last_run": None, "processed_emails": {"abc123": {"date": "2026-07-16", "meeting": "Test"}}}
    assert is_processed(data, "abc123") is True
    assert is_processed(data, "xyz789") is False


def test_mark_processed():
    data = {"last_run": None, "processed_emails": {}}
    updated = mark_processed(data, "newid", "Sprint Review")
    assert "newid" in updated["processed_emails"]
    assert updated["processed_emails"]["newid"]["meeting"] == "Sprint Review"
    assert "date" in updated["processed_emails"]["newid"]


def test_prune_old_entries():
    old_date = (datetime.now(timezone.utc) - timedelta(days=45)).strftime("%Y-%m-%d")
    recent_date = (datetime.now(timezone.utc) - timedelta(days=5)).strftime("%Y-%m-%d")
    data = {
        "last_run": None,
        "processed_emails": {
            "old_one": {"date": old_date, "meeting": "Old Meeting"},
            "new_one": {"date": recent_date, "meeting": "Recent Meeting"},
        },
    }
    pruned = prune_old_entries(data, days=30)
    assert "old_one" not in pruned["processed_emails"]
    assert "new_one" in pruned["processed_emails"]


if __name__ == "__main__":
    test_load_state_missing_file()
    print("✓ load_state missing file")
    test_load_state_existing_file()
    print("✓ load_state existing file")
    test_save_state_atomic()
    print("✓ save_state atomic")
    test_is_processed()
    print("✓ is_processed")
    test_mark_processed()
    print("✓ mark_processed")
    test_prune_old_entries()
    print("✓ prune_old_entries")
    print("\nAll state tests passed.")
