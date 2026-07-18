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
