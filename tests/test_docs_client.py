import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.docs_client import extract_doc_id, extract_text_from_doc_json, read_radar_annotations


def test_extract_doc_id_edit_url():
    url = "https://docs.google.com/document/d/1abc123def/edit"
    assert extract_doc_id(url) == "1abc123def"


def test_extract_doc_id_view_url():
    url = "https://docs.google.com/document/d/xyz789abc/edit#heading=h.abc"
    assert extract_doc_id(url) == "xyz789abc"


def test_extract_doc_id_bare():
    url = "https://docs.google.com/document/d/onlyid"
    assert extract_doc_id(url) == "onlyid"


def test_extract_text_from_doc_json():
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "gemini_doc.json")
    with open(fixture_path) as f:
        doc = json.load(f)
    text = extract_text_from_doc_json(doc)
    assert "Meeting Summary" in text
    assert "OpenShell sandbox" in text
    assert "contributing upstream" in text


def test_read_radar_annotations_star_emoji():
    text = "⭐ Some Idea\nDescription here\nAnother Idea\nNo star"
    annotations = read_radar_annotations(text)
    assert "Some Idea" in annotations
    assert annotations["Some Idea"] == "starred"


def test_read_radar_annotations_asterisk_prefix():
    text = "Score: 7.4/10\n*Auto-Deployer Agent\nDescription"
    annotations = read_radar_annotations(text)
    assert "Auto-Deployer Agent" in annotations
    assert annotations["Auto-Deployer Agent"] == "starred"


def test_read_radar_annotations_asterisk_suffix():
    text = "Score: 7.4/10\nAuto-Deployer Agent*\nDescription"
    annotations = read_radar_annotations(text)
    assert "Auto-Deployer Agent" in annotations
    assert annotations["Auto-Deployer Agent"] == "starred"


def test_read_radar_annotations_status():
    text = "Build Agent [exploring]\nSome text\nDeploy Tool [building]\nMore text"
    annotations = read_radar_annotations(text)
    assert annotations.get("Build Agent") == "exploring"
    assert annotations.get("Deploy Tool") == "building"


def test_read_radar_annotations_empty():
    text = "Plain Idea\nNo markers here"
    annotations = read_radar_annotations(text)
    assert len(annotations) == 0


def test_read_radar_annotations_ignores_bold_double_asterisk():
    text = "**Bold Text**\nNot a star marker"
    annotations = read_radar_annotations(text)
    assert len(annotations) == 0


if __name__ == "__main__":
    test_extract_doc_id_edit_url()
    print("✓ extract_doc_id edit URL")
    test_extract_doc_id_view_url()
    print("✓ extract_doc_id view URL")
    test_extract_doc_id_bare()
    print("✓ extract_doc_id bare")
    test_extract_text_from_doc_json()
    print("✓ extract_text_from_doc_json")
    test_read_radar_annotations_star_emoji()
    print("✓ read_radar_annotations ⭐ emoji")
    test_read_radar_annotations_asterisk_prefix()
    print("✓ read_radar_annotations * prefix")
    test_read_radar_annotations_asterisk_suffix()
    print("✓ read_radar_annotations * suffix")
    test_read_radar_annotations_status()
    print("✓ read_radar_annotations status")
    test_read_radar_annotations_empty()
    print("✓ read_radar_annotations empty")
    test_read_radar_annotations_ignores_bold_double_asterisk()
    print("✓ read_radar_annotations ignores ** bold")
    print("\nAll docs_client tests passed.")
