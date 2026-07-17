import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from openai import OpenAI
import config
from lib.radar_store import generate_idea_id


def _client() -> OpenAI:
    return OpenAI(base_url=config.LLM_BASE_URL, api_key=config.LLM_API_KEY)


def _chat(prompt: str, system: str = "") -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = _client().chat.completions.create(
        model=config.LLM_MODEL,
        messages=messages,
        temperature=0.9,
        max_tokens=4096,
    )
    return resp.choices[0].message.content


def _parse_json_response(text: str) -> dict:
    md_match = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
    if md_match:
        return json.loads(md_match.group(1))
    brace = text.find("{")
    bracket = text.find("[")
    if brace == -1 and bracket == -1:
        raise ValueError(f"No JSON found in response: {text[:200]}")
    start = min(x for x in [brace, bracket] if x >= 0)
    candidate = text[start:]
    return json.loads(candidate)


def run_pipeline(transcripts: list[dict], existing_ideas: list[dict]) -> list[dict]:
    signals = extract_signals(transcripts)
    persona_ideas = parallel_ideation(signals)
    cross_ideas = cross_meeting_synthesis(signals, transcripts)
    all_raw = persona_ideas + cross_ideas
    scored = consolidate_and_score(all_raw, existing_ideas)
    top_work = [i for i in scored if i.get("category") == "work" and i.get("overall_score", 0) >= 6]
    startup_ideas = startup_lens(top_work)
    return scored + startup_ideas


def extract_signals(transcripts: list[dict]) -> dict:
    prompt = _build_extraction_prompt(transcripts)
    system = "You are a signal extraction engine. Output valid JSON only."
    response = _chat(prompt, system)
    return _parse_json_response(response)


def parallel_ideation(signals: dict) -> list[dict]:
    def run_persona(persona):
        prompt = _build_persona_prompt(signals, persona)
        system = persona["prompt"] + " Output valid JSON only."
        response = _chat(prompt, system)
        try:
            result = _parse_json_response(response)
            return result.get("ideas", [])
        except (json.JSONDecodeError, ValueError):
            return []

    all_ideas = []
    with ThreadPoolExecutor(max_workers=config.MAX_PARALLEL_PERSONAS) as pool:
        results = list(pool.map(run_persona, config.PERSONAS))
    for ideas in results:
        all_ideas.extend(ideas)
    return all_ideas


def cross_meeting_synthesis(signals: dict, transcripts: list[dict]) -> list[dict]:
    if len(transcripts) < 2:
        return []
    prompt = _build_cross_meeting_prompt(signals, transcripts)
    system = "You find connections across different meetings that nobody else sees. Output valid JSON only."
    response = _chat(prompt, system)
    try:
        result = _parse_json_response(response)
        return result.get("ideas", [])
    except (json.JSONDecodeError, ValueError):
        return []


def consolidate_and_score(raw_ideas: list[dict], existing_ideas: list[dict]) -> list[dict]:
    prompt = _build_scoring_prompt(raw_ideas, existing_ideas)
    system = "You are a critical evaluator. Score harshly. Discard weak ideas. Output valid JSON only."
    response = _chat(prompt, system)
    try:
        result = _parse_json_response(response)
        ideas = result.get("ideas", [])
    except (json.JSONDecodeError, ValueError):
        return []

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for idea in ideas:
        if "id" not in idea or not idea["id"]:
            idea["id"] = generate_idea_id(idea.get("title", "untitled"), today)
        idea.setdefault("created", today)
        idea.setdefault("category", "work")
        idea.setdefault("status", None)
        idea.setdefault("starred", False)
        idea.setdefault("related_ideas", [])
        scores = idea.get("scores", {})
        if scores:
            vals = [v for v in scores.values() if isinstance(v, (int, float))]
            idea["overall_score"] = round(sum(vals) / len(vals), 1) if vals else 0
    return ideas


def startup_lens(top_ideas: list[dict]) -> list[dict]:
    if not top_ideas:
        return []
    prompt = _build_startup_prompt(top_ideas)
    system = "You think like a startup founder evaluating market opportunities. Output valid JSON only."
    response = _chat(prompt, system)
    try:
        result = _parse_json_response(response)
        ideas = result.get("ideas", [])
    except (json.JSONDecodeError, ValueError):
        return []

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for idea in ideas:
        idea["category"] = "startup"
        if "id" not in idea or not idea["id"]:
            idea["id"] = generate_idea_id(idea.get("title", "startup"), today)
        idea.setdefault("created", today)
        idea.setdefault("status", None)
        idea.setdefault("starred", False)
        idea.setdefault("related_ideas", [])
    return ideas


def _build_extraction_prompt(transcripts: list[dict]) -> str:
    meeting_texts = []
    for t in transcripts:
        meeting_texts.append(f"=== {t['meeting_name']} ({t.get('date', 'unknown date')}) ===\n{t['text']}\n")
    all_text = "\n".join(meeting_texts)
    return f"""Analyze these meeting transcripts and extract signals.

{all_text}

Extract signals into these categories:
- FRICTION: Manual, repetitive, error-prone processes. Language markers: "every time," "I have to," "it takes hours," "painful," "broken."
- GAP: Problems nobody owns. Markers: "someone should," "we don't have," "nobody is," "I wish."
- COLLISION: Ideas/tools in one meeting that could solve problems in another.
- INTENSITY: Emotional language indicating real suffering, not casual complaints.
- PATTERN: Same problem appearing across 2+ meetings.

Return JSON:
{{"friction": [{{"text": "...", "meeting": "...", "speaker": "..."}}], "gap": [...], "collision": [...], "intensity": [...], "pattern": [...]}}"""


def _build_persona_prompt(signals: dict, persona: dict) -> str:
    signals_text = json.dumps(signals, indent=2)
    persona_name = persona.get("name", "unknown")
    return f"""You are a {persona_name}. Based on these signals extracted from engineering meetings, generate invention ideas.

SIGNALS:
{signals_text}

Apply these lateral thinking techniques to EACH signal:
- Inversion: Flip the problem. What if we caused it on purpose? What does that reveal?
- Deletion: What if nobody did this at all? What would break? What wouldn't?
- Transplant: Steal a solution from your domain and adapt it.
- Audience Shift: Who else has this exact problem outside this team?
- Emotional Forensics: Ignore what they said. Listen to HOW they said it.

For each idea, provide:
- title: A sharp, memorable name (not generic)
- description: 2-3 sentences on what it does and why it matters
- tags: Relevant team areas (agent-ops, security, platform, networking, developer-experience, automation)
- starting_point: What you could build in a weekend as an MVP. Name specific tools and APIs.
- ambitious_version: The long-term architectural vision. Think 6th-order effects — what happens as this scales through the entire organization?
- evidence: Which signal inspired this, from which meeting, attributed to whom

IMPORTANT: If your first instinct is a dashboard or a Slack bot, discard it and think harder.

Return JSON: {{"ideas": [...]}}"""


def _build_cross_meeting_prompt(signals: dict, transcripts: list[dict]) -> str:
    signals_text = json.dumps(signals, indent=2)
    meetings_summary = "\n".join(
        f"- {t['meeting_name']}: {t['text'][:300]}..." for t in transcripts
    )
    return f"""You specialize in finding connections ACROSS different meetings that nobody else can see.

SIGNALS from all meetings:
{signals_text}

MEETINGS:
{meetings_summary}

Look for:
1. Problem in Meeting A + solution discussed in Meeting B
2. Same theme appearing in unrelated teams (they don't know about each other)
3. Contradictions: one team's solution is another team's problem

For each cross-meeting connection, provide:
- title, description, tags, starting_point, ambitious_version
- evidence: MUST reference at least 2 different meetings with specific quotes

Return JSON: {{"ideas": [...]}}"""


def _build_scoring_prompt(raw_ideas: list[dict], existing_ideas: list[dict]) -> str:
    ideas_text = json.dumps(raw_ideas, indent=2)
    existing_titles = [i.get("title", "") for i in existing_ideas[:50]]
    return f"""Score and deduplicate these invention ideas.

RAW IDEAS:
{ideas_text}

ALREADY EXISTING IDEAS (avoid duplicating these):
{json.dumps(existing_titles)}

Score each idea on these criteria (1-10):
- frustration_intensity: How painful is this problem based on speaker language?
- nobody_owns_this: Is anyone already working on it? (10 = total vacuum)
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


def _build_startup_prompt(ideas: list[dict]) -> str:
    ideas_text = json.dumps(
        [{"title": i["title"], "description": i.get("description", ""), "overall_score": i.get("overall_score", 0)} for i in ideas],
        indent=2,
    )
    return f"""Re-examine these work ideas through a startup/business lens.

IDEAS:
{ideas_text}

For each idea that has business potential, answer:
- Who is the customer outside Red Hat? Be specific (job title, company size).
- What do they pay today for a worse version of this? Name actual products/services.
- What's the minimum viable product you could charge for?
- Is this problem growing or shrinking? Why?
- Market signal: any trends, competitors, or regulatory changes?

Only include ideas with genuine business potential. Don't force it.

Return JSON:
{{"ideas": [{{"title": "...", "description": "...", "tags": [...], "starting_point": "Weekend MVP: ...", "ambitious_version": "Full product: ...", "evidence": [...], "scores": {{}}, "startup_analysis": {{"customer": "...", "current_spend": "...", "mvp": "...", "market_direction": "..."}}}}]}}"""
