import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.analyzer import (
    _build_extraction_prompt,
    _build_persona_prompt,
    _build_cross_meeting_prompt,
    _build_scoring_prompt,
    _build_startup_prompt,
    _parse_json_response,
)


def test_build_extraction_prompt():
    transcripts = [
        {"meeting_name": "Scrum", "date": "2026-07-17", "text": "We keep manually deploying."},
    ]
    prompt = _build_extraction_prompt(transcripts)
    assert "FRICTION" in prompt
    assert "GAP" in prompt
    assert "manually deploying" in prompt
    assert "Scrum" in prompt


def test_build_extraction_prompt_includes_meeting_summaries():
    transcripts = [
        {"meeting_name": "Scrum", "date": "2026-07-17", "text": "We keep manually deploying."},
    ]
    prompt = _build_extraction_prompt(transcripts)
    assert "meeting_summaries" in prompt
    assert "summary" in prompt
    assert "TL;DR" in prompt


def test_build_persona_prompt():
    signals = {"friction": [{"text": "manual deployments", "meeting": "Scrum"}]}
    persona = {"name": "logistics coordinator", "prompt": "You are a logistics coordinator."}
    prompt = _build_persona_prompt(signals, persona)
    assert "logistics coordinator" in prompt.lower() or "logistics" in prompt.lower()
    assert "Inversion" in prompt or "inversion" in prompt
    assert "manual deployments" in prompt


def test_build_cross_meeting_prompt():
    signals = {"friction": [{"text": "auth is broken", "meeting": "Security Sync"}]}
    transcripts = [
        {"meeting_name": "Security Sync", "text": "Auth keeps failing"},
        {"meeting_name": "Platform Weekly", "text": "We built a new auth service"},
    ]
    prompt = _build_cross_meeting_prompt(signals, transcripts)
    assert "Security Sync" in prompt
    assert "Platform Weekly" in prompt


def test_build_scoring_prompt():
    raw_ideas = [{"title": "Auto-deployer", "description": "Automates deployments"}]
    existing = [{"title": "Old Idea", "id": "old"}]
    prompt = _build_scoring_prompt(raw_ideas, existing)
    assert "frustration_intensity" in prompt
    assert "Auto-deployer" in prompt


def test_build_startup_prompt():
    ideas = [{"title": "Auto-deployer", "description": "Automates deployments", "overall_score": 8.5}]
    prompt = _build_startup_prompt(ideas)
    assert "customer" in prompt.lower() or "business" in prompt.lower()
    assert "Auto-deployer" in prompt


def test_parse_json_response_clean():
    response = '{"ideas": [{"title": "Test"}]}'
    result = _parse_json_response(response)
    assert result["ideas"][0]["title"] == "Test"


def test_parse_json_response_markdown_wrapped():
    response = '```json\n{"ideas": [{"title": "Test"}]}\n```'
    result = _parse_json_response(response)
    assert result["ideas"][0]["title"] == "Test"


def test_parse_json_response_with_preamble():
    response = 'Here are the results:\n\n{"ideas": [{"title": "Test"}]}'
    result = _parse_json_response(response)
    assert result["ideas"][0]["title"] == "Test"


def test_parse_json_response_bare_array():
    response = '[{"title": "Test"}]'
    result = _parse_json_response(response)
    assert result == {"ideas": [{"title": "Test"}]}


def test_build_scoring_prompt_includes_jira_coverage():
    raw_ideas = [{"title": "Auto-deployer", "description": "Automates deployments"}]
    existing = [{"title": "Old Idea", "id": "old"}]
    jira_coverage = {
        "Auto-deployer": {
            "covered": True,
            "issue_count": 2,
            "issues": [
                {"key": "RHAIENG-100", "summary": "Deploy automation", "status": "In Progress", "type": "Epic"},
                {"key": "RHAIENG-101", "summary": "CI pipeline", "status": "Done", "type": "Story"},
            ],
        }
    }
    prompt = _build_scoring_prompt(raw_ideas, existing, jira_coverage=jira_coverage)
    assert "JIRA COVERAGE" in prompt
    assert "RHAIENG-100" in prompt
    assert "In Progress" in prompt


def test_build_scoring_prompt_without_jira_coverage():
    raw_ideas = [{"title": "Auto-deployer", "description": "Automates deployments"}]
    existing = [{"title": "Old Idea", "id": "old"}]
    prompt = _build_scoring_prompt(raw_ideas, existing)
    assert "nobody_owns_this" in prompt
    assert "JIRA COVERAGE" not in prompt


if __name__ == "__main__":
    test_build_extraction_prompt()
    print("✓ build_extraction_prompt")
    test_build_extraction_prompt_includes_meeting_summaries()
    print("✓ build_extraction_prompt includes meeting_summaries")
    test_build_persona_prompt()
    print("✓ build_persona_prompt")
    test_build_cross_meeting_prompt()
    print("✓ build_cross_meeting_prompt")
    test_build_scoring_prompt()
    print("✓ build_scoring_prompt")
    test_build_scoring_prompt_includes_jira_coverage()
    print("✓ build_scoring_prompt includes jira coverage")
    test_build_scoring_prompt_without_jira_coverage()
    print("✓ build_scoring_prompt without jira coverage")
    test_build_startup_prompt()
    print("✓ build_startup_prompt")
    test_parse_json_response_clean()
    print("✓ parse_json_response clean")
    test_parse_json_response_markdown_wrapped()
    print("✓ parse_json_response markdown wrapped")
    test_parse_json_response_with_preamble()
    print("✓ parse_json_response with preamble")
    test_parse_json_response_bare_array()
    print("✓ parse_json_response bare array")
    print("\nAll analyzer tests passed.")
