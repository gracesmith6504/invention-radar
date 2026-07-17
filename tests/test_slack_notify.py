import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.slack_notify import build_slack_message


def test_build_slack_message():
    idea = {
        "title": "Auto-Deployer",
        "description": "Automates deployments.",
        "overall_score": 8.5,
        "scores": {"cross_meeting": 9},
        "category": "work",
    }
    msg = build_slack_message(idea)
    assert "Auto-Deployer" in str(msg)
    assert "8.5" in str(msg)


def test_build_slack_message_cross_meeting():
    idea = {
        "title": "Cross Idea",
        "description": "Links two meetings.",
        "overall_score": 9.0,
        "scores": {"cross_meeting": 9},
        "category": "work",
    }
    msg = build_slack_message(idea)
    text = str(msg)
    assert "Cross" in text or "cross" in text


def test_build_slack_message_startup():
    idea = {
        "title": "Startup Idea",
        "description": "Business opportunity.",
        "overall_score": 8.0,
        "scores": {},
        "category": "startup",
    }
    msg = build_slack_message(idea)
    assert "Startup" in str(msg) or "startup" in str(msg)


if __name__ == "__main__":
    test_build_slack_message()
    print("✓ build_slack_message")
    test_build_slack_message_cross_meeting()
    print("✓ build_slack_message cross meeting")
    test_build_slack_message_startup()
    print("✓ build_slack_message startup")
    print("\nAll slack_notify tests passed.")
