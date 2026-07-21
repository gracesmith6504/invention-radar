import json
import html as html_mod


def _build_signals_html(radar_data: dict) -> str:
    signals = radar_data.get("meeting_signals", [])
    if not signals:
        return ""
    cards = []
    for s in signals:
        meeting = html_mod.escape(s.get("meeting", "Unknown"))
        date = html_mod.escape(s.get("date", ""))
        summary = html_mod.escape(s.get("summary", ""))
        date_label = f' <span class="signal-date">({date})</span>' if date else ""
        cards.append(
            f'<div class="signal-card">'
            f'<div class="signal-meeting">{meeting}{date_label}</div>'
            f'<div class="signal-summary">{summary}</div>'
            f'</div>'
        )
    return (
        '<div class="signals-panel">'
        '<h2 class="signals-title">Meeting Signals</h2>'
        '<div class="signals-grid">' + "".join(cards) + '</div>'
        '</div>'
    )


def render_dashboard(radar_data: dict, output_path: str) -> None:
    ideas = radar_data.get("ideas", [])
    all_tags = sorted({tag for idea in ideas for tag in (idea.get("tags") or [])})

    ideas_json = json.dumps(ideas)
    signals_html = _build_signals_html(radar_data)

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Meeting Miner</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0a; color: #e0e0e0; padding: 24px; }}
h1 {{ font-size: 28px; margin-bottom: 8px; color: #fff; }}
.subtitle {{ color: #888; margin-bottom: 24px; }}
.filters {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 24px; }}
.filter-btn {{ padding: 6px 14px; border-radius: 20px; border: 1px solid #333; background: #1a1a1a; color: #ccc; cursor: pointer; font-size: 13px; transition: all 0.2s; }}
.filter-btn:hover {{ border-color: #666; }}
.filter-btn.active {{ background: #2563eb; border-color: #2563eb; color: #fff; }}
.search {{ width: 100%; padding: 10px 16px; border-radius: 8px; border: 1px solid #333; background: #1a1a1a; color: #e0e0e0; font-size: 14px; margin-bottom: 24px; }}
.search:focus {{ outline: none; border-color: #2563eb; }}
.ideas {{ display: grid; gap: 16px; }}
.idea {{ background: #141414; border: 1px solid #222; border-radius: 12px; padding: 20px; transition: border-color 0.2s; }}
.idea:hover {{ border-color: #444; }}
.idea-header {{ display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px; }}
.idea-title {{ font-size: 18px; font-weight: 600; color: #fff; }}
.idea-score {{ font-size: 24px; font-weight: 700; color: #2563eb; min-width: 48px; text-align: right; }}
.idea-desc {{ color: #aaa; margin-bottom: 12px; line-height: 1.5; }}
.idea-tags {{ display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 12px; }}
.tag {{ padding: 3px 10px; border-radius: 12px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }}
.tag-work {{ background: #1e3a5f; color: #60a5fa; }}
.tag-startup {{ background: #5f1e3a; color: #fa6090; }}
.tag-default {{ background: #2a2a2a; color: #999; }}
.section {{ margin-bottom: 12px; }}
.section-label {{ font-size: 12px; text-transform: uppercase; color: #666; letter-spacing: 0.5px; margin-bottom: 4px; }}
.section-content {{ color: #ccc; font-size: 14px; line-height: 1.5; }}
.evidence {{ margin-top: 12px; border-top: 1px solid #222; padding-top: 12px; }}
.evidence-item {{ font-size: 13px; color: #888; margin-bottom: 6px; }}
.evidence-item a {{ color: #60a5fa; text-decoration: none; }}
.evidence-item a:hover {{ text-decoration: underline; }}
.scores {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 12px; }}
.score-item {{ font-size: 12px; color: #666; }}
.score-val {{ color: #fff; font-weight: 600; }}
.starred {{ border-color: #f59e0b !important; }}
.star-badge {{ color: #f59e0b; margin-left: 8px; }}
.status-badge {{ font-size: 11px; padding: 2px 8px; border-radius: 10px; background: #1a3a1a; color: #4ade80; margin-left: 8px; }}
.empty {{ text-align: center; padding: 60px; color: #666; }}
.signals-panel {{ margin-bottom: 24px; }}
.signals-title {{ font-size: 20px; color: #fff; margin-bottom: 12px; }}
.signals-grid {{ display: grid; gap: 12px; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); }}
.signal-card {{ background: #141414; border: 1px solid #222; border-radius: 10px; padding: 16px; }}
.signal-card:hover {{ border-color: #444; }}
.signal-meeting {{ font-size: 15px; font-weight: 600; color: #60a5fa; margin-bottom: 6px; }}
.signal-date {{ font-weight: 400; color: #888; }}
.signal-summary {{ font-size: 14px; color: #ccc; line-height: 1.5; }}
.sort-controls {{ display: flex; gap: 8px; margin-bottom: 16px; align-items: center; }}
.sort-controls label {{ color: #888; font-size: 13px; }}
.sort-controls select {{ padding: 4px 8px; border-radius: 6px; border: 1px solid #333; background: #1a1a1a; color: #ccc; font-size: 13px; }}
.team-impact-badge {{ display: block; font-size: 11px; color: #4ade80; font-weight: 400; text-align: right; }}
</style>
</head>
<body>
<h1>Meeting Miner</h1>
<p class="subtitle">{len(ideas)} ideas tracked</p>

{signals_html}

<input type="text" class="search" id="search" placeholder="Search ideas..." oninput="filterIdeas()">

<div class="filters" id="tag-filters">
  <button class="filter-btn active" onclick="toggleFilter(this, 'all')" data-filter="all">All</button>
  <button class="filter-btn" onclick="toggleFilter(this, 'category:work')" data-filter="category:work">Work</button>
  <button class="filter-btn" onclick="toggleFilter(this, 'category:startup')" data-filter="category:startup">Startup</button>
  <button class="filter-btn" onclick="toggleFilter(this, 'starred')" data-filter="starred">Starred</button>
  {"".join(f'  <button class="filter-btn" onclick="toggleFilter(this, \'tag:{t}\')" data-filter="tag:{t}">{html_mod.escape(t)}</button>' for t in all_tags)}
</div>

<div class="sort-controls">
  <label>Sort by:</label>
  <select id="sort" onchange="filterIdeas()">
    <option value="score">Score (high to low)</option>
    <option value="date">Date (newest first)</option>
    <option value="title">Title (A-Z)</option>
  </select>
</div>

<div class="ideas" id="ideas-container"></div>

<script>
const ALL_IDEAS = {ideas_json};
let activeFilter = 'all';

function toggleFilter(btn, filter) {{
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  activeFilter = filter;
  filterIdeas();
}}

function filterIdeas() {{
  const search = document.getElementById('search').value.toLowerCase();
  const sort = document.getElementById('sort').value;
  let filtered = ALL_IDEAS.filter(idea => {{
    if (search && !JSON.stringify(idea).toLowerCase().includes(search)) return false;
    if (activeFilter === 'all') return true;
    if (activeFilter === 'starred') return idea.starred;
    if (activeFilter.startsWith('category:')) return idea.category === activeFilter.split(':')[1];
    if (activeFilter.startsWith('tag:')) return (idea.tags || []).includes(activeFilter.split(':')[1]);
    return true;
  }});
  filtered.sort((a, b) => {{
    if (sort === 'score') return (b.overall_score || 0) - (a.overall_score || 0);
    if (sort === 'date') return (b.created || '').localeCompare(a.created || '');
    if (sort === 'title') return (a.title || '').localeCompare(b.title || '');
    return 0;
  }});
  renderIdeas(filtered);
}}

function renderIdeas(ideas) {{
  const container = document.getElementById('ideas-container');
  if (!ideas.length) {{ container.innerHTML = '<div class="empty">No ideas yet</div>'; return; }}
  container.innerHTML = ideas.map(idea => {{
    const scores = idea.scores || {{}};
    const scoreHtml = Object.entries(scores).filter(([k]) => k !== 'grace_fit').map(([k, v]) =>
      `<div class="score-item">${{k.replace(/_/g, ' ')}}: <span class="score-val">${{v}}</span></div>`
    ).join('');
    const impactMap = {{'some': '+0.5', 'high': '+1.0'}};
    const impactBadge = idea.team_impact && impactMap[idea.team_impact]
      ? `<span class="team-impact-badge">${{impactMap[idea.team_impact]}} team</span>` : '';
    const evidenceItems = (idea.evidence || []).slice(0, 2);
    const evidenceHtml = evidenceItems.map(e =>
      typeof e === 'string'
        ? `<div class="evidence-item">${{e}}</div>`
        : `<div class="evidence-item">${{e.speaker || '?'}} (${{e.meeting || '?'}}): "${{e.quote || ''}}" <a href="${{e.doc_link || '#'}}" target="_blank">[source]</a></div>`
    ).join('') + ((idea.evidence || []).length > 2 ? `<div class="evidence-item" style="color:#555">(+${{(idea.evidence || []).length - 2}} more)</div>` : '');
    const catClass = idea.category === 'startup' ? 'tag-startup' : 'tag-work';
    const tagsHtml = (idea.tags || []).map(t => `<span class="tag tag-default">${{t}}</span>`).join('');
    const starBadge = idea.starred ? '<span class="star-badge">\\u2B50</span>' : '';
    const statusBadge = idea.status ? `<span class="status-badge">${{idea.status}}</span>` : '';
    return `
      <div class="idea ${{idea.starred ? 'starred' : ''}}">
        <div class="idea-header">
          <div class="idea-title">${{idea.title || 'Untitled'}}${{starBadge}}${{statusBadge}}</div>
          <div class="idea-score">${{idea.overall_score || '?'}}${{impactBadge}}</div>
        </div>
        <div class="idea-desc">${{idea.description || ''}}</div>
        <div class="idea-tags"><span class="tag ${{catClass}}">${{idea.category || 'work'}}</span>${{tagsHtml}}</div>
        <div class="section"><div class="section-label">Starting Point</div><div class="section-content">${{idea.starting_point || ''}}</div></div>
        <div class="section"><div class="section-label">Ambitious Version</div><div class="section-content">${{idea.ambitious_version || ''}}</div></div>
        ${{idea.startup_analysis ? `
        <div class="section"><div class="section-label">Customer</div><div class="section-content">${{idea.startup_analysis.customer || ''}}</div></div>
        <div class="section"><div class="section-label">Current Spend</div><div class="section-content">${{idea.startup_analysis.current_spend || ''}}</div></div>
        <div class="section"><div class="section-label">MVP</div><div class="section-content">${{idea.startup_analysis.mvp || ''}}</div></div>
        <div class="section"><div class="section-label">Market Direction</div><div class="section-content">${{idea.startup_analysis.market_direction || ''}}</div></div>
        ` : ''}}
        ${{scoreHtml ? `<div class="scores">${{scoreHtml}}</div>` : ''}}
        ${{evidenceHtml ? `<div class="evidence">${{evidenceHtml}}</div>` : ''}}
      </div>`;
  }}).join('');
}}

filterIdeas();
</script>
</body>
</html>"""

    with open(output_path, "w") as f:
        f.write(page)
