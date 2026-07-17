def render_idea_text(idea: dict) -> str:
    scores = idea.get("scores", {})
    score_line = " | ".join(f"{k}: {v}" for k, v in scores.items())
    overall = idea.get("overall_score", "?")

    evidence_lines = []
    for e in idea.get("evidence", []):
        speaker = e.get("speaker", "Unknown")
        meeting = e.get("meeting", "Unknown meeting")
        quote = e.get("quote", "")
        link = e.get("doc_link", "")
        evidence_lines.append(f'    - {speaker} ({meeting}): "{quote}" [source]({link})')
    evidence_text = "\n".join(evidence_lines) if evidence_lines else "    (no evidence recorded)"

    tags = ", ".join(idea.get("tags", []))

    return f"""## {idea['title']}  (Score: {overall}/10)
{idea.get('description', '')}
Tags: {tags}

**Starting Point:** {idea.get('starting_point', 'TBD')}

**Ambitious Version:** {idea.get('ambitious_version', 'TBD')}

Scores: {score_line}

Evidence:
{evidence_text}

---
"""


def render_weekly_header(week_label: str, stats: dict) -> str:
    return f"""# {week_label}
Meetings processed: {stats.get('meetings_processed', 0)} | Ideas generated: {stats.get('ideas_generated', 0)} | Cross-meeting connections: {stats.get('cross_connections', 0)}

"""


def render_favourites_text(starred: list[dict]) -> str:
    if not starred:
        return "# Favourites\n(No favourited ideas yet)\n\n"
    lines = ["# Favourites\n"]
    for idea in starred:
        status = idea.get("status") or "starred"
        score = idea.get("overall_score", "?")
        lines.append(f"- **{idea['title']}** (Score: {score}) [{status}]")
    lines.append("\n")
    return "\n".join(lines)


def build_full_update(radar_data: dict, new_ideas: list[dict]) -> list[dict]:
    from lib.radar_store import get_starred

    starred = get_starred(radar_data)
    fav_text = render_favourites_text(starred)

    work_ideas = [i for i in new_ideas if i.get("category") != "startup"]
    startup_ideas = [i for i in new_ideas if i.get("category") == "startup"]

    stats = {
        "meetings_processed": len({e.get("meeting") for i in new_ideas for e in i.get("evidence", [])}),
        "ideas_generated": len(new_ideas),
        "cross_connections": sum(1 for i in new_ideas if i.get("scores", {}).get("cross_meeting", 0) >= 7),
    }

    from datetime import datetime, timezone
    week_label = f"Week of {datetime.now(timezone.utc).strftime('%b %d, %Y')}"

    sections = []
    sections.append(fav_text)
    sections.append(render_weekly_header(week_label, stats))

    if work_ideas:
        sections.append("## Work Ideas\n\n")
        for idea in sorted(work_ideas, key=lambda i: i.get("overall_score", 0), reverse=True):
            sections.append(render_idea_text(idea))

    if startup_ideas:
        sections.append("## Startup Radar\n\n")
        for idea in sorted(startup_ideas, key=lambda i: i.get("overall_score", 0), reverse=True):
            text = render_idea_text(idea)
            analysis = idea.get("startup_analysis", {})
            if analysis:
                text += f"\n**Customer:** {analysis.get('customer', '?')}\n"
                text += f"**Current Spend:** {analysis.get('current_spend', '?')}\n"
                text += f"**MVP:** {analysis.get('mvp', '?')}\n"
                text += f"**Market Direction:** {analysis.get('market_direction', '?')}\n\n"
            sections.append(text)

    full_text = "\n".join(sections)

    requests = [
        {"insertText": {"location": {"index": 1}, "text": full_text}},
    ]
    return requests
