import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.doc_renderer import render_idea_text, render_weekly_header, render_favourites_text, render_signals_text


def test_render_idea_text():
    idea = {
        "title": "Auto-Deployer",
        "description": "Automates deployments to staging.",
        "tags": ["agent-ops", "automation"],
        "starting_point": "Script that watches a git branch.",
        "ambitious_version": "Full GitOps pipeline with policy gates.",
        "scores": {"frustration_intensity": 8, "grace_fit": 7},
        "overall_score": 7.5,
        "evidence": [
            {"meeting": "Scrum", "date": "2026-07-17", "speaker": "James", "quote": "I deploy manually every time", "doc_link": "https://docs.google.com/document/d/abc/edit"},
        ],
    }
    text = render_idea_text(idea)
    assert "Auto-Deployer" in text
    assert "7.5" in text
    assert "Starting Point" in text or "starting_point" in text.lower()
    assert "Ambitious" in text or "ambitious" in text.lower()
    assert "James" in text
    assert "Scrum" in text
    assert "https://docs.google.com/document/d/abc/edit" in text


def test_render_weekly_header():
    stats = {"meetings_processed": 5, "ideas_generated": 12, "cross_connections": 3}
    text = render_weekly_header("Week of Jul 14, 2026", stats)
    assert "Jul 14" in text
    assert "5" in text
    assert "12" in text


def test_render_favourites_text():
    starred = [
        {"title": "Great Idea", "overall_score": 9.0, "status": "exploring", "starred": True},
        {"title": "Another One", "overall_score": 7.5, "status": None, "starred": True},
    ]
    text = render_favourites_text(starred)
    assert "Great Idea" in text
    assert "Another One" in text
    assert "exploring" in text


def test_render_signals_text():
    signals = {
        "friction": [
            {"text": "I deploy manually every time", "meeting": "Scrum", "speaker": "James"},
        ],
        "gap": [
            {"text": "Nobody owns the auth middleware", "meeting": "Scrum", "speaker": "Sarah"},
        ],
        "collision": [],
        "intensity": [],
        "pattern": [],
        "meeting_summaries": [
            {"meeting": "Scrum", "date": "Jul 17", "summary": "Frustration with manual deployments, nobody owning auth middleware"},
        ],
    }
    text = render_signals_text(signals)
    assert "Meeting Signals" in text
    assert "Scrum" in text
    assert "Jul 17" in text
    assert "Frustration with manual deployments" in text
    assert "FRICTION" in text
    assert "James" in text
    assert "GAP" in text
    assert "Sarah" in text


def test_render_signals_text_empty():
    signals = {"friction": [], "gap": [], "collision": [], "intensity": [], "pattern": [], "meeting_summaries": []}
    text = render_signals_text(signals)
    assert text == ""


if __name__ == "__main__":
    test_render_idea_text()
    print("✓ render_idea_text")
    test_render_weekly_header()
    print("✓ render_weekly_header")
    test_render_favourites_text()
    print("✓ render_favourites_text")
    test_render_signals_text()
    print("✓ render_signals_text")
    test_render_signals_text_empty()
    print("✓ render_signals_text empty")
    print("\nAll doc_renderer tests passed.")
