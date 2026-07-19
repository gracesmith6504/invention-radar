import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.doc_renderer import DocBuilder, build_full_update, _week_range, _render_signals, _render_idea


def test_doc_builder_add_heading():
    doc = DocBuilder()
    doc.add_heading("Test Heading", level=1)
    assert len(doc.requests) == 2
    assert doc.requests[0]["insertText"]["text"] == "Test Heading\n"
    assert doc.requests[1]["updateParagraphStyle"]["paragraphStyle"]["namedStyleType"] == "HEADING_1"


def test_doc_builder_add_heading_level2():
    doc = DocBuilder()
    doc.add_heading("Sub Heading", level=2)
    assert doc.requests[1]["updateParagraphStyle"]["paragraphStyle"]["namedStyleType"] == "HEADING_2"


def test_doc_builder_add_text():
    doc = DocBuilder()
    doc.add_text("Hello world")
    assert len(doc.requests) == 1
    assert doc.requests[0]["insertText"]["text"] == "Hello world\n"
    assert doc.index == 1 + len("Hello world\n")


def test_doc_builder_add_bold_text():
    doc = DocBuilder()
    doc.add_bold_text("Bold text")
    assert len(doc.requests) == 2
    assert doc.requests[0]["insertText"]["text"] == "Bold text\n"
    style_req = doc.requests[1]["updateTextStyle"]
    assert style_req["textStyle"]["bold"] is True


def test_doc_builder_add_bullet():
    doc = DocBuilder()
    doc.add_bullet("Bullet item")
    assert len(doc.requests) == 2
    assert doc.requests[0]["insertText"]["text"] == "Bullet item\n"
    assert "createParagraphBullets" in doc.requests[1]


def test_doc_builder_add_colored_text():
    doc = DocBuilder()
    doc.add_colored_text("Blue text", {"red": 0, "green": 0, "blue": 1})
    style_req = doc.requests[1]["updateTextStyle"]
    assert style_req["textStyle"]["foregroundColor"]["color"]["rgbColor"]["blue"] == 1


def test_doc_builder_add_inline():
    doc = DocBuilder()
    doc.add_inline([("Label: ", {"bold": True}), ("value", {})])
    assert len(doc.requests) >= 2
    texts = [r["insertText"]["text"] for r in doc.requests if "insertText" in r]
    assert "Label: " in texts
    assert "value\n" in texts


def test_doc_builder_index_tracking():
    doc = DocBuilder(start_index=1)
    doc.add_text("abc")
    assert doc.index == 1 + len("abc\n")
    doc.add_text("def")
    assert doc.index == 1 + len("abc\n") + len("def\n")


def test_week_range_format():
    result = _week_range()
    assert "–" in result
    assert "20" in result  # year


def test_render_signals():
    doc = DocBuilder()
    signals = {
        "friction": [{"text": "manual deploy", "meeting": "Scrum", "speaker": "James"}],
        "gap": [],
        "collision": [],
        "intensity": [],
        "pattern": [],
        "meeting_summaries": [
            {"meeting": "Scrum", "date": "Jul 17", "summary": "Frustration with deployments"},
        ],
    }
    _render_signals(doc, signals)
    all_text = " ".join(r["insertText"]["text"] for r in doc.requests if "insertText" in r)
    assert "Meeting Signals" in all_text
    assert "Scrum" in all_text
    assert "Frustration with deployments" in all_text
    assert "manual deploy" in all_text


def test_render_signals_empty():
    doc = DocBuilder()
    _render_signals(doc, {"friction": [], "gap": [], "collision": [], "intensity": [], "pattern": [], "meeting_summaries": []})
    assert len(doc.requests) == 0


def test_build_full_update_returns_requests():
    radar_data = {"ideas": [], "trends": {}, "people": {}}
    new_ideas = [
        {
            "id": "test-1",
            "title": "Auto-Deployer",
            "description": "Automates deployments.",
            "tags": ["agent-ops"],
            "starting_point": "Script that watches a branch.",
            "ambitious_version": "Full GitOps pipeline.",
            "scores": {"frustration_intensity": 8, "grace_fit": 7},
            "overall_score": 7.5,
            "evidence": [{"speaker": "James", "meeting": "Scrum", "quote": "I deploy manually", "doc_link": ""}],
            "category": "work",
            "status": None,
            "starred": False,
            "related_ideas": [],
            "created": "2026-07-17",
        }
    ]
    requests = build_full_update(radar_data, new_ideas)
    assert isinstance(requests, list)
    assert len(requests) > 1

    req_types = set()
    for r in requests:
        req_types.update(r.keys())
    assert "insertText" in req_types
    assert "updateParagraphStyle" in req_types
    assert "updateTextStyle" in req_types

    all_text = " ".join(r["insertText"]["text"] for r in requests if "insertText" in r)
    assert "Auto-Deployer" in all_text
    assert "Favourites" in all_text
    assert "Work Ideas" in all_text
    assert "Starting Point" in all_text


def test_starred_idea_gets_star_emoji():
    doc = DocBuilder()
    idea = {
        "title": "Auto-Deployer",
        "starred": True,
        "overall_score": 8,
        "description": "Deploys things.",
        "tags": [],
        "evidence": [],
        "scores": {},
    }
    _render_idea(doc, idea)
    all_text = " ".join(r["insertText"]["text"] for r in doc.requests if "insertText" in r)
    assert "⭐ Auto-Deployer" in all_text


def test_unstarred_idea_no_emoji():
    doc = DocBuilder()
    idea = {
        "title": "Auto-Deployer",
        "starred": False,
        "overall_score": 8,
        "description": "Deploys things.",
        "tags": [],
        "evidence": [],
        "scores": {},
    }
    _render_idea(doc, idea)
    all_text = " ".join(r["insertText"]["text"] for r in doc.requests if "insertText" in r)
    assert "⭐" not in all_text
    assert "Auto-Deployer" in all_text


def test_build_full_update_with_signals():
    radar_data = {"ideas": [], "trends": {}, "people": {}}
    signals = {
        "friction": [{"text": "manual CI", "meeting": "Scrum", "speaker": "Alex"}],
        "gap": [], "collision": [], "intensity": [], "pattern": [],
        "meeting_summaries": [{"meeting": "Scrum", "date": "Jul 17", "summary": "CI pain"}],
    }
    requests = build_full_update(radar_data, [], signals)
    all_text = " ".join(r["insertText"]["text"] for r in requests if "insertText" in r)
    assert "Meeting Signals" in all_text
    assert "CI pain" in all_text


if __name__ == "__main__":
    test_doc_builder_add_heading()
    print("✓ DocBuilder add_heading")
    test_doc_builder_add_heading_level2()
    print("✓ DocBuilder add_heading level 2")
    test_doc_builder_add_text()
    print("✓ DocBuilder add_text")
    test_doc_builder_add_bold_text()
    print("✓ DocBuilder add_bold_text")
    test_doc_builder_add_bullet()
    print("✓ DocBuilder add_bullet")
    test_doc_builder_add_colored_text()
    print("✓ DocBuilder add_colored_text")
    test_doc_builder_add_inline()
    print("✓ DocBuilder add_inline")
    test_doc_builder_index_tracking()
    print("✓ DocBuilder index tracking")
    test_week_range_format()
    print("✓ week_range format")
    test_render_signals()
    print("✓ render_signals")
    test_render_signals_empty()
    print("✓ render_signals empty")
    test_starred_idea_gets_star_emoji()
    print("✓ starred idea gets ⭐ emoji")
    test_unstarred_idea_no_emoji()
    print("✓ unstarred idea no emoji")
    test_build_full_update_returns_requests()
    print("✓ build_full_update returns requests")
    test_build_full_update_with_signals()
    print("✓ build_full_update with signals")
    print("\nAll doc_renderer tests passed.")
