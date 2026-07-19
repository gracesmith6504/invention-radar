# Jira Lookup Integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Jira REST API lookup to the scoring pipeline so "nobody_owns_this" is scored against real Jira data instead of LLM guessing.

**Architecture:** New module `lib/jira_lookup.py` queries Jira Cloud for each candidate idea before scoring. Results are injected into the scoring prompt. Everything else in the pipeline stays untouched.

**Tech Stack:** Python 3.12, `requests` (new dependency), Jira Cloud REST API v2, existing `openai` SDK

## Global Constraints

- Python 3.12+ required
- All tests use `unittest` with `sys.path` insert pattern (matching existing test files)
- No new test frameworks — no pytest, no pytest fixtures
- Jira auth uses Basic Auth (email + API token), same credentials as the MCP setup
- Jira URL defaults to `https://redhat.atlassian.net`
- Graceful fallback on all Jira failures — the radar must still work without Jira

---

### Task 1: Jira Lookup Module

**Files:**
- Create: `lib/jira_lookup.py`
- Create: `tests/test_jira_lookup.py`
- Modify: `requirements.txt`

**Interfaces:**
- Consumes: list of idea dicts with `title` (str) and `tags` (list[str]) keys
- Produces: `lookup_existing_work(ideas: list[dict]) -> dict[str, dict]` — keyed by idea title, each value has `covered` (bool), `issue_count` (int), `issues` (list of `{"key", "summary", "status", "type"}`)

- [ ] **Step 1: Add `requests` to requirements.txt**

```
openai>=1.30.0
requests>=2.31.0
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_jira_lookup.py`:

```python
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.jira_lookup import build_jql, extract_keywords, lookup_existing_work


class TestExtractKeywords(unittest.TestCase):
    def test_strips_stop_words(self):
        keywords = extract_keywords("A tool for the automatic deployment of agents")
        self.assertNotIn("a", keywords)
        self.assertNotIn("for", keywords)
        self.assertNotIn("the", keywords)
        self.assertNotIn("of", keywords)
        self.assertIn("automatic", keywords)
        self.assertIn("deployment", keywords)
        self.assertIn("agents", keywords)

    def test_empty_title(self):
        keywords = extract_keywords("")
        self.assertEqual(keywords, [])

    def test_short_words_excluded(self):
        keywords = extract_keywords("An AI fix for it")
        for kw in keywords:
            self.assertGreater(len(kw), 2)


class TestBuildJql(unittest.TestCase):
    def test_basic_query(self):
        jql = build_jql("Auto-deployer", ["agent-ops", "automation"])
        self.assertIn("project = RHAIENG", jql)
        self.assertIn("text ~", jql)

    def test_includes_component(self):
        jql = build_jql("Identity rotation", ["agent-ops"])
        self.assertIn("component = AgentOps", jql)

    def test_no_matching_component(self):
        jql = build_jql("Some idea", ["unrelated-tag"])
        self.assertNotIn("component =", jql)

    def test_escapes_quotes_in_keywords(self):
        jql = build_jql('Fix "broken" auth', ["agent-ops"])
        self.assertNotIn('"broken"', jql.split("text ~")[1].split('"')[1])


class TestLookupExistingWork(unittest.TestCase):
    @patch("lib.jira_lookup._jira_search")
    def test_returns_coverage_when_issues_found(self, mock_search):
        mock_search.return_value = {
            "issues": [
                {
                    "key": "RHAIENG-1234",
                    "fields": {
                        "summary": "Agent identity lifecycle",
                        "status": {"name": "In Progress"},
                        "issuetype": {"name": "Epic"},
                    },
                }
            ]
        }
        ideas = [{"title": "Agent identity rotation", "tags": ["agent-ops"]}]
        result = lookup_existing_work(ideas)
        entry = result["Agent identity rotation"]
        self.assertTrue(entry["covered"])
        self.assertEqual(entry["issue_count"], 1)
        self.assertEqual(entry["issues"][0]["key"], "RHAIENG-1234")
        self.assertEqual(entry["issues"][0]["status"], "In Progress")

    @patch("lib.jira_lookup._jira_search")
    def test_returns_not_covered_when_no_issues(self, mock_search):
        mock_search.return_value = {"issues": []}
        ideas = [{"title": "Brand new concept", "tags": ["automation"]}]
        result = lookup_existing_work(ideas)
        entry = result["Brand new concept"]
        self.assertFalse(entry["covered"])
        self.assertEqual(entry["issue_count"], 0)
        self.assertEqual(entry["issues"], [])

    @patch("lib.jira_lookup._jira_search")
    def test_graceful_fallback_on_exception(self, mock_search):
        mock_search.side_effect = Exception("Connection refused")
        ideas = [{"title": "Some idea", "tags": ["agent-ops"]}]
        result = lookup_existing_work(ideas)
        entry = result["Some idea"]
        self.assertFalse(entry["covered"])
        self.assertEqual(entry["issue_count"], 0)

    @patch("lib.jira_lookup._jira_search")
    def test_caps_at_five_issues(self, mock_search):
        mock_search.return_value = {
            "issues": [
                {
                    "key": f"RHAIENG-{i}",
                    "fields": {
                        "summary": f"Issue {i}",
                        "status": {"name": "Open"},
                        "issuetype": {"name": "Bug"},
                    },
                }
                for i in range(10)
            ]
        }
        ideas = [{"title": "Overloaded area", "tags": ["agent-ops"]}]
        result = lookup_existing_work(ideas)
        self.assertLessEqual(len(result["Overloaded area"]["issues"]), 5)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python3 tests/test_jira_lookup.py`
Expected: `ModuleNotFoundError: No module named 'lib.jira_lookup'`

- [ ] **Step 4: Implement `lib/jira_lookup.py`**

```python
import os
import requests
import config


STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "as", "be", "was", "are",
    "been", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "this", "that", "these", "those",
    "not", "no", "so", "if", "then", "than", "too", "very", "just",
    "about", "up", "out", "all", "into", "also", "how", "what", "when",
    "where", "who", "which", "each", "every", "any", "our", "your",
    "their", "its", "we", "they", "you", "he", "she", "my",
}

TAG_TO_COMPONENT = {
    "agent-ops": "AgentOps",
}


def extract_keywords(title: str) -> list[str]:
    words = title.lower().replace("-", " ").split()
    cleaned = []
    for w in words:
        stripped = "".join(c for c in w if c.isalnum())
        if stripped and stripped not in STOP_WORDS and len(stripped) > 2:
            cleaned.append(stripped)
    return cleaned


def build_jql(title: str, tags: list[str]) -> str:
    keywords = extract_keywords(title)
    parts = ["project = RHAIENG"]

    for tag in tags:
        component = TAG_TO_COMPONENT.get(tag)
        if component:
            parts.append(f"component = {component}")
            break

    if keywords:
        keyword_str = " ".join(keywords)
        safe_str = keyword_str.replace('"', "")
        parts.append(f'text ~ "{safe_str}"')

    return " AND ".join(parts)


def _jira_search(jql: str, max_results: int = 5) -> dict:
    url = f"{config.JIRA_URL}/rest/api/2/search"
    auth = (config.JIRA_EMAIL, config.JIRA_API_TOKEN)
    params = {
        "jql": jql,
        "maxResults": max_results,
        "fields": "summary,status,issuetype",
    }
    resp = requests.get(url, params=params, auth=auth, timeout=10)
    resp.raise_for_status()
    return resp.json()


def lookup_existing_work(ideas: list[dict]) -> dict[str, dict]:
    results = {}
    for idea in ideas:
        title = idea.get("title", "")
        tags = idea.get("tags", [])
        try:
            jql = build_jql(title, tags)
            data = _jira_search(jql)
            issues = data.get("issues", [])[:5]
            parsed = [
                {
                    "key": iss["key"],
                    "summary": iss["fields"]["summary"],
                    "status": iss["fields"]["status"]["name"],
                    "type": iss["fields"]["issuetype"]["name"],
                }
                for iss in issues
            ]
            results[title] = {
                "covered": len(parsed) > 0,
                "issue_count": len(parsed),
                "issues": parsed,
            }
        except Exception as e:
            print(f"Jira lookup failed for '{title}': {e}")
            results[title] = {
                "covered": False,
                "issue_count": 0,
                "issues": [],
            }
    return results
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 tests/test_jira_lookup.py`
Expected: all 8 tests pass

- [ ] **Step 6: Commit**

```bash
git add lib/jira_lookup.py tests/test_jira_lookup.py requirements.txt
git commit -m "feat: add Jira lookup module for nobody_owns_this scoring"
```

---

### Task 2: Config + Analyzer Integration

**Files:**
- Modify: `config.py:1-50`
- Modify: `lib/analyzer.py:97-248`
- Modify: `tests/test_analyzer.py`

**Interfaces:**
- Consumes: `lookup_existing_work(ideas)` from `lib/jira_lookup` (Task 1)
- Produces: updated `consolidate_and_score()` that injects Jira data into the scoring prompt; updated `_build_scoring_prompt()` accepting an optional `jira_coverage` parameter

- [ ] **Step 1: Write the failing test**

Add to the bottom of `tests/test_analyzer.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 tests/test_analyzer.py`
Expected: `TypeError: _build_scoring_prompt() got an unexpected keyword argument 'jira_coverage'`

- [ ] **Step 3: Add Jira config vars to `config.py`**

Add after line 20 (after `GOOGLE_REFRESH_TOKEN`):

```python
JIRA_URL = os.environ.get("JIRA_URL", "https://redhat.atlassian.net")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL", "")
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN", "")
```

- [ ] **Step 4: Update `_build_scoring_prompt()` in `lib/analyzer.py`**

Replace the function signature and add the Jira coverage section. Change line 222:

```python
def _build_scoring_prompt(raw_ideas: list[dict], existing_ideas: list[dict], jira_coverage: dict | None = None) -> str:
    ideas_text = json.dumps(raw_ideas, indent=2)
    existing_titles = [i.get("title", "") for i in existing_ideas[:50]]

    jira_section = ""
    if jira_coverage:
        lines = []
        for title, data in jira_coverage.items():
            if data["covered"]:
                issue_strs = [
                    f"{iss['key']} {iss['type']} \"{iss['summary']}\" — {iss['status']}"
                    for iss in data["issues"]
                ]
                lines.append(f"- \"{title}\": {data['issue_count']} matching issues found ({', '.join(issue_strs)})")
            else:
                lines.append(f"- \"{title}\": No matching issues found")
        jira_section = "\n\nJIRA COVERAGE (real data — use this for nobody_owns_this scoring):\n" + "\n".join(lines)

    return f"""Score and deduplicate these invention ideas.

RAW IDEAS:
{ideas_text}

ALREADY EXISTING IDEAS (avoid duplicating these):
{json.dumps(existing_titles)}
{jira_section}

Score each idea on these criteria (1-10):
- frustration_intensity: How painful is this problem based on speaker language?
- nobody_owns_this: Is anyone already working on it? (10 = total vacuum){" Use the JIRA COVERAGE data above as ground truth." if jira_coverage else ""}
- cross_meeting: Does this link signals from multiple meetings?
- repeat_frequency: Has this come up before?
- grace_fit: Does this match Grace's skills? (OpenShell, sandboxing, Python, Jira, agents, security, Kubernetes)
- demo_ability: Could you show this working in 5 minutes?

Rules:
- Discard any idea that duplicates an existing idea
- Discard any idea scoring below 4 overall
- Merge similar ideas into a stronger combined version
- Be harsh — only strong ideas survive

Return JSON with fully formed ideas:
{{"ideas": [{{"id": "", "title": "...", "description": "...", "tags": [...], "starting_point": "...", "ambitious_version": "...", "evidence": [...], "scores": {{"frustration_intensity": N, "nobody_owns_this": N, "cross_meeting": N, "repeat_frequency": N, "grace_fit": N, "demo_ability": N}}, "category": "work"}}]}}"""
```

- [ ] **Step 5: Update `consolidate_and_score()` in `lib/analyzer.py`**

Replace lines 97-98:

```python
def consolidate_and_score(raw_ideas: list[dict], existing_ideas: list[dict]) -> list[dict]:
    jira_coverage = None
    if config.JIRA_EMAIL and config.JIRA_API_TOKEN:
        try:
            from lib.jira_lookup import lookup_existing_work
            jira_coverage = lookup_existing_work(raw_ideas)
            print(f"Jira lookup complete: {sum(1 for v in jira_coverage.values() if v['covered'])}/{len(jira_coverage)} ideas have existing coverage")
        except Exception as e:
            print(f"Jira lookup failed (non-fatal): {e}")

    prompt = _build_scoring_prompt(raw_ideas, existing_ideas, jira_coverage=jira_coverage)
    system = "You are a critical evaluator. Score harshly. Discard weak ideas. Output valid JSON only."
```

The rest of the function (lines 100-120) stays exactly the same.

- [ ] **Step 6: Run tests to verify they pass**

Run: `python3 tests/test_analyzer.py`
Expected: all tests pass (both old and new)

- [ ] **Step 7: Run the full test suite**

Run: `python3 tests/test_jira_lookup.py && python3 tests/test_analyzer.py`
Expected: all tests pass

- [ ] **Step 8: Commit**

```bash
git add config.py lib/analyzer.py tests/test_analyzer.py
git commit -m "feat: integrate Jira lookup into scoring pipeline"
```

---

### Task 3: Manifests Update

**Files:**
- Modify: `manifests/05-secrets.yaml`
- Modify: `manifests/04-cronjob.yaml`

**Interfaces:**
- Consumes: `JIRA_EMAIL` and `JIRA_API_TOKEN` env vars read by `config.py` (Task 2)
- Produces: updated OpenShift manifests that pass Jira credentials to the container

- [ ] **Step 1: Add Jira secrets to `manifests/05-secrets.yaml`**

Add two new entries to the `stringData` section:

```yaml
# TEMPLATE — fill in real values before applying
# kubectl create secret generic invention-radar-secrets -n invention-radar \
#   --from-literal=RADAR_DOC_ID=<your-doc-id> \
#   --from-literal=GOOGLE_CLIENT_ID=<your-client-id> \
#   --from-literal=GOOGLE_CLIENT_SECRET=<your-secret> \
#   --from-literal=GOOGLE_REFRESH_TOKEN=<your-token> \
#   --from-literal=SLACK_WEBHOOK_URL=<your-webhook> \
#   --from-literal=JIRA_EMAIL=<your-email> \
#   --from-literal=JIRA_API_TOKEN=<your-token>
apiVersion: v1
kind: Secret
metadata:
  name: invention-radar-secrets
  namespace: invention-radar
type: Opaque
stringData:
  RADAR_DOC_ID: "REPLACE_ME"
  GOOGLE_CLIENT_ID: "REPLACE_ME"
  GOOGLE_CLIENT_SECRET: "REPLACE_ME"
  GOOGLE_REFRESH_TOKEN: "REPLACE_ME"
  SLACK_WEBHOOK_URL: "REPLACE_ME"
  JIRA_EMAIL: "REPLACE_ME"
  JIRA_API_TOKEN: "REPLACE_ME"
```

- [ ] **Step 2: Add Jira env vars to `manifests/04-cronjob.yaml`**

Add after the `SLACK_WEBHOOK_URL` env block (after line 51), before the `OPENAI_BASE_URL` entry:

```yaml
                - name: JIRA_EMAIL
                  valueFrom:
                    secretKeyRef:
                      name: invention-radar-secrets
                      key: JIRA_EMAIL
                - name: JIRA_API_TOKEN
                  valueFrom:
                    secretKeyRef:
                      name: invention-radar-secrets
                      key: JIRA_API_TOKEN
```

- [ ] **Step 3: Verify YAML is valid**

Run: `python3 -c "import yaml; yaml.safe_load(open('manifests/04-cronjob.yaml')); yaml.safe_load(open('manifests/05-secrets.yaml')); print('YAML valid')"`
Expected: `YAML valid`

- [ ] **Step 4: Commit**

```bash
git add manifests/04-cronjob.yaml manifests/05-secrets.yaml
git commit -m "feat: add Jira credentials to OpenShift manifests"
```
