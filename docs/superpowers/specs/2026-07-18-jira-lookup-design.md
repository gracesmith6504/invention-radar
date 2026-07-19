# Jira Lookup for Invention Radar

## Summary

Add a Jira lookup step to the scoring pipeline so the "nobody_owns_this" score is based on real Jira data instead of LLM guessing.

## Problem

The current scoring pipeline asks the LLM to rate "nobody_owns_this" 1-10, but the LLM has no visibility into what work is actually tracked in Jira. It guesses based on the meeting transcript context alone, producing scores that are essentially vibes.

## Solution

A new module `lib/jira_lookup.py` that queries the Jira REST API during the `consolidate_and_score()` step. For each candidate idea, it searches for existing epics, stories, and bugs that cover the same problem area. The results are injected into the scoring prompt so the LLM can make an informed judgment.

## New Module: `lib/jira_lookup.py`

### Interface

```python
def lookup_existing_work(ideas: list[dict]) -> dict[str, dict]:
    """For each idea, search Jira for existing work covering the same area.

    Args:
        ideas: list of raw idea dicts with at least 'title' and 'tags'

    Returns:
        dict keyed by idea title, each value:
        {
            "covered": bool,       # True if matching issues found
            "issue_count": int,    # Number of matching issues
            "issues": [            # Up to 5 matching issues
                {"key": "RHAIENG-1234", "summary": "...", "status": "...", "type": "..."}
            ]
        }
    """
```

### Auth

Uses Jira Cloud Basic Auth (email + API token), same credentials as the existing MCP setup.

Three new environment variables:
- `JIRA_URL` — defaults to `https://redhat.atlassian.net`
- `JIRA_EMAIL` — Red Hat email
- `JIRA_API_TOKEN` — Jira API token

### Query Strategy

For each idea, build a JQL query from its title keywords and tags:

```
project = RHAIENG AND component = AgentOps AND text ~ "keyword1 keyword2"
```

- Strip English stop words (the, a, is, for, with, etc.) from the title to get meaningful search terms
- Use the idea's tags to narrow by component where possible
- Limit to 5 results per idea (enough to determine coverage, not a full audit)
- If the Jira lookup fails (network, auth), fall back gracefully — log a warning and let the LLM score without data (same as today)

### Performance

Ideas are scored in a single LLM call. The Jira lookups happen before that call, one HTTP request per idea. With typical runs producing 5-15 candidate ideas, that's 5-15 Jira API calls — negligible latency.

## Changes to Existing Code

### `config.py`

Add three new env vars:

```python
JIRA_URL = os.environ.get("JIRA_URL", "https://redhat.atlassian.net")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL", "")
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN", "")
```

### `analyzer.py`

In `consolidate_and_score()`, call `lookup_existing_work(raw_ideas)` before building the scoring prompt. Pass the results into `_build_scoring_prompt()`.

Update `_build_scoring_prompt()` to include a new section:

```
JIRA COVERAGE (real data — use this for nobody_owns_this scoring):
- "Agent identity rotation": 3 matching issues found (RHAIENG-5501 Epic "Agent Identity Lifecycle" — In Progress, RHAIENG-5823 Story — Done, ...)
- "Sandbox network policy generator": No matching issues found
```

The LLM sees actual Jira state and can score "nobody_owns_this" accordingly: low score if there's an active epic, high score if Jira is empty.

### `manifests/`

Add `JIRA_EMAIL` and `JIRA_API_TOKEN` to the `invention-radar-secrets` Secret in the OpenShift manifests.

## What Does NOT Change

- Gmail client, transcript reading
- Signal extraction pipeline
- Persona ideation
- Cross-meeting synthesis
- Doc renderer, web renderer
- Slack notifications
- State management

## Testing

New test file `tests/test_jira_lookup.py`:
- Test JQL query construction from idea titles/tags
- Test response parsing (matching issues found, no matches, malformed response)
- Test graceful fallback when Jira is unreachable
- Mock the HTTP layer — no live Jira calls in tests

## Failure Modes

- **Jira unreachable:** Log warning, score without Jira data (same as today). The radar still produces ideas, just with less-grounded "nobody_owns_this" scores.
- **Bad credentials:** Same as unreachable — graceful fallback.
- **No matching issues:** Not a failure. This is the signal that nobody owns it — score high.
- **Too many matches:** Cap at 5 per idea. The LLM doesn't need an exhaustive list.
