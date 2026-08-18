"""HTML exporter for trace — minimal aesthetic.

Self-contained single-file HTML, file:// safe (no CDN).
Minimal, quiet, spacious — muted palette with single theme accent.
"""

from __future__ import annotations

# ruff: noqa: I001, B905

import html as _html
import json as _json
from pathlib import Path

from .models import TraceGraph
from .query import TraceNode, TraceTree

_THEMES: dict[str, dict[str, str]] = {
    "anthropic-pro": {"bg": "#0a0a0f", "panel": "#14141e", "panel2": "#1c1c2a", "line": "#23232e", "border": "#23232e", "ink": "#E8E6E3", "muted": "#9A9590", "muted2": "#6a6886", "accent": "#D4A27F"},
    "cinematic": {"bg": "#0b0c0f", "panel": "#121316", "panel2": "#1a1c1f", "line": "#232529", "border": "#232529", "ink": "#E8E9EB", "muted": "#9AA0A6", "muted2": "#5F6368", "accent": "#FF3B30"},
    "dracula": {"bg": "#282a36", "panel": "#1e1f29", "panel2": "#2a2c3a", "line": "#333545", "border": "#333545", "ink": "#f8f8f2", "muted": "#8b8fa3", "muted2": "#6a6e85", "accent": "#ff79c6"},
    "catppuccin-mocha": {"bg": "#1e1e2e", "panel": "#181825", "panel2": "#252536", "line": "#313244", "border": "#313244", "ink": "#cdd6f4", "muted": "#9ca0b0", "muted2": "#7f849c", "accent": "#f9e2af"},
    "github-dark": {"bg": "#0d1117", "panel": "#11151c", "panel2": "#1a1f29", "line": "#21262d", "border": "#21262d", "ink": "#c9d1d9", "muted": "#8b949e", "muted2": "#6e7681", "accent": "#58a6ff"},
    "minimal-mono": {"bg": "#fcfcfc", "panel": "#ffffff", "panel2": "#f5f5f5", "line": "#e8e8e8", "border": "#e8e8e8", "ink": "#111111", "muted": "#888888", "muted2": "#aaaaaa", "accent": "#111111"},
    "monokai": {"bg": "#272822", "panel": "#1e1f1c", "panel2": "#2a2b26", "line": "#3a3b35", "border": "#3a3b35", "ink": "#f8f8f2", "muted": "#9a9a92", "muted2": "#7a7a72", "accent": "#f92672"},
    "nord": {"bg": "#2e3440", "panel": "#353c4a", "panel2": "#3f4759", "line": "#434c5e", "border": "#434c5e", "ink": "#eceff4", "muted": "#aeb8c9", "muted2": "#8a95aa", "accent": "#88c0d0"},
    "solarized-dark": {"bg": "#002b36", "panel": "#073642", "panel2": "#0a3d4a", "line": "#184a5a", "border": "#184a5a", "ink": "#eee8d5", "muted": "#93a1a1", "muted2": "#708183", "accent": "#b58900"},
    "tokyo-night": {"bg": "#1a1b26", "panel": "#16161e", "panel2": "#1f2233", "line": "#2a2e44", "border": "#2a2e44", "ink": "#c0caf5", "muted": "#7a80a3", "muted2": "#5a5f7a", "accent": "#bb9af7"},
}


def _tokens(theme=None) -> dict[str, str]:
    try:
        if theme and hasattr(theme, "tokens"):
            merged = dict(_THEMES["anthropic-pro"])
            merged.update(theme.tokens)  # type: ignore[attr-defined]
            return merged
        if isinstance(theme, str) and theme in _THEMES:
            return _THEMES[theme]
        if theme and hasattr(theme, "name") and str(theme.name) in _THEMES:  # type: ignore[attr-defined]
            return _THEMES[str(theme.name)]  # type: ignore[attr-defined]
    except Exception:
        pass
    return _THEMES["anthropic-pro"]


def _theme_label(theme) -> str:
    try:
        if isinstance(theme, str) and theme in _THEMES:
            return theme
        if theme and hasattr(theme, "name"):
            v = str(theme.name)  # type: ignore[attr-defined]
            if v in _THEMES:
                return v
    except Exception:
        pass
    return "anthropic-pro"


def _esc(s: str) -> str:
    return _html.escape(s or "", quote=True)


def _rel_for(node, graph: TraceGraph) -> str:
    try:
        return node.rel.as_posix()  # type: ignore[attr-defined]
    except Exception:
        try:
            return node.rel.name  # type: ignore[attr-defined]
        except Exception:
            return str(getattr(node, "file", ""))


def _sig_for(func) -> str:
    try:
        params_str = ", ".join(p.format() for p in getattr(func, "params", []) or [])
        sig = f"{func.qualname}({params_str})"
        if getattr(func, "returns", None):
            sig += f" -> {func.returns}"
        if len(sig) > 100:
            sig = sig[:97] + "..."
        return sig
    except Exception:
        return getattr(func, "qualname", "?")  # type: ignore[attr-defined]


def build_trace_html(trace_tree: TraceTree, graph: TraceGraph, theme=None, root_path: Path | None = None) -> str:
    t0 = _tokens(theme)
    theme_name = _theme_label(theme)
    focal = graph.nodes[trace_tree.focal]
    focal_sig = _sig_for(focal)

    files_involved: set[str] = set()

    def _collect(n: TraceNode):
        try:
            if str(n.func.file) != "<external>":
                files_involved.add(_rel_for(n.func, graph))
        except Exception:
            pass
        for c in n.children:
            _collect(c)

    _collect(trace_tree.root)
    files_sorted = sorted(files_involved)
    file_pills = "".join(f'<button class="file-pill" onclick="filterTo(\'{_esc(f)}\')">{_esc(f)}</button>' for f in files_sorted[:10])
    if len(files_sorted) > 10:
        file_pills += f'<span class="pill muted">+{len(files_sorted)-10}</span>'
    files_str = ", ".join(files_sorted[:5]) + (f" +{len(files_sorted)-5}" if len(files_sorted) > 5 else "")

    themes = list(_THEMES.keys())

    def _node_html(node: TraceNode, depth: int = 0) -> str:
        func = node.func
        rel = _rel_for(func, graph) if not node.is_external else "<external>"
        sig = _sig_for(func) if not node.is_external else (node.external_label or getattr(func, "qualname", "?"))
        kind = _esc(getattr(func, "kind", "def"))
        lineno = getattr(func, "lineno", 0)
        is_focal = depth == 0
        has_children = len(node.children) > 0

        # minimal chips — muted, only accent for focal
        file_name = rel.split("/")[-1] if "/" in rel else rel
        file_chip = f'<span class="chip file" title="{_esc(rel)}">{_esc(file_name)}:{lineno}</span>' if not node.is_external else '<span class="chip">external</span>'
        kind_chip = f'<span class="chip">{kind}</span>'
        badge = ""
        if node.is_cycle:
            badge = '<span class="chip cycle">↺ recursive</span>'
        elif node.is_external:
            badge = f'<span class="chip">{_esc(node.external_label or "")}</span>'

        edge_html = ""
        if node.edge:
            e = node.edge  # type: ignore[attr-defined]
            try:
                call_args = getattr(e, "call_args", []) or []
                assign = getattr(e, "assign_target", None)
                eline = getattr(e, "lineno", lineno)
                is_await = getattr(e, "is_await", False)
                # minimal — just text, no colourful pills
                args_txt = ", ".join(_esc(a) for a in call_args[:3])
                if len(call_args) > 3:
                    args_txt += ", …"
                if not args_txt:
                    args_txt = "—"
                assign_html = f'<span class="assign">→ {_esc(assign)}</span>' if assign else ""
                await_html = '<span class="await">await</span>' if is_await else ""
                edge_html = f'<div class="edge"><span class="edge-k">takes</span> <span class="edge-v">{args_txt}</span> {assign_html} <span class="edge-meta">· L{eline} {await_html}</span></div>'
            except Exception:
                edge_html = ""

        toggle = ""
        if has_children:
            toggle = '<span class="toggle">▾</span>'
        elif node.is_external:
            toggle = '<span class="toggle leaf">↗</span>'
        else:
            toggle = '<span class="toggle leaf">·</span>'

        children_html = ""
        if has_children:
            inner = "".join(_node_html(c, depth + 1) for c in node.children)
            style = "" if depth < 2 else ' style="display:none"'
            children_html = f'<ul class="children"{style}>{inner}</ul>'
            if depth >= 2:
                toggle = '<span class="toggle">▸</span>'

        filter_text = _esc(f"{func.qualname} {rel} {kind} {sig}")
        cls = "node" + (" focal" if is_focal else "") + (" cycle" if node.is_cycle else "")
        actions = f'<span class="actions"><button class="icon-btn" onclick="copyText(event, \'{_esc(sig)}\')" title="Copy">⧉</button></span>' if not node.is_external else ""
        return (
            f'<li class="{cls}" data-filter="{filter_text}">'
            f'<div class="row" onclick="toggleRow(this)">{toggle}<span class="sig">{_esc(sig)}</span> {kind_chip} {file_chip} {badge} {actions}</div>'
            f"{edge_html}"
            f"{children_html}"
            f"</li>"
        )

    tree_html = _node_html(trace_tree.root)

    try:
        from .render import trace_to_json

        payload = trace_to_json(trace_tree, graph)
        payload["root"] = str(root_path or graph.root)
        json_str = _json.dumps(payload, indent=2, ensure_ascii=False)
        json_esc = _esc(json_str)
    except Exception:
        json_str = "{}"
        json_esc = "{}"

    theme_css = "\n".join(f'[data-theme="{k}"]{{' + "".join(f"--{ck}:{cv};" for ck, cv in v.items()) + "}" for k, v in _THEMES.items())

    return f"""<!doctype html>
<html lang="en" data-theme="{_esc(theme_name)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark light">
<title>peek trace — {_esc(focal.qualname)} · depth {trace_tree.depth}</title>
<style>
{theme_css}
:root{{--bg:{t0["bg"]};--panel:{t0["panel"]};--panel2:{t0["panel2"]};--line:{t0["line"]};--border:{t0["border"]};--ink:{t0["ink"]};--muted:{t0["muted"]};--muted2:{t0["muted2"]};--accent:{t0["accent"]};--radius:12px;--radius-sm:8px}}
*{{box-sizing:border-box}} html{{scroll-behavior:smooth}} html,body{{margin:0;padding:0;background:var(--bg);color:var(--ink);font:13.5px/1.6 Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;-webkit-font-smoothing:antialiased;}}
a{{color:var(--ink);text-decoration:none;border-bottom:1px solid var(--border)}} a:hover{{border-color:var(--accent)}}
/* header — minimal */
.header{{position:sticky;top:0;z-index:20;background:var(--panel);border-bottom:1px solid var(--border);padding:14px 18px}}
.header-top{{display:flex;gap:12px;align-items:center;flex-wrap:wrap}}
.brand{{display:flex;align-items:center;gap:10px;font-size:13px;font-weight:600;letter-spacing:-.01em}}
.brand .logo{{width:24px;height:24px;display:grid;place-items:center;border:1px solid var(--border);border-radius:6px;font-size:11px;color:var(--muted)}}
.brand small{{font-weight:500;color:var(--muted);letter-spacing:.08em;text-transform:uppercase;font-size:10px}}
.toolbar{{display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-left:auto}}
.toolbar input{{min-width:220px;background:var(--panel2);color:var(--ink);border:1px solid var(--border);border-radius:8px;padding:7px 10px 7px 30px;font-size:12px;outline:none;transition:border-color .12s}}
.toolbar input:focus{{border-color:var(--accent)}}
.toolbar input{{background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%239A9590' stroke-width='2'%3E%3Ccircle cx='11' cy='11' r='6'/%3E%3Cpath d='M21 21l-3-3'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:10px 50%}}
.toolbar select{{background:var(--panel2);color:var(--muted);border:1px solid var(--border);border-radius:8px;padding:7px 8px;font-size:12px;outline:none}}
.toolbar button{{background:var(--panel2);color:var(--muted);border:1px solid var(--border);border-radius:8px;padding:7px 10px;font-size:11px;font-weight:500;cursor:pointer;transition:all .12s}}
.toolbar button:hover{{border-color:var(--border);color:var(--ink)}}
.toolbar button.primary{{background:var(--ink);color:var(--bg);border-color:var(--ink)}} .toolbar button.primary:hover{{opacity:.9}}
.hero{{margin-top:10px;display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}}
.hero h1{{margin:0;font-size:15px;font-weight:600;letter-spacing:-.02em}}
.hero h1 span{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-weight:600}}
.hero .focal-sig{{font-family:ui-monospace,monospace;font-size:11px;color:var(--muted);background:var(--panel2);border:1px solid var(--border);border-radius:999px;padding:3px 8px}}
.stats{{display:flex;gap:6px;align-items:center;flex-wrap:wrap;font-size:11px;color:var(--muted);margin-top:8px}}
.pill{{display:inline-flex;align-items:center;gap:5px;background:var(--panel2);border:1px solid var(--border);border-radius:999px;padding:3px 8px;font-size:11px;color:var(--muted)}}
.pill.accent{{border-color:var(--accent);color:var(--accent);background:transparent}}
/* layout — airy */
.wrap{{max-width:1100px;margin:0 auto;padding:18px 16px 40px}}
.grid{{display:grid;grid-template-columns:1fr 300px;gap:16px;align-items:start}}
@media (max-width:960px){{.grid{{grid-template-columns:1fr}}}}
.card{{background:var(--panel);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden}}
.card-head{{padding:10px 12px;border-bottom:1px solid var(--border);display:flex;gap:8px;align-items:center;flex-wrap:wrap}}
.card-head h2{{margin:0;font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);font-weight:600}}
.card-head .spacer{{margin-left:auto;display:flex;gap:6px;align-items:center}}
.mini{{font-size:10px;color:var(--muted2)}}
.chip{{display:inline-flex;align-items:center;border:1px solid var(--border);background:var(--panel2);border-radius:999px;padding:1px 7px;font-size:10px;color:var(--muted);font-weight:500}}
.chip.file{{color:var(--muted)}} .chip.cycle{{border-color:var(--accent);color:var(--accent)}}
.file-pill{{display:inline-flex;align-items:center;border:1px solid var(--border);background:transparent;border-radius:999px;padding:3px 8px;font-size:10px;color:var(--muted);cursor:pointer}} .file-pill:hover{{border-color:var(--accent);color:var(--ink)}}
/* tree — minimal lines */
.tree{{list-style:none;margin:0;padding:8px 10px 12px}}
.tree ul{{list-style:none;margin:6px 0 0 11px;padding-left:12px;border-left:1px solid var(--border)}}
.node{{margin:5px 0;padding:8px 8px 6px;border-radius:8px;border:1px solid transparent;transition:background .12s, border-color .12s}}
.node:hover{{background:var(--panel2);border-color:var(--border)}}
.node.focal{{background:var(--panel2);border-color:var(--accent)}}
.node.focal .sig{{color:var(--ink)}}
.row{{display:flex;gap:7px;align-items:center;cursor:pointer;flex-wrap:wrap}}
.toggle{{width:16px;height:16px;display:grid;place-items:center;border-radius:4px;font-size:10px;color:var(--muted2);flex:0 0 16px}} .toggle.leaf{{color:var(--muted2)}}
.sig{{font-weight:600;color:var(--ink);font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12.5px;letter-spacing:-.01em;word-break:break-word}} .sig mark{{background:color-mix(in srgb, var(--accent) 18%, transparent);border-radius:3px;padding:0 1px}}
.edge{{margin:4px 0 0 23px;font-size:10.5px;color:var(--muted);font-family:ui-monospace,monospace;display:flex;gap:5px;flex-wrap:wrap;align-items:center}} .edge-k{{color:var(--muted2);font-weight:600;letter-spacing:.06em;text-transform:uppercase;font-size:9px}} .edge-v{{color:var(--muted)}} .assign{{color:var(--ink);font-weight:600}} .edge-meta{{color:var(--muted2)}} .await{{border:1px solid var(--border);border-radius:999px;padding:0 5px;font-size:9px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}}
.actions{{margin-left:auto;display:inline-flex;gap:3px;opacity:0;transition:opacity .12s}} .node:hover .actions{{opacity:1}} .icon-btn{{width:18px;height:18px;display:grid;place-items:center;border-radius:5px;border:1px solid var(--border);background:transparent;color:var(--muted);font-size:10px;cursor:pointer}} .icon-btn:hover{{border-color:var(--accent);color:var(--ink)}}
.hidden{{display:none !important}} .empty{{padding:20px;text-align:center;color:var(--muted);font-size:12px}} .empty b{{color:var(--ink)}}
.side .card{{position:sticky;top:78px}} .side h3{{margin:0 0 6px;font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);font-weight:600}} .side .stack{{display:flex;flex-direction:column;gap:14px;padding:12px}} .side .file-list{{display:flex;flex-wrap:wrap;gap:5px}} .foot{{margin-top:10px;font-size:10px;color:var(--muted2);display:flex;gap:8px;flex-wrap:wrap}} .foot code{{background:var(--panel2);border:1px solid var(--border);border-radius:5px;padding:1px 5px;font-size:10px}} .kbd{{display:inline-block;border:1px solid var(--border);border-bottom-width:1.5px;background:var(--panel2);border-radius:5px;padding:0 4px;font-size:10px;font-family:ui-monospace,monospace;color:var(--muted)}}
@media print{{.header{{position:static}} .toolbar,.side{{display:none}} .grid{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<div class="header">
  <div class="header-top">
    <div class="brand"><span class="logo">—</span> peek <small>trace</small></div>
    <div class="toolbar">
      <input id="q" type="search" placeholder="Filter" aria-label="Filter" oninput="onFilter(this.value)">
      <select id="theme" aria-label="Theme" onchange="setTheme(this.value)">{''.join(f'<option value="{_esc(th)}">{_esc(th)}</option>' for th in themes)}</select>
      <button onclick="expandAll()" title="Expand (e)">Expand</button>
      <button onclick="collapseAll()" title="Collapse (c)">Collapse</button>
      <button class="primary" onclick="copyJson()">Copy JSON</button>
      <button onclick="downloadHtml()">Save</button>
    </div>
  </div>
  <div class="hero">
    <h1><span>{_esc(focal.qualname)}</span></h1>
    <span class="focal-sig">{_esc(focal_sig)}</span>
    <span class="pill accent">{trace_tree.direction} · depth {trace_tree.depth}</span>
  </div>
  <div class="stats">
    <span class="pill"><b>{trace_tree.total_nodes}</b> nodes</span>
    <span class="pill"><b>{len(files_sorted)}</b> files</span>
    <span class="pill">{_esc(focal.rel.as_posix() if hasattr(focal.rel, "as_posix") else str(focal.rel))}:{focal.lineno}</span>
    <span class="pill muted">{_esc(files_str) if files_str else "—"}</span>
  </div>
</div>
<div class="wrap">
  <div class="grid">
    <div class="card">
      <div class="card-head">
        <h2>Trace Tree</h2>
        <span class="pill muted">{trace_tree.direction} · depth {trace_tree.depth}</span>
        <span class="pill muted" id="matchCount" style="display:none"></span>
        <div class="spacer"><span class="mini">{len(files_sorted)} files · {trace_tree.total_nodes} nodes</span></div>
      </div>
      <ul class="tree" id="tree">{tree_html}</ul>
      <div id="empty" class="empty hidden">No matches — <a href="#" onclick="clearFilter();return false">clear filter</a></div>
    </div>
    <div class="side">
      <div class="card">
        <div class="stack">
          <div>
            <h3>Files</h3>
            <div class="file-list">{file_pills or '<span class="muted" style="font-size:11px">—</span>'}</div>
          </div>
          <div>
            <h3>Reading</h3>
            <div style="font-size:11px;color:var(--muted);line-height:1.6">
              <div><span class="edge-k">takes</span> args at call site → <span class="assign">assign</span> · L line</div>
              <div style="margin-top:4px"><span class="kbd">/</span> filter · <span class="kbd">e</span> expand · <span class="kbd">c</span> collapse · <span class="kbd">Esc</span> clear</div>
            </div>
          </div>
          <div>
            <h3>Meta</h3>
            <div style="font-size:11px;color:var(--muted);display:flex;flex-direction:column;gap:3px">
              <div>Direction <b style="color:var(--ink)">{_esc(trace_tree.direction)}</b></div>
              <div>Depth <b style="color:var(--ink)">{trace_tree.depth}</b></div>
              <div>Nodes <b style="color:var(--ink)">{trace_tree.total_nodes}</b></div>
              <div style="word-break:break-all" class="muted">{_esc(str(root_path or ""))}</div>
            </div>
          </div>
          <div style="display:flex;gap:6px">
            <button onclick="expandAll()" style="flex:1">Expand</button>
            <button onclick="collapseAll()" style="flex:1">Collapse</button>
          </div>
        </div>
      </div>
      <div class="foot"><span>peek trace <code>{_esc(focal.qualname)} --depth {trace_tree.depth}</code></span> <span class="muted">· file:// safe · <a href="#" onclick="copyJson();return false">copy JSON</a></span></div>
    </div>
  </div>
  <pre id="json" class="hidden">{json_esc}</pre>
</div>
<script>
const THEMES = {_json.dumps(_THEMES)};
const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];
function setTheme(name) {{
  if (!name || !THEMES[name]) return;
  const t = THEMES[name];
  const root = document.documentElement;
  for (const [k,v] of Object.entries(t)) root.style.setProperty('--'+k, v);
  root.setAttribute('data-theme', name);
  localStorage.setItem('peek-theme', name);
  const sel = $('#theme');
  if (sel && sel.value !== name) sel.value = name;
}}
function applySavedTheme() {{
  const saved = localStorage.getItem('peek-theme');
  const initial = document.documentElement.getAttribute('data-theme');
  const name = (saved && THEMES[saved]) ? saved : (THEMES[initial] ? initial : 'anthropic-pro');
  setTheme(name);
}}
function toggleRow(el) {{
  const li = el.closest('li');
  const ul = li.querySelector(':scope > ul');
  if (!ul) return;
  const hidden = ul.style.display === 'none';
  ul.style.display = hidden ? '' : 'none';
  const tw = el.querySelector('.toggle');
  if (tw) tw.textContent = hidden ? '▾' : '▸';
}}
function expandAll() {{ $$('#tree ul').forEach(u=>u.style.display=''); $$('#tree .toggle').forEach(t=>{{ if(t.textContent==='▸') t.textContent='▾'; }}); }}
function collapseAll() {{ $$('#tree ul').forEach(u=>u.style.display='none'); $$('#tree .toggle').forEach(t=>{{ if(t.textContent==='▾') t.textContent='▸'; }}); const root = document.querySelector('#tree > li > ul'); if(root) root.style.display=''; const rt=document.querySelector('#tree > li > .row .toggle'); if(rt) rt.textContent='▾'; }}
function clearFilter() {{ const q=$('#q'); if(q){{ q.value=''; onFilter(''); }} }}
function filterTo(file) {{ const q=$('#q'); if(q){{ q.value=file; onFilter(file); q.focus(); }} }}
function escapeReg(s){{ return s.replace(/[.*+?^${{}}()|[\\]\\\\]/g,'\\\\$&'); }}
function onFilter(q) {{
  q = (q||'').trim();
  const lower = q.toLowerCase();
  const all = $$('#tree li');
  if (!q) {{
    all.forEach(li=>{{ li.classList.remove('hidden'); const sig=li.querySelector('.sig'); if(sig){{ sig.innerHTML = sig.textContent; }} }});
    document.getElementById('empty').classList.add('hidden');
    if (all.length>50) collapseAll(); else expandAll();
    const el=document.getElementById('matchCount'); if(el) el.style.display='none';
    return;
  }}
  let visible=0;
  all.forEach(li=>li.classList.add('hidden'));
  const re=new RegExp('('+escapeReg(q)+')','ig');
  all.forEach(li=>{{
    const txt=(li.getAttribute('data-filter')||'');
    if(txt.toLowerCase().includes(lower)) {{
      const sigEl=li.querySelector('.sig');
      if(sigEl && q.length>=2) {{
        const raw=sigEl.textContent;
        sigEl.innerHTML=raw.replace(re,'<mark class="hl" style="background:color-mix(in srgb, var(--accent) 18%, transparent);border-radius:3px;padding:0 1px">$1</mark>');
      }}
      let cur=li;
      while(cur && cur.id!=='tree') {{
        cur.classList.remove('hidden');
        if(cur.tagName==='UL') cur.style.display='';
        const row=cur.querySelector(':scope > .row .toggle');
        if(row && row.textContent==='▸') row.textContent='▾';
        cur=cur.parentElement;
      }}
      visible++;
    }}
  }});
  document.getElementById('empty').classList.toggle('hidden', visible!==0);
  const el=document.getElementById('matchCount');
  if(el){{ el.textContent=visible+' matches'; el.style.display=''; }}
}}
function copyText(e, txt) {{ e.stopPropagation(); navigator.clipboard.writeText(txt).then(()=>{{ const btn=e.currentTarget; const old=btn.textContent; btn.textContent='✓'; setTimeout(()=>btn.textContent=old, 800); }}); }}
function copyJson() {{ const txt=document.getElementById('json').textContent; navigator.clipboard.writeText(txt).then(()=>{{ const b=document.activeElement; const orig=b?b.textContent:''; if(b){{ b.textContent='copied!'; setTimeout(()=>b.textContent=orig||'Copy JSON', 1000); }} }}); }}
function downloadHtml() {{ const blob=new Blob([document.documentElement.outerHTML], {{type:'text/html'}}); const url=URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download='trace-{_esc(focal.qualname)}.html'; a.click(); URL.revokeObjectURL(url); }}
document.addEventListener('keydown', e=>{{ if(e.key==='/' && !e.ctrlKey && !e.metaKey){{ const ae=document.activeElement; if(ae && ae.tagName==='INPUT') return; e.preventDefault(); $('#q').focus(); }} if(e.key==='Escape') clearFilter(); if((e.key==='e'||e.key==='E')&&!e.ctrlKey){{ if(document.activeElement.tagName!=='INPUT') expandAll(); }} if((e.key==='c'||e.key==='C')&&!e.ctrlKey){{ if(document.activeElement.tagName!=='INPUT') collapseAll(); }} }});
applySavedTheme();
(function(){{ const cur=document.documentElement.getAttribute('data-theme'); const sel=$('#theme'); if(sel) sel.value=cur; const n=$$('#tree li').length; if(n>60) collapseAll(); else if(n>20){{ $$('#tree li li ul').forEach(u=>u.style.display='none'); $$('#tree li li .toggle').forEach(t=>{{ if(t.textContent==='▾') t.textContent='▸'; }}); }} }})();
</script>
</body>
</html>
"""
