import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import anthropic
import config
from lib.radar_store import generate_idea_id


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(base_url=config.LLM_BASE_URL, api_key=config.LLM_API_KEY)


def _chat(prompt: str, system: str = "") -> str:
    kwargs = {
        "model": config.LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.9,
        "max_tokens": 16384,
    }
    if system:
        kwargs["system"] = system
    resp = _client().messages.create(**kwargs)
    return resp.content[0].text


def _parse_json_response(text: str) -> dict:
    md_match = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
    if md_match:
        parsed = json.loads(md_match.group(1))
        if isinstance(parsed, list):
            return {"ideas": parsed}
        return parsed
    brace = text.find("{")
    bracket = text.find("[")
    if brace == -1 and bracket == -1:
        raise ValueError(f"No JSON found in response: {text[:200]}")
    start = min(x for x in [brace, bracket] if x >= 0)
    candidate = text[start:]
    parsed = json.loads(candidate)
    if isinstance(parsed, list):
        return {"ideas": parsed}
    return parsed


def run_pipeline(transcripts: list[dict], existing_ideas: list[dict]) -> tuple[list[dict], dict]:
    signals = extract_signals(transcripts)
    print(f"  Extracted signals: {len(signals.get('friction', []))} friction, {len(signals.get('gap', []))} gap, {len(signals.get('collision', []))} collision")
    persona_ideas = parallel_ideation(signals)
    print(f"  Persona ideation: {len(persona_ideas)} raw ideas from {len(config.PERSONAS)} personas")
    cross_ideas = cross_meeting_synthesis(signals, transcripts)
    print(f"  Cross-meeting synthesis: {len(cross_ideas)} ideas")
    all_raw = persona_ideas + cross_ideas
    print(f"  Total raw ideas before scoring: {len(all_raw)}")
    scored = consolidate_and_score(all_raw, existing_ideas)
    print(f"  After scoring/dedup: {len(scored)} ideas")
    scored = sorted(scored, key=lambda i: i.get("overall_score", 0), reverse=True)[:config.MAX_IDEAS_PER_RUN]
    print(f"  After top-{config.MAX_IDEAS_PER_RUN} cap: {len(scored)} ideas")
    top_work = [i for i in scored if i.get("category") == "work" and i.get("overall_score", 0) >= 6]
    startup_ideas = startup_lens(top_work)
    print(f"  Startup lens: {len(startup_ideas)} ideas from {len(top_work)} top work ideas")
    return scored + startup_ideas, signals


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
        except (json.JSONDecodeError, ValueError) as e:
            print(f"    JSON parse error for persona '{persona['name']}': {e}")
            print(f"    Response preview: {response[:200]}")
            return []

    all_ideas = []
    with ThreadPoolExecutor(max_workers=config.MAX_PARALLEL_PERSONAS) as pool:
        results = list(pool.map(run_persona, config.PERSONAS))
    for i, ideas in enumerate(results):
        print(f"    Persona '{config.PERSONAS[i]['name']}': {len(ideas)} ideas")
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
    except (json.JSONDecodeError, ValueError) as e:
        print(f"    Cross-meeting JSON parse error: {e}")
        print(f"    Response preview: {response[:200]}")
        return []


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
    response = _chat(prompt, system)
    try:
        result = _parse_json_response(response)
        ideas = result.get("ideas", [])
    except (json.JSONDecodeError, ValueError) as e:
        print(f"    Scoring JSON parse error: {e}")
        print(f"    Response preview: {response[:200]}")
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
            core = {k: v for k, v in scores.items() if k in config.SCORING_CRITERIA}
            vals = [v for v in core.values() if isinstance(v, (int, float))]
            base = sum(vals) / len(vals) if vals else 0
            impact = idea.get("team_impact", "none")
            bonus = {"none": 0, "some": 0.5, "high": 1.0}.get(impact, 0)
            idea["overall_score"] = round(min(base + bonus, 10), 1)
    return [i for i in ideas if i.get("overall_score", 0) >= config.MIN_SCORE]


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
            idea["id"] = generate_idea_id(f"startup-{idea.get('title', 'startup')}", today)
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

Also write a per-meeting summary — a one-sentence TL;DR of each meeting's theme, NOT restating individual signals. The summary should capture the overall flavor (e.g. "team frustrated with manual triage workflows and unclear ownership") while the categorized signals above carry the specific evidence. Do not duplicate signal content in the summary.

Return JSON:
{{"friction": [{{"text": "...", "meeting": "...", "speaker": "..."}}], "gap": [...], "collision": [...], "intensity": [...], "pattern": [...], "meeting_summaries": [{{"meeting": "...", "date": "...", "summary": "..."}}]}}"""


def _build_persona_prompt(signals: dict, persona: dict) -> str:
    signals_text = json.dumps(signals, indent=2)
    persona_name = persona.get("name", "unknown")
    return f"""You are a {persona_name}. Based on these signals extracted from engineering meetings, generate ideas.

Be brief. Every sentence must earn its place. No AI jargon, no filler phrases like 'leveraging', 'ecosystem', 'paradigm', 'infrastructure layer', 'holistic', 'seamless'.

SIGNALS:
{signals_text}

Apply these lateral thinking techniques to EACH signal:
- Inversion: Flip the problem. What if we caused it on purpose? What does that reveal?
- Deletion: What if nobody did this at all? What would break? What wouldn't?
- Transplant: Steal a solution from your domain and adapt it.
- Audience Shift: Who else has this exact problem outside this team?
- Emotional Forensics: Ignore what they said. Listen to HOW they said it.

For each idea, provide:
- title: Plain English, 3-6 words. Say what it does, not a metaphor. Bad: "Ownership Tombstone Tracker". Good: "Find Unowned Action Items".
- description: 2-3 short sentences. No jargon, no filler, no buzzwords.
- tags: Relevant team areas (agent-ops, security, platform, networking, developer-experience, automation)
- starting_point: 1-2 sentences. A concrete weekend build — name the tools, skip the explanation.
- ambitious_version: 1-2 sentences. Where this goes long-term if it works.
- evidence: Which signal inspired this, from which meeting, attributed to whom. Quote the key phrase, not the full sentence.

IMPORTANT: If your first instinct is a dashboard or a Slack bot, discard it and think harder.

Generate at most 3 ideas. Quality over quantity — only your strongest.

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

Be brief. No jargon, no filler. For each cross-meeting connection, provide:
- title: Plain English, 3-6 words. Say what it does, not a metaphor.
- description (2-3 sentences, no jargon), tags, starting_point (1-2 sentences), ambitious_version (1-2 sentences)
- evidence: MUST reference at least 2 different meetings — quote the key phrase, not the full sentence

Generate at most 3 cross-meeting ideas. Quality over quantity.

Return JSON: {{"ideas": [...]}}"""


def _build_scoring_prompt(raw_ideas: list[dict], existing_ideas: list[dict], jira_coverage: dict | None = None) -> str:
    ideas_text = json.dumps(raw_ideas, indent=2)
    existing_summaries = [
        {"title": i.get("title", ""), "description": i.get("description", "")[:100]}
        for i in existing_ideas[:50]
    ]

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

    return f"""Score and deduplicate these ideas.

RAW IDEAS:
{ideas_text}

ALREADY EXISTING IDEAS (avoid duplicating or restating these — check both titles AND descriptions for overlap):
{json.dumps(existing_summaries)}
{jira_section}

Score each idea on these criteria (1-10):
- frustration_intensity: How painful is this problem based on speaker language?
- nobody_owns_this: Is anyone already working on it? (10 = total vacuum){" Use the JIRA COVERAGE data above as ground truth." if jira_coverage else ""}
- cross_meeting: Does this link signals from multiple meetings?
- repeat_frequency: Has this come up before?
- demo_ability: Could you show this working in 5 minutes?

Also assess team_impact — would the Agent Ops team actually adopt and use this day-to-day?
Answer "none", "some", or "high". This is a lightweight bonus, not a core criterion.

Rules:
- Discard any idea that duplicates an existing idea
- Discard any idea scoring below 5 overall
- Merge similar ideas into a stronger combined version
- Titles must be plain English, 3-6 words — say what it does. No metaphors, no AI jargon, no ominous-sounding names.
- Keep merged descriptions to 2-3 sentences, starting_point to 1-2 sentences, ambitious_version to 1-2 sentences. Cut jargon and filler ruthlessly.
- Be harsh — only strong ideas survive

Return JSON with fully formed ideas:
{{"ideas": [{{"id": "", "title": "...", "description": "...", "tags": [...], "starting_point": "...", "ambitious_version": "...", "evidence": [...], "scores": {{"frustration_intensity": N, "nobody_owns_this": N, "cross_meeting": N, "repeat_frequency": N, "demo_ability": N}}, "team_impact": "none|some|high", "category": "work"}}]}}"""


def _build_startup_prompt(ideas: list[dict]) -> str:
    ideas_text = json.dumps(
        [{"title": i["title"], "description": i.get("description", ""), "overall_score": i.get("overall_score", 0)} for i in ideas],
        indent=2,
    )
    return f"""Re-examine these work ideas through a startup/business lens.

IDEAS:
{ideas_text}

For each idea that has business potential, answer in 1 sentence each:
- customer: Who buys this outside Red Hat? (job title + company size)
- current_spend: What do they pay today for a worse version?
- mvp: What's the minimum product you could charge for?
- market_direction: Is this problem growing or shrinking, and why?

Keep starting_point to 1-2 sentences and ambitious_version to 1-2 sentences.
Only include ideas with genuine business potential. Don't force it. No jargon or filler. Titles must be plain English, 3-6 words.

Return JSON:
{{"ideas": [{{"title": "...", "description": "...", "tags": [...], "starting_point": "...", "ambitious_version": "...", "evidence": [...], "scores": {{}}, "startup_analysis": {{"customer": "...", "current_spend": "...", "mvp": "...", "market_direction": "..."}}}}]}}"""
