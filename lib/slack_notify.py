import json
import urllib.request
import config


def build_slack_message(idea: dict) -> dict:
    score = idea.get("overall_score", "?")
    title = idea.get("title", "Untitled")
    desc = idea.get("description", "")
    category = idea.get("category", "work")
    cross_meeting = idea.get("scores", {}).get("cross_meeting", 0)

    emoji = "🚀" if category == "startup" else "💡"
    cross_flag = " ⚡ Cross-meeting connection!" if cross_meeting >= 7 else ""
    category_label = "Startup Radar" if category == "startup" else "Work Idea"

    doc_url = f"https://docs.google.com/document/d/{config.RADAR_DOC_ID}/edit" if config.RADAR_DOC_ID else ""

    return {
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"{emoji} Meeting Miner: {title}"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Score: {score}/10* | {category_label}{cross_flag}\n\n{desc}"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"<{doc_url}|View in Radar Doc>"},
            },
        ],
    }


def notify_high_scores(ideas: list[dict]) -> int:
    if not config.SLACK_WEBHOOK_URL:
        return 0

    count = 0
    for idea in ideas:
        if idea.get("overall_score", 0) >= config.SCORE_THRESHOLD:
            msg = build_slack_message(idea)
            data = json.dumps(msg).encode()
            req = urllib.request.Request(
                config.SLACK_WEBHOOK_URL,
                data=data,
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            try:
                with urllib.request.urlopen(req, timeout=10):
                    count += 1
            except Exception as e:
                print(f"Slack notification failed for '{idea.get('title')}': {e}")
    return count
