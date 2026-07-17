import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.radar_store import (
    load_radar,
    save_radar,
    add_ideas,
    update_annotations,
    generate_idea_id,
    get_starred,
)


def test_load_radar_missing():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "radar.json")
        data = load_radar(path)
        assert data["ideas"] == []
        assert data["trends"] == {}
        assert data["people"] == {}


def test_load_radar_existing():
    fixture = os.path.join(os.path.dirname(__file__), "fixtures", "radar_sample.json")
    data = load_radar(fixture)
    assert len(data["ideas"]) == 1
    assert data["ideas"][0]["title"] == "Policy-Aware Model Router"


def test_save_radar_atomic():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "radar.json")
        data = {"ideas": [], "trends": {}, "people": {}}
        save_radar(data, path)
        with open(path) as f:
            loaded = json.load(f)
        assert loaded["ideas"] == []


def test_add_ideas_no_duplicates():
    data = {"ideas": [{"id": "existing-idea", "title": "Existing"}], "trends": {}, "people": {}}
    new = [
        {"id": "existing-idea", "title": "Existing Updated"},
        {"id": "brand-new", "title": "Brand New"},
    ]
    updated = add_ideas(data, new)
    assert len(updated["ideas"]) == 2
    existing = [i for i in updated["ideas"] if i["id"] == "existing-idea"][0]
    assert existing["title"] == "Existing"


def test_add_ideas_appends():
    data = {"ideas": [], "trends": {}, "people": {}}
    new = [{"id": "idea-1", "title": "First"}, {"id": "idea-2", "title": "Second"}]
    updated = add_ideas(data, new)
    assert len(updated["ideas"]) == 2


def test_generate_idea_id():
    result = generate_idea_id("Policy-Aware Model Router", "2026-07-17")
    assert result == "2026-07-17-policy-aware-model-router"


def test_generate_idea_id_special_chars():
    result = generate_idea_id("What's the Deal? (v2)", "2026-07-17")
    assert "?" not in result
    assert "'" not in result
    assert result.startswith("2026-07-17-")


def test_update_annotations():
    data = {
        "ideas": [
            {"id": "a", "title": "Build Agent", "status": None, "starred": False},
            {"id": "b", "title": "Deploy Tool", "status": None, "starred": False},
        ],
        "trends": {},
        "people": {},
    }
    annotations = {"Build Agent": "exploring", "Deploy Tool": "starred"}
    updated = update_annotations(data, annotations)
    agent = [i for i in updated["ideas"] if i["id"] == "a"][0]
    tool = [i for i in updated["ideas"] if i["id"] == "b"][0]
    assert agent["status"] == "exploring"
    assert tool["starred"] is True


def test_get_starred():
    data = {
        "ideas": [
            {"id": "a", "title": "Starred One", "starred": True, "status": None},
            {"id": "b", "title": "Not Starred", "starred": False, "status": None},
            {"id": "c", "title": "Exploring", "starred": False, "status": "exploring"},
        ],
        "trends": {},
        "people": {},
    }
    result = get_starred(data)
    titles = [i["title"] for i in result]
    assert "Starred One" in titles
    assert "Exploring" in titles
    assert "Not Starred" not in titles


if __name__ == "__main__":
    test_load_radar_missing()
    print("✓ load_radar missing")
    test_load_radar_existing()
    print("✓ load_radar existing")
    test_save_radar_atomic()
    print("✓ save_radar atomic")
    test_add_ideas_no_duplicates()
    print("✓ add_ideas no duplicates")
    test_add_ideas_appends()
    print("✓ add_ideas appends")
    test_generate_idea_id()
    print("✓ generate_idea_id")
    test_generate_idea_id_special_chars()
    print("✓ generate_idea_id special chars")
    test_update_annotations()
    print("✓ update_annotations")
    test_get_starred()
    print("✓ get_starred")
    print("\nAll radar_store tests passed.")
