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
