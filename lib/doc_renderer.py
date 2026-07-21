from datetime import datetime, timezone, timedelta


BLUE = {"red": 0.15, "green": 0.4, "blue": 0.85}
GRAY = {"red": 0.5, "green": 0.5, "blue": 0.5}
DARK_GRAY = {"red": 0.3, "green": 0.3, "blue": 0.3}
GREEN = {"red": 0.15, "green": 0.55, "blue": 0.25}
LIGHT_GRAY = {"red": 0.7, "green": 0.7, "blue": 0.7}


class DocBuilder:
    def __init__(self, start_index=1):
        self.index = start_index
        self.requests = []

    def _insert(self, text):
        self.requests.append({"insertText": {"location": {"index": self.index}, "text": text}})
        start = self.index
        self.index += len(text)
        return start

    def _style_paragraph(self, start, end, heading_level):
        style_map = {1: "HEADING_1", 2: "HEADING_2", 3: "HEADING_3"}
        named = style_map.get(heading_level, "NORMAL_TEXT")
        self.requests.append({
            "updateParagraphStyle": {
                "range": {"startIndex": start, "endIndex": end},
                "paragraphStyle": {"namedStyleType": named},
                "fields": "namedStyleType",
            }
        })

    def _style_text(self, start, end, bold=None, italic=None, color=None, font_size=None):
        style = {}
        fields = []
        if bold is not None:
            style["bold"] = bold
            fields.append("bold")
        if italic is not None:
            style["italic"] = italic
            fields.append("italic")
        if color is not None:
            style["foregroundColor"] = {"color": {"rgbColor": color}}
            fields.append("foregroundColor")
        if font_size is not None:
            style["fontSize"] = {"magnitude": font_size, "unit": "PT"}
            fields.append("fontSize")
        if not fields:
            return
        self.requests.append({
            "updateTextStyle": {
                "range": {"startIndex": start, "endIndex": end},
                "textStyle": style,
                "fields": ",".join(fields),
            }
        })

    def _make_bullets(self, start, end):
        self.requests.append({
            "createParagraphBullets": {
                "range": {"startIndex": start, "endIndex": end},
                "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE",
            }
        })

    def add_heading(self, text, level=1):
        line = text + "\n"
        start = self._insert(line)
        self._style_paragraph(start, self.index, level)

    def add_text(self, text):
        if not text.endswith("\n"):
            text += "\n"
        self._insert(text)

    def add_bold_text(self, text):
        if not text.endswith("\n"):
            text += "\n"
        start = self._insert(text)
        self._style_text(start, self.index - 1, bold=True)

    def add_colored_text(self, text, color):
        if not text.endswith("\n"):
            text += "\n"
        start = self._insert(text)
        self._style_text(start, self.index - 1, color=color)

    def add_bold_colored_text(self, text, color):
        if not text.endswith("\n"):
            text += "\n"
        start = self._insert(text)
        self._style_text(start, self.index - 1, bold=True, color=color)

    def add_gray_text(self, text):
        self.add_colored_text(text, GRAY)

    def add_bullet(self, text):
        if not text.endswith("\n"):
            text += "\n"
        start = self._insert(text)
        self._make_bullets(start, self.index)

    def add_bold_bullet(self, text):
        if not text.endswith("\n"):
            text += "\n"
        start = self._insert(text)
        self._make_bullets(start, self.index)
        self._style_text(start, self.index - 1, bold=True)

    def add_inline(self, segments):
        """Add a line with mixed formatting: [("text", {style}), ...]
        Style keys: bold, italic, color. Last segment gets \\n appended."""
        for i, (text, style) in enumerate(segments):
            if i == len(segments) - 1 and not text.endswith("\n"):
                text += "\n"
            start = self._insert(text)
            self._style_text(
                start, start + len(text.rstrip("\n")),
                bold=style.get("bold"),
                italic=style.get("italic"),
                color=style.get("color"),
            )

    def add_divider(self):
        line = "───────────────────────────────────────\n"
        start = self._insert(line)
        self._style_text(start, self.index - 1, color=LIGHT_GRAY)

    def add_blank_line(self):
        self._insert("\n")


def _week_range() -> str:
    today = datetime.now(timezone.utc)
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    if monday.month == sunday.month:
        return f"{monday.strftime('%b %d')} – {sunday.strftime('%d, %Y')}"
    return f"{monday.strftime('%b %d')} – {sunday.strftime('%b %d, %Y')}"


def _render_summary_table(doc: DocBuilder, ideas: list[dict]) -> None:
    if not ideas:
        return
    doc.add_heading("Top Ideas", level=1)
    ranked = sorted(ideas, key=lambda i: i.get("overall_score", 0), reverse=True)
    for rank, idea in enumerate(ranked[:10], 1):
        title = idea.get("title", "Untitled")
        score = idea.get("overall_score", "?")
        tags = idea.get("tags") or []
        tag_str = f"  ({', '.join(tags[:3])})" if tags else ""
        doc.add_inline([
            (f"{rank}. {title} — ", {}),
            (f"{score}/10", {"bold": True, "color": _score_color(score)}),
            (tag_str, {"color": GRAY}),
        ])
    bonus_count = sum(1 for i in ideas if i.get("team_impact") in ("some", "high"))
    if bonus_count:
        doc.add_gray_text(f"{bonus_count} idea{'s' if bonus_count != 1 else ''} with team impact bonus")
    doc.add_blank_line()


def _render_favourites(doc: DocBuilder, starred: list[dict]) -> None:
    doc.add_heading("Favourites", level=1)
    if not starred:
        doc.add_gray_text("(No favourited ideas yet)")
        doc.add_blank_line()
        return
    for idea in starred:
        status = idea.get("status") or "starred"
        score = idea.get("overall_score", "?")
        doc.add_bold_bullet(f"{idea['title']} (Score: {score}) [{status}]")
    doc.add_blank_line()


def _render_weekly_header(doc: DocBuilder, week_range: str, stats: dict) -> None:
    doc.add_heading(week_range, level=1)
    meetings = stats.get("meetings_processed", 0)
    ideas = stats.get("ideas_generated", 0)
    cross = stats.get("cross_connections", 0)
    doc.add_gray_text(f"{meetings} meetings · {ideas} ideas · {cross} cross-connections")
    doc.add_blank_line()


def _render_signals(doc: DocBuilder, signals: dict) -> None:
    summaries = signals.get("meeting_summaries", [])
    has_raw = any(signals.get(k) for k in ("friction", "gap", "collision", "intensity", "pattern"))
    if not summaries and not has_raw:
        return

    doc.add_heading("Meeting Signals", level=2)

    signal_by_meeting = {}
    seen_texts = set()
    for category in ("friction", "gap", "collision"):
        for s in signals.get(category, []):
            text = s.get("text", "").strip()
            if not text or text in seen_texts:
                continue
            seen_texts.add(text)
            meeting = s.get("meeting", "Unknown")
            signal_by_meeting.setdefault(meeting, []).append((category.upper(), s))

    for summary in summaries:
        meeting = summary.get("meeting", "Unknown")
        date = summary.get("date", "")
        date_label = f" ({date})" if date else ""
        doc.add_inline([
            (f"{meeting}{date_label}", {"bold": True}),
            (f" — {summary.get('summary', '')}", {"italic": True, "color": DARK_GRAY}),
        ])
        for cat_label, s in signal_by_meeting.get(meeting, []):
            speaker = s.get("speaker", "")
            speaker_part = f" — {speaker}" if speaker else ""
            doc.add_bullet(f"[{cat_label}] \"{s.get('text', '')}\"{speaker_part}")

    for meeting, items in signal_by_meeting.items():
        if any(meeting == s.get("meeting") for s in summaries):
            continue
        doc.add_bold_text(f"{meeting}:")
        for cat_label, s in items:
            speaker = s.get("speaker", "")
            speaker_part = f" — {speaker}" if speaker else ""
            doc.add_bullet(f"[{cat_label}] \"{s.get('text', '')}\"{speaker_part}")

    doc.add_blank_line()


def _team_impact_bonus(idea: dict) -> float:
    impact = idea.get("team_impact", "none")
    return {"none": 0, "some": 0.5, "high": 1.0}.get(impact, 0)


def _score_color(score):
    if isinstance(score, (int, float)):
        if score >= 7:
            return BLUE
        if score >= 5:
            return {"red": 0.85, "green": 0.55, "blue": 0.1}
    return GRAY


def _render_idea(doc: DocBuilder, idea: dict) -> None:
    title = idea.get("title", "Untitled")
    if idea.get("starred"):
        title = f"⭐ {title}"
    overall = idea.get("overall_score", "?")

    doc.add_heading(f"{title}", level=3)

    bonus = _team_impact_bonus(idea)
    score_line = f"Score: {overall}/10"
    if bonus > 0:
        score_line += f"  (+{bonus} team impact)"
    doc.add_bold_colored_text(score_line, _score_color(overall))

    scores = idea.get("scores") or {}
    if scores:
        parts = " · ".join(f"{k.replace('_', ' ')}: {v}" for k, v in scores.items())
        doc.add_gray_text(parts)

    desc = idea.get("description", "")
    if desc:
        doc.add_text(desc)

    tags = idea.get("tags") or []
    if tags:
        doc.add_gray_text(f"Tags: {', '.join(tags)}")

    doc.add_blank_line()

    sp = idea.get("starting_point", "")
    if sp:
        doc.add_inline([("Starting Point: ", {"bold": True, "color": GREEN}), (sp, {})])

    av = idea.get("ambitious_version", "")
    if av:
        doc.add_inline([("Ambitious Version: ", {"bold": True, "color": BLUE}), (av, {})])

    evidence = idea.get("evidence") or []
    if evidence:
        max_shown = 2
        doc.add_bold_text("Evidence:")
        for e in evidence[:max_shown]:
            if isinstance(e, str):
                doc.add_bullet(e)
            else:
                speaker = e.get("speaker", "Unknown")
                meeting = e.get("meeting", "Unknown")
                quote = e.get("quote", "")
                doc.add_bullet(f"\"{quote}\" — {speaker} ({meeting})")
        remaining = len(evidence) - max_shown
        if remaining > 0:
            doc.add_gray_text(f"(+{remaining} more)")

    doc.add_blank_line()


def _render_startup_compact(doc: DocBuilder, idea: dict) -> None:
    title = idea.get("title", "Untitled")
    overall = idea.get("overall_score", "?")
    doc.add_inline([
        (f"{title} — ", {"bold": True}),
        (f"{overall}/10", {"bold": True, "color": _score_color(overall)}),
    ])
    desc = idea.get("description", "")
    if desc:
        doc.add_gray_text(desc)
    analysis = idea.get("startup_analysis") or {}
    if analysis:
        doc.add_inline([("Customer: ", {"bold": True}), (analysis.get("customer", "?"), {})])
        doc.add_inline([("Current Spend: ", {"bold": True}), (analysis.get("current_spend", "?"), {})])
        doc.add_inline([("MVP: ", {"bold": True}), (analysis.get("mvp", "?"), {})])
        doc.add_inline([("Market: ", {"bold": True}), (analysis.get("market_direction", "?"), {})])
    doc.add_blank_line()


def build_full_update(radar_data: dict, new_ideas: list[dict], signals: dict | None = None, meetings_count: int = 0) -> list[dict]:
    from lib.radar_store import get_starred

    doc = DocBuilder()

    starred = get_starred(radar_data)
    _render_favourites(doc, starred)

    _render_summary_table(doc, new_ideas)
    doc.add_divider()

    work_ideas = [i for i in new_ideas if i.get("category") != "startup"]
    startup_ideas = [i for i in new_ideas if i.get("category") == "startup"]

    stats = {
        "meetings_processed": meetings_count,
        "ideas_generated": len(new_ideas),
        "cross_connections": sum(1 for i in new_ideas if (i.get("scores") or {}).get("cross_meeting", 0) >= 7),
    }

    _render_weekly_header(doc, _week_range(), stats)

    if signals:
        _render_signals(doc, signals)
        doc.add_divider()

    if work_ideas:
        doc.add_heading("Work Ideas", level=2)
        for idea in sorted(work_ideas, key=lambda i: i.get("overall_score", 0), reverse=True):
            _render_idea(doc, idea)

    if startup_ideas:
        doc.add_divider()
        doc.add_heading("Startup Radar", level=2)
        for idea in sorted(startup_ideas, key=lambda i: i.get("overall_score", 0), reverse=True):
            _render_startup_compact(doc, idea)

    return doc.requests
