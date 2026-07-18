import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.web_renderer import render_dashboard


def test_render_dashboard_creates_file():
    data = {
        "ideas": [
            {
                "id": "test-1",
                "title": "Test Idea",
                "description": "A test idea",
                "category": "work",
                "tags": ["agent-ops"],
                "overall_score": 8.0,
                "scores": {"frustration_intensity": 8, "grace_fit": 7},
                "created": "2026-07-17",
                "evidence": [],
                "starting_point": "Build it",
                "ambitious_version": "Scale it",
                "status": None,
                "starred": False,
                "related_ideas": [],
            }
        ],
        "trends": {},
        "people": {},
    }
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "dashboard.html")
        render_dashboard(data, path)
        assert os.path.exists(path)
        with open(path) as f:
            html = f.read()
        assert "Test Idea" in html
        assert "agent-ops" in html
        assert "8.0" in html


def test_render_dashboard_empty():
    data = {"ideas": [], "trends": {}, "people": {}}
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "dashboard.html")
        render_dashboard(data, path)
        with open(path) as f:
            html = f.read()
        assert "No ideas yet" in html or "<!DOCTYPE html>" in html


def test_render_dashboard_filter_buttons():
    data = {
        "ideas": [
            {"id": "a", "title": "A", "tags": ["security"], "category": "work", "overall_score": 9, "scores": {}, "created": "2026-07-17", "evidence": [], "starting_point": "", "ambitious_version": "", "status": None, "starred": False, "related_ideas": []},
            {"id": "b", "title": "B", "tags": ["agent-ops"], "category": "startup", "overall_score": 7, "scores": {}, "created": "2026-07-17", "evidence": [], "starting_point": "", "ambitious_version": "", "status": None, "starred": False, "related_ideas": []},
        ],
        "trends": {},
        "people": {},
    }
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "dashboard.html")
        render_dashboard(data, path)
        with open(path) as f:
            html = f.read()
        assert "security" in html
        assert "agent-ops" in html
        assert "filter" in html.lower() or "Filter" in html


def test_render_dashboard_with_signals():
    data = {
        "ideas": [
            {"id": "test-1", "title": "Test Idea", "description": "A test", "category": "work", "tags": [], "overall_score": 8.0, "scores": {}, "created": "2026-07-17", "evidence": [], "starting_point": "", "ambitious_version": "", "status": None, "starred": False, "related_ideas": []},
        ],
        "meeting_signals": [
            {"meeting": "Scrum", "date": "Jul 17", "summary": "Frustration with manual triage"},
            {"meeting": "Platform Weekly", "date": "Jul 17", "summary": "CI pipelines keep breaking"},
        ],
        "trends": {},
        "people": {},
    }
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "dashboard.html")
        render_dashboard(data, path)
        with open(path) as f:
            html = f.read()
        assert "Meeting Signals" in html
        assert "Scrum" in html
        assert "Frustration with manual triage" in html
        assert "Platform Weekly" in html
        assert "CI pipelines keep breaking" in html


def test_render_dashboard_no_signals():
    data = {"ideas": [], "trends": {}, "people": {}}
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "dashboard.html")
        render_dashboard(data, path)
        with open(path) as f:
            html = f.read()
        assert "Meeting Signals" not in html


if __name__ == "__main__":
    test_render_dashboard_creates_file()
    print("✓ render_dashboard creates file")
    test_render_dashboard_empty()
    print("✓ render_dashboard empty")
    test_render_dashboard_filter_buttons()
    print("✓ render_dashboard filter buttons")
    test_render_dashboard_with_signals()
    print("✓ render_dashboard with signals")
    test_render_dashboard_no_signals()
    print("✓ render_dashboard no signals")
    print("\nAll web_renderer tests passed.")
