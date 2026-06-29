#!/usr/bin/env python3
"""Generate index.html from locations.json."""

import json
import sys

VIEWER_JS = r"""
const data = JSON.parse(document.getElementById('data').textContent);
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];

let state = { q: '', type: 'all', coordsOnly: false };

function esc(s) {
  return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function mapUrl(lat, lng) {
  return `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lng}#map=13/${lat}/${lng}`;
}

function matches(item) {
  if (state.type !== 'all' && item.type !== state.type) return false;
  if (state.coordsOnly && item.lat == null) return false;
  if (!state.q) return true;
  const hay = [item.title, item.region, item.category, item.coordinatesRaw].join(' ').toLowerCase();
  return hay.includes(state.q.toLowerCase());
}

function render() {
  const main = $('#main');
  const summary = data.summary;
  $('#stats').innerHTML = `
    <span><strong>${summary.total}</strong> total</span>
    <span><strong>${summary.withCoordinates}</strong> with GPS</span>
    <span><strong>${summary.groupCount}</strong> groups</span>
    <span><strong>${summary.byType.location || 0}</strong> locations</span>
    <span><strong>${summary.byType.tour || 0}</strong> tours</span>
  `;

  let visibleGroups = 0;
  let visibleItems = 0;
  main.innerHTML = '';

  for (const group of data.groups) {
    const items = group.items.filter(matches);
    if (!items.length) continue;
    visibleGroups++;
    visibleItems += items.length;

    const section = document.createElement('section');
    section.className = 'group';
    section.innerHTML = `
      <button class="group-head" type="button" aria-expanded="true">
        <span class="group-title">
          <span class="badge badge-${group.type}">${group.type}</span>
          ${esc(group.category)}
        </span>
        <span class="group-meta">${items.length} shown · ${group.withCoordinates} with coords</span>
        <span class="chevron">▼</span>
      </button>
      <div class="group-body"></div>
    `;

    const body = $('.group-body', section);
    for (const item of items) {
      const card = document.createElement('article');
      card.className = 'card';
      const coord = item.lat != null
        ? `<a class="coord" href="${mapUrl(item.lat, item.lng)}" target="_blank" rel="noopener">${item.lat}, ${item.lng}</a>`
        : '<span class="muted">no coordinates</span>';
      card.innerHTML = `
        <h3><a href="${esc(item.url)}" target="_blank" rel="noopener">${esc(item.title)}</a></h3>
        <div class="card-meta">
          ${item.region ? `<span class="region">${esc(item.region)}</span>` : ''}
          ${coord}
        </div>
      `;
      body.appendChild(card);
    }

    $('.group-head', section).addEventListener('click', () => {
      section.classList.toggle('collapsed');
      const open = !section.classList.contains('collapsed');
      $('.group-head', section).setAttribute('aria-expanded', open);
    });

    main.appendChild(section);
  }

  $('#result-count').textContent = visibleItems
    ? `${visibleItems} items in ${visibleGroups} groups`
    : 'No matches';
}

function bind() {
  $('#search').addEventListener('input', e => { state.q = e.target.value.trim(); render(); });
  $('#type').addEventListener('change', e => { state.type = e.target.value; render(); });
  $('#coords-only').addEventListener('change', e => { state.coordsOnly = e.target.checked; render(); });
  $('#expand-all').addEventListener('click', () => $$('.group').forEach(g => g.classList.remove('collapsed')));
  $('#collapse-all').addEventListener('click', () => $$('.group').forEach(g => g.classList.add('collapsed')));
}

bind();
render();
"""

VIEWER_CSS = """
:root {
  --bg: #f4f1ea;
  --surface: #fff;
  --text: #1f2933;
  --muted: #6b7280;
  --border: #e5e0d6;
  --accent: #c8922a;
  --accent-soft: #f5ead4;
  --location: #2d6a4f;
  --tour: #1d4e89;
  --shadow: 0 1px 3px rgba(0,0,0,.08);
  --radius: 10px;
  font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  line-height: 1.5;
}
a { color: var(--tour); }
header {
  position: sticky;
  top: 0;
  z-index: 10;
  background: rgba(244,241,234,.95);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--border);
  padding: 1rem 1.25rem;
}
.header-inner { max-width: 1100px; margin: 0 auto; }
h1 { margin: 0 0 .25rem; font-size: 1.35rem; }
.subtitle { margin: 0 0 .75rem; color: var(--muted); font-size: .9rem; }
#stats {
  display: flex;
  flex-wrap: wrap;
  gap: .75rem 1.25rem;
  font-size: .85rem;
  margin-bottom: .9rem;
}
.controls {
  display: flex;
  flex-wrap: wrap;
  gap: .6rem;
  align-items: center;
}
#search {
  flex: 1 1 220px;
  padding: .55rem .75rem;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: .95rem;
}
select, .btn {
  padding: .55rem .75rem;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  font-size: .9rem;
  cursor: pointer;
}
.btn:hover { background: var(--accent-soft); }
label.chk {
  display: flex;
  align-items: center;
  gap: .35rem;
  font-size: .9rem;
  color: var(--muted);
  cursor: pointer;
}
main { max-width: 1100px; margin: 0 auto; padding: 1rem 1.25rem 3rem; }
#result-count { color: var(--muted); font-size: .85rem; margin-bottom: 1rem; }
.group {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  margin-bottom: .75rem;
  overflow: hidden;
}
.group-head {
  width: 100%;
  display: flex;
  align-items: center;
  gap: .75rem;
  padding: .85rem 1rem;
  border: 0;
  background: transparent;
  text-align: left;
  cursor: pointer;
  font: inherit;
}
.group-head:hover { background: #faf8f4; }
.group-title { flex: 1; font-weight: 600; display: flex; align-items: center; gap: .5rem; }
.group-meta { color: var(--muted); font-size: .82rem; }
.chevron { color: var(--muted); font-size: .75rem; transition: transform .15s; }
.group.collapsed .group-body { display: none; }
.group.collapsed .chevron { transform: rotate(-90deg); }
.group-body {
  display: grid;
  gap: .5rem;
  padding: 0 1rem 1rem;
  border-top: 1px solid var(--border);
}
.card {
  padding: .7rem .85rem;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: #fcfbfa;
}
.card h3 { margin: 0 0 .35rem; font-size: 1rem; }
.card h3 a { text-decoration: none; color: var(--text); }
.card h3 a:hover { color: var(--accent); text-decoration: underline; }
.card-meta { display: flex; flex-wrap: wrap; gap: .5rem 1rem; font-size: .85rem; }
.region { color: var(--location); }
.coord { font-family: ui-monospace, monospace; font-size: .82rem; }
.muted { color: var(--muted); font-size: .82rem; }
.badge {
  font-size: .68rem;
  text-transform: uppercase;
  letter-spacing: .04em;
  padding: .15rem .45rem;
  border-radius: 999px;
  color: #fff;
  font-weight: 700;
}
.badge-location { background: var(--location); }
.badge-tour { background: var(--tour); }
.badge-both { background: var(--accent); }
footer {
  max-width: 1100px;
  margin: 0 auto;
  padding: 0 1.25rem 2rem;
  color: var(--muted);
  font-size: .8rem;
}
@media (max-width: 640px) {
  .group-head { flex-wrap: wrap; }
  .group-meta { width: 100%; padding-left: 0; }
}
"""


def build_html(data, path="index.html"):
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ArmGeo Locations</title>
  <style>{VIEWER_CSS}</style>
</head>
<body>
  <header>
    <div class="header-inner">
      <h1>ArmGeo Locations</h1>
      <p class="subtitle">Browse tours and places from <a href="{data.get('source', '#')}" target="_blank" rel="noopener">armgeo.am</a></p>
      <div id="stats"></div>
      <div class="controls">
        <input id="search" type="search" placeholder="Search title, region, category…" autocomplete="off">
        <select id="type" aria-label="Filter by type">
          <option value="all">All types</option>
          <option value="location">Locations only</option>
          <option value="tour">Tours only</option>
        </select>
        <label class="chk"><input id="coords-only" type="checkbox"> GPS only</label>
        <button class="btn" id="expand-all" type="button">Expand all</button>
        <button class="btn" id="collapse-all" type="button">Collapse all</button>
      </div>
    </div>
  </header>
  <main>
    <div id="result-count"></div>
    <div id="main"></div>
  </main>
  <footer>Generated from locations.json · coordinates open in OpenStreetMap</footer>
  <script id="data" type="application/json">{json.dumps(data, ensure_ascii=False)}</script>
  <script>{VIEWER_JS}</script>
</body>
</html>
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "locations.json"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "index.html"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    build_html(data, out_path)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
