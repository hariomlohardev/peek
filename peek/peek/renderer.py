"""Renderer — static Rich output for peek · Lab Notebook No.01

Day 3+ redesign: every panel is a sheet of paper on graph-paper.
Colors from Lab tokens: paper #FFFEFB, ink #0B1220, signal #FFD400, line #D9E2EF.
Used by `peek --no-tui` and `build_html` (full lab notebook page).
"""

from __future__ import annotations

from pathlib import Path

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from peek import __version__
from peek._ascii_graph import ascii_graph

# Lab Notebook No.01 — tokens mapped to Rich styles
INK = "#0B1220"
INK2 = "#1A2744"
MUTED = "#6E7D9A"
MUTED2 = "#8A9AB6"
LINE = "#D9E2EF"
LINE2 = "#B9C8E2"
SIGNAL = "#FFD400"
SIGNAL_SOFT = "#FFF4B3"  # soft wash
PAPER = "#FFFEFB"
PAPER2 = "#F3F0E8"
RED = "#E10600"
BLUE = "#0050FF"
GREEN = "#0E9F6E"


def _format_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n/1024:.1f} KB"
    return f"{n/(1024*1024):.1f} MB"


def make_header(root: Path, elapsed: float) -> Panel:
    header = Text()
    header.append("◈ PEEK", style=f"bold {INK}")
    header.append("  Lab — 01", style=f"dim {MUTED}")
    header.append(f"  v{__version__}", style=f"dim {MUTED}")
    header.append(f"  —  {root}", style=f"{BLUE}")
    header.append(f"  ({elapsed:.2f}s)", style=f"dim {MUTED}")
    # Washi tape hint via subtitle
    return Panel(
        header,
        box=box.ROUNDED,
        border_style=INK,
        padding=(0, 1),
        title="[#FFD400 on #0B1220] LAB NOTEBOOK No.01 [/]",
        title_align="left",
        subtitle=f"[{MUTED}]graph-paper · sheet · tape[/]",
        subtitle_align="right",
    )


def make_languages_panel(stats: dict) -> Panel | None:
    by_lang = stats.get("by_lang", {})
    if not by_lang:
        return None
    sorted_langs = sorted(by_lang.items(), key=lambda x: x[1], reverse=True)[:6]
    total = sum(by_lang.values())
    t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style=f"bold {INK}", padding=(0, 1), border_style=LINE)
    t.add_column("Language", style=INK)
    t.add_column("Files", justify="right", style=GREEN)
    t.add_column("Share", justify="right", style=MUTED)
    t.add_column("Bar", style=SIGNAL)
    max_count = sorted_langs[0][1] if sorted_langs else 1
    for lang, count in sorted_langs:
        pct = count / total * 100 if total else 0
        bar_len = int(count / max_count * 16) if max_count else 0
        bar = "█" * bar_len + "░" * (16 - bar_len)
        t.add_row(f"[{INK}]{lang}[/]", str(count), f"{pct:.0f}%", f"[{SIGNAL}]{bar}[/]")
    return Panel(t, title=f"[bold {INK}]Languages[/]", subtitle=f"[{MUTED}]paper-2 · ink · signal[/]", box=box.ROUNDED, border_style=INK, padding=(0, 1))


def make_tech_stack_panel(tech_stack: dict, external_imports: set[str] | None = None) -> Panel | None:
    if not tech_stack:
        return None
    lines: list[str] = []
    if tech_stack.get("primary") and tech_stack["primary"] != "unknown":
        lines.append(f"[bold {INK}]Primary:[/] [{INK2}]{tech_stack['primary']}[/]")
    if tech_stack.get("frameworks"):
        lines.append(f"[bold {INK}]Frameworks:[/] [{BLUE}]{', '.join(tech_stack['frameworks'])}[/]")
    if external_imports:
        preview = ", ".join(sorted(external_imports)[:8])
        if len(external_imports) > 8:
            preview += f"  [dim {MUTED}](+{len(external_imports)-8} more)[/]"
        lines.append(f"[bold {INK}]External:[/] [{MUTED}]{preview}[/]")
    if tech_stack.get("configs"):
        lines.append(f"[bold {INK}]Configs:[/] [{MUTED}]{', '.join(tech_stack['configs'][:6])}[/]")
    if tech_stack.get("deps"):
        deps_preview = ", ".join(tech_stack["deps"][:8])
        if len(tech_stack["deps"]) > 8:
            deps_preview += f"  [dim {MUTED}](+{len(tech_stack['deps'])-8} more)[/]"
        lines.append(f"[bold {INK}]Deps:[/] [{MUTED}]{deps_preview}[/]")
    if not lines:
        return None
    return Panel("\n".join(lines), title=f"[bold {INK}]Tech Stack[/]", subtitle=f"[{MUTED}]sheet · tape[/]", box=box.ROUNDED, border_style=INK, padding=(0, 1))


def make_summary_panel(summary: str) -> Panel:
    # Summary is the highlighter — show with signal wash
    return Panel(
        f"[{INK}]{summary}[/]",
        title=f"[bold {INK} on {SIGNAL}] SUMMARY [/]",
        subtitle=f"[{MUTED}]highlighter · signal[/]",
        box=box.ROUNDED,
        border_style=INK,
        padding=(0, 1),
        style=f"on {PAPER}",
    )


def make_ranked_panel(ranked, root: Path, scan_files=None) -> Panel | None:
    if not ranked:
        return Panel("[dim]No Python modules found — nothing to rank.[/]", title=f"[bold {INK}]Start Here[/]", box=box.ROUNDED, border_style=INK)
    t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style=f"bold {INK}", padding=(0, 1), border_style=LINE)
    t.add_column("#", style=MUTED, width=3, justify="right")
    t.add_column("File", style=INK, overflow="fold")
    t.add_column("Score", justify="right", style=GREEN)
    t.add_column("Why", style=MUTED, overflow="fold")
    t.add_column("LOC", justify="right", style=BLUE)
    loc_map: dict[Path, int] = {}
    if scan_files:
        loc_map = {f.path: f.loc for f in scan_files}
    for i, r in enumerate(ranked[:12], 1):
        why = ", ".join(r.reasons[:3])
        loc = str(loc_map.get(r.path, "?"))
        style = f"bold {INK}" if i <= 3 else INK
        # Top 3 get signal tape
        if i == 1:
            why = f"[on {SIGNAL}]{why}[/]"
        t.add_row(f"[{MUTED}]{i}[/]", f"[{style}]{r.rel.as_posix()}[/]", f"[{GREEN}]{r.score:.1f}[/]", f"[{MUTED}]{why}[/]", f"[{BLUE}]{loc}[/]")
    return Panel(t, title=f"[bold {INK}]Start Here ⭐[/]  [dim {MUTED}]({len(ranked)} modules ranked)[/]", subtitle=f"[{MUTED}]sheet · washi tape[/]", box=box.ROUNDED, border_style=INK, padding=(0, 1))


def make_graph_panel(graph: dict[Path, set[Path]], ranked, root: Path) -> Panel | None:
    if not graph:
        return None
    most = sorted(graph.items(), key=lambda kv: len(kv[1]), reverse=True)[:3]
    lines: list[str] = []
    for src, deps in most:
        if not deps:
            continue
        try:
            src_rel = src.relative_to(root).as_posix()
        except ValueError:
            src_rel = src.name
        dep_rels = []
        for d in list(deps)[:3]:
            try:
                dep_rels.append(d.relative_to(root).as_posix())
            except ValueError:
                dep_rels.append(d.name)
        suffix = f" (+{len(deps)-3} more)" if len(deps) > 3 else ""
        lines.append(f"[{BLUE}]{src_rel}[/] [{MUTED}]→[/] [{INK}]{', '.join(dep_rels)}[/][{MUTED}]{suffix}[/]")
    one = ascii_graph(graph, ranked, root)
    if one:
        lines.append(f"[dim {MUTED}]{one}[/]")
    if not lines:
        return None
    return Panel("\n".join(lines), title=f"[bold {INK}]Import Graph[/]  [dim {MUTED}](top hubs → deps)[/]", subtitle=f"[{MUTED}]paper · grid[/]", box=box.ROUNDED, border_style=INK, padding=(0, 1))


def render_static(
    scan_result,
    analyzer_result,
    elapsed: float,
    console: Console,
) -> None:
    """Lab Notebook static render — sheet on graph-paper."""
    root = analyzer_result.root if analyzer_result else scan_result.root
    # Paper frame — washi tape via header subtitle
    console.print(make_header(root, elapsed))
    s = analyzer_result.stats if analyzer_result else scan_result.stats
    trunc = f"  [yellow on {SIGNAL}](truncated)[/]" if s.get("truncated") else ""
    if analyzer_result:
        console.print(
            f"[bold {INK}]{s.get('total_files',0)}[/] files  •  [bold {INK}]{s.get('total_loc',0):,}[/] LOC  •  "
            f"[bold {INK}]{_format_bytes(s.get('total_bytes',0))}[/]  •  "
            f"[{BLUE}]{s.get('graph_nodes',0)}[/] modules  •  [{BLUE}]{s.get('graph_edges',0)}[/] edges{trunc}",
            style=MUTED,
        )
    else:
        console.print(
            f"[bold {INK}]{s['total_files']}[/] files  •  [bold {INK}]{s['total_loc']:,}[/] LOC  •  [bold {INK}]{_format_bytes(s['total_bytes'])}[/]{trunc}",
            style=MUTED,
        )

    # Graph-paper rule
    console.print(f"[{LINE}]────────────────────────────────────────────────[/]")

    lang_panel = make_languages_panel(s)
    if lang_panel:
        console.print(lang_panel)

    if analyzer_result:
        console.print(make_summary_panel(analyzer_result.summary))
        tech = make_tech_stack_panel(analyzer_result.tech_stack, analyzer_result.external_imports)
        if tech:
            console.print(tech)
        ranked_panel = make_ranked_panel(analyzer_result.ranked, analyzer_result.root, scan_result.files)
        if ranked_panel:
            console.print(ranked_panel)
        graph_panel = make_graph_panel(analyzer_result.graph, analyzer_result.ranked, analyzer_result.root)
        if graph_panel:
            console.print(graph_panel)
        if scan_result.files:
            largest = sorted(scan_result.files, key=lambda f: f.loc, reverse=True)[:6]
            t2 = Table(box=box.SIMPLE_HEAD, show_header=True, header_style=f"bold {INK}", padding=(0, 1), border_style=LINE)
            t2.add_column("File", style=INK, overflow="fold")
            t2.add_column("LOC", justify="right", style=GREEN)
            t2.add_column("Lang", style=BLUE)
            t2.add_column("Size", justify="right", style=MUTED)
            for f in largest:
                if f.loc == 0:
                    continue
                t2.add_row(f"[{INK}]{str(f.rel)}[/]", f"[{GREEN}]{str(f.loc)}[/]", f"[{BLUE}]{f.language}[/]", f"[{MUTED}]{_format_bytes(f.size)}[/]")
            if t2.row_count:
                console.print(Panel(t2, title=f"[bold {INK}]Largest Files[/]  [dim {MUTED}](top {t2.row_count})[/]", box=box.ROUNDED, border_style=INK, padding=(0, 1)))
        console.print(f"[dim {MUTED}]Tip: [bold {INK}]peek[/] TUI · [bold {INK}]peek --no-tui[/] static · [bold {INK}]peek --html -o map.html[/] lab sheet[/]")
    else:
        tech = make_tech_stack_panel(scan_result.tech_stack)
        if tech:
            console.print(tech)
        if scan_result.entry_candidates:
            t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style=f"bold {INK}", padding=(0, 1), border_style=LINE)
            t.add_column("#", style=MUTED, width=3, justify="right")
            t.add_column("Entry Candidate", style=INK)
            t.add_column("Reason", style=MUTED)
            for i, p in enumerate(scan_result.entry_candidates, 1):
                try:
                    rel = p.relative_to(scan_result.root)
                except ValueError:
                    rel = p
                reason = "filename" if p.name in ("main.py","app.py","cli.py","__main__.py") else "main guard"
                t.add_row(f"[{MUTED}]{i}[/]", f"[{INK}]{str(rel)}[/]", f"[{MUTED}]{reason}[/]")
            console.print(Panel(t, title=f"[bold {INK}]Start Here ⭐[/]", box=box.ROUNDED, border_style=INK, padding=(0, 1)))


def build_html(scan_result, analyzer_result, elapsed: float) -> str:
    """Lab Notebook HTML export — full sheet on graph-paper.

    Captures Rich render to HTML, then wraps in Lab Notebook chrome
    (tokens, header, marginalia, footer, graph-paper background).
    """
    try:
        from rich.console import Console as RichConsole

        c = RichConsole(record=True, width=100, legacy_windows=False, force_terminal=True, color_system="truecolor")
        render_static(scan_result, analyzer_result, elapsed, c)
        html_fragment = c.export_html(inline_styles=True)
        root = analyzer_result.root if analyzer_result else scan_result.root
        summary = analyzer_result.summary if analyzer_result else "scan"
        # Escape for meta
        import html as _html
        title = f"peek — {root} — Lab Notebook No.01"
        desc = _html.escape(summary[:160])

        # Lab Notebook wrapper — tokens duplicated identically (do not edit values)
        doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light">
<meta name="theme-color" content="#FFD400">
<title>{_html.escape(title)}</title>
<meta name="description" content="{desc}">
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700;12..96,800&family=Instrument+Sans:wght@400;500;600;700&family=Instrument+Serif:ital@0;1&family=Fragment+Mono:ital@0;1&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{{--paper:#FFFEFB;--paper-2:#F3F0E8;--paper-3:#EAE6DA;--sheet:#FFFFFF;--ink:#0B1220;--ink-2:#1A2744;--muted:#6E7D9A;--muted-2:#8A9AB6;--line:#D9E2EF;--line-2:#B9C8E2;--grid:#E3ECFB;--grid-2:#C9D8F0;--signal:#FFD400;--signal-soft:rgba(255,212,0,.18);--red:#E10600;--blue:#0050FF;--green:#0E9F6E;--green-soft:rgba(14,159,110,.10);--mono:'Fragment Mono','JetBrains Mono',monospace;--display:'Bricolage Grotesque',sans-serif;--serif:'Instrument Serif',Georgia,serif;--sans:'Instrument Sans',sans-serif}}
*{{margin:0;padding:0;box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{background:var(--paper);color:var(--ink);font-family:var(--sans);line-height:1.6;background-image:linear-gradient(var(--grid) 1px,transparent 1px),linear-gradient(90deg,var(--grid) 1px,transparent 1px),linear-gradient(var(--grid-2) 1px,transparent 1px),linear-gradient(90deg,var(--grid-2) 1px,transparent 1px);background-size:24px 24px,24px 24px,120px 120px,120px 120px;background-position:-1px -1px}}
.wrap{{max-width:1280px;margin:0 auto;padding:0 clamp(18px,4vw,52px)}}
#prog{{position:fixed;top:0;left:0;height:3px;width:100%;background:var(--signal);transform:scaleX(0);transform-origin:left}}
header{{position:sticky;top:0;z-index:40;background:rgba(255,254,251,.88);backdrop-filter:saturate(150%) blur(10px);border-bottom:1px solid var(--line)}}
.head-top{{display:flex;justify-content:space-between;gap:16px;padding:14px 0 12px;border-bottom:1px dashed var(--line);font-family:var(--mono);font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}}
.head-top b{{color:var(--ink)}}
.head-main{{display:flex;align-items:center;justify-content:space-between;gap:24px;height:56px}}
.logo{{font-family:var(--mono);font-size:13px;display:flex;align-items:center;gap:10px;font-weight:500}}
.logo-mark{{width:28px;height:28px;background:var(--ink);color:var(--paper);display:grid;place-items:center;font-family:var(--mono);font-size:11px;font-weight:600}}
nav{{display:flex;gap:22px}}nav a{{font-family:var(--mono);font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);padding:6px 0;border-bottom:2px solid transparent}}
nav a.active{{color:var(--ink);border-bottom-color:var(--signal);background:rgba(255,212,0,.18)}}
.marginalia{{border-top:1px solid var(--ink);border-bottom:1px solid var(--ink);background:var(--ink);color:#C8D2E6;overflow:hidden;padding:10px 0}}
.marginalia .track{{display:flex;width:max-content;animation:marq 28s linear infinite}}@keyframes marq{{to{{transform:translateX(-50%)}}}}.marginalia .track span{{font-family:var(--mono);font-size:11px;letter-spacing:.14em;text-transform:uppercase;padding:0 18px;white-space:nowrap}}.marginalia .track span.dot{{color:var(--signal)}}
.page{{background:var(--sheet);border:1px solid var(--ink);position:relative;box-shadow:0 1px 0 rgba(11,18,32,.06),0 12px 32px rgba(11,18,32,.06);padding:28px}}
.page::before{{content:"";position:absolute;top:-10px;left:50%;transform:translateX(-50%) rotate(-1.2deg);width:140px;height:18px;background:rgba(255,255,255,.72);border-left:1px solid rgba(0,0,0,.04);border-right:1px solid rgba(0,0,0,.04);box-shadow:0 1px 6px rgba(0,0,0,.08);background-image:repeating-linear-gradient(90deg,transparent 0 6px,rgba(0,0,0,.03) 6px 7px);backdrop-filter:blur(2px)}}
h1{{font-family:var(--display);font-weight:800;letter-spacing:-.045em;line-height:.88;font-size:clamp(2.2rem,5vw,3.2rem);text-transform:uppercase}}
h1 .line2{{position:relative}}h1 .line2::after{{content:"";position:absolute;left:-4px;right:6%;bottom:.18em;height:.32em;background:var(--signal);z-index:0;transform:rotate(-.6deg)}}h1 .line2 span{{position:relative;z-index:1}}
footer{{border-top:2px solid var(--ink);background:var(--paper-2)}}.foot-in{{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;padding:18px 0;font-family:var(--mono);font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}}
.rich-wrap{{margin:18px 0}}.rich-wrap pre{{background:transparent !important}}
@media print{{header,.marginalia,#prog{{display:none !important}}body{{background:#fff;background-image:none}}}}
</style>
</head>
<body>
<div id="prog"></div>
<header>
  <div class="wrap">
    <div class="head-top"><span>Lab Notebook No.01 — <b>peek</b> — htop for codebases</span><span>2026-08-11 · <b>{_html.escape(str(root))}</b> · {elapsed:.2f}s</span></div>
    <div class="head-main">
      <a class="logo" href="#"><span class="logo-mark">◈</span> PEEK <i>/ LAB — 01</i></a>
      <nav><a class="active" href="#">Specimen</a><a href="#">Scan</a><a href="#">Analyze</a></nav>
      <span style="font-family:var(--mono);font-size:11px;letter-spacing:.08em;text-transform:uppercase;border:1px solid var(--green);color:var(--green);padding:6px 10px;background:var(--green-soft)">◉ Lab Verified</span>
    </div>
  </div>
</header>
<div class="marginalia"><div class="track"><span>peek — htop for codebases</span><span class="dot">✦</span><span>Lab Notebook No.01</span><span class="dot">✦</span><span>Graph Paper · Sheet · Tape · Signal</span><span class="dot">✦</span><span>AST + PageRank + Rich + Textual</span><span class="dot">✦</span><span>Zero-config · Offline</span><span class="dot">✦</span></div></div>
<main class="wrap" style="padding:22px 0 32px">
  <div class="page">
    <h1>PEEK <span class="line2"><span>SPECIMEN<span style="color:var(--blue)">_</span></span></span></h1>
    <p style="font-family:var(--serif);font-style:italic;color:var(--muted);margin:10px 0 14px;letter-spacing:-.02em">{desc}</p>
    <div style="font-family:var(--mono);font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);border-top:1px dashed var(--line);padding-top:10px">Lab — 01 · Sheet on Graph-Paper · Washi Tape holds the truth</div>
    <div class="rich-wrap">{html_fragment}</div>
  </div>
</main>
<footer><div class="wrap"><div class="foot-in"><span>peek v{__version__} · Lab Notebook No.01 · <code>pip install peek && peek .</code></span><span>Graph Paper · Sheet · Tape · Signal · Stamp</span></div></div></footer>
<script>addEventListener('scroll',()=>{{const h=document.documentElement.scrollHeight-innerHeight;document.getElementById('prog').style.transform=`scaleX(${{h>0?scrollY/h:0}})`}},{{passive:true}})</script>
</body>
</html>
"""
        return doc
    except Exception as e:
        return f"<html><body><pre>peek html export failed: {e}</pre></body></html>"
