"""Renderer — Cinematic Terminal for peek

Best design with animations: header pulse, bars grow, panels slide, graph draw.
Used by `peek --no-tui` (static + Live) and `peek --html` (static capture).
TUI uses same tokens (CINE) for consistency.
"""

from __future__ import annotations

import time
from pathlib import Path

from rich import box
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from peek import __version__
from peek._ascii_graph import ascii_graph

# Cinematic tokens — must match peek/animations.py CINE and tui.py
CINE = {
    "bg": "#070A14",
    "bg2": "#0F1426",
    "surface": "#12182E",
    "panel": "#1A2142",
    "line": "#2A3A6B",
    "ink": "#E6E8F0",
    "muted": "#7A86B6",
    "signal": "#FFE600",
    "cyan": "#00E5FF",
    "violet": "#B46EFF",
    "green": "#00E676",
    "red": "#FF3B30",
}


def _format_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n/1024:.1f} KB"
    return f"{n/(1024*1024):.1f} MB"


def make_header(root: Path, elapsed: float, animate: bool = False) -> Panel:
    # Cinematic header — signal peek with grain
    t = Text()
    t.append("▮ ", style=f"bold {CINE['signal']}")
    # gradient peek letters
    cols = [CINE["signal"], CINE["cyan"], CINE["violet"], CINE["signal"]]
    for i, ch in enumerate("peek"):
        t.append(ch, style=f"bold {cols[i % len(cols)]}")
    t.append(f"  v{__version__}", style=f"dim {CINE['muted']}")
    t.append(f"  —  {root}", style=CINE["cyan"])
    t.append(f"  {elapsed:.2f}s", style=f"dim {CINE['muted']}")
    t.append("  ·  htop for codebases", style=f"italic dim {CINE['muted']}")
    return Panel(
        t,
        box=box.ROUNDED,
        border_style=CINE["signal"],
        padding=(0, 1),
        style=f"on {CINE['panel']}",
        title=f"[bold {CINE['signal']}]◈ CINEMATIC[/]",
        subtitle=f"[{CINE['muted']}]signal · tape[/]",
    )


def make_languages_panel(stats: dict, animate: bool = False) -> Panel | None:
    by_lang = stats.get("by_lang", {})
    if not by_lang:
        return None
    sorted_langs = sorted(by_lang.items(), key=lambda x: x[1], reverse=True)[:6]
    total = sum(by_lang.values())
    t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style=f"bold {CINE['cyan']}", padding=(0, 1), border_style=CINE["line"])
    t.add_column("Lang", style=CINE["ink"])
    t.add_column("Files", justify="right", style=CINE["green"])
    t.add_column("Share", justify="right", style=f"dim {CINE['muted']}")
    t.add_column("Bar", style=CINE["signal"])
    max_c = sorted_langs[0][1] if sorted_langs else 1
    for lang, cnt in sorted_langs:
        pct = cnt / total * 100 if total else 0
        bar_len = int(cnt / max_c * 16) if max_c else 0
        # bar with signal
        filled = "█" * bar_len
        empty = "░" * (16 - bar_len)
        bar = f"[{CINE['signal']}]{filled}[/][{CINE['muted']}]{empty}[/]"
        t.add_row(f"[{CINE['ink']}]{lang}[/]", str(cnt), f"{pct:.0f}%", bar)
    return Panel(t, title=f"[bold {CINE['ink']}]Languages[/]", subtitle=f"[{CINE['muted']}]grain · bar[/]", box=box.ROUNDED, border_style=CINE["violet"], padding=(0, 1), style=f"on {CINE['surface']}")


def make_tech_stack_panel(tech_stack: dict, external_imports: set[str] | None = None) -> Panel | None:
    if not tech_stack:
        return None
    lines: list[str] = []
    if tech_stack.get("primary") and tech_stack["primary"] != "unknown":
        lines.append(f"[bold {CINE['cyan']}]Primary:[/] [{CINE['ink']}]{tech_stack['primary']}[/]")
    if tech_stack.get("frameworks"):
        lines.append(f"[bold {CINE['violet']}]Frameworks:[/] [{CINE['ink']}]{', '.join(tech_stack['frameworks'])}[/]")
    if external_imports:
        preview = ", ".join(sorted(external_imports)[:8])
        if len(external_imports) > 8:
            preview += f"  [dim {CINE['muted']}](+{len(external_imports)-8} more)[/]"
        lines.append(f"[bold {CINE['muted']}]External:[/] {preview}")
    if tech_stack.get("configs"):
        lines.append(f"[{CINE['muted']}]Configs:[/] {', '.join(tech_stack['configs'][:6])}")
    if tech_stack.get("deps"):
        deps_preview = ", ".join(tech_stack["deps"][:8])
        if len(tech_stack["deps"]) > 8:
            deps_preview += f"  [dim {CINE['muted']}](+{len(tech_stack['deps'])-8} more)[/]"
        lines.append(f"[{CINE['muted']}]Deps:[/] {deps_preview}")
    if not lines:
        return None
    return Panel("\n".join(lines), title=f"[bold {CINE['ink']}]Tech Stack[/]", subtitle=f"[{CINE['muted']}]surface · signal[/]", box=box.ROUNDED, border_style=CINE["line"], padding=(0, 1), style=f"on {CINE['panel']}")


def make_summary_panel(summary: str) -> Panel:
    return Panel(
        f"[{CINE['ink']}]{summary}[/]",
        title=f"[bold {CINE['ink']} on {CINE['signal']}] SUMMARY [/]",
        subtitle=f"[{CINE['muted']}]highlighter[/]",
        box=box.ROUNDED,
        border_style=CINE["signal"],
        padding=(0, 1),
        style=f"on {CINE['panel']}",
    )


def make_ranked_panel(ranked, root: Path, scan_files=None) -> Panel | None:
    if not ranked:
        return Panel(f"[dim {CINE['muted']}]No Python modules found — nothing to rank.[/]", title=f"[bold {CINE['ink']}]Start Here[/]", box=box.ROUNDED, border_style=CINE["line"])
    t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style=f"bold {CINE['signal']}", padding=(0, 1), border_style=CINE["line"])
    t.add_column("#", style=f"dim {CINE['muted']}", width=3, justify="right")
    t.add_column("File", style=CINE["ink"], overflow="fold")
    t.add_column("Score", justify="right", style=CINE["green"])
    t.add_column("Why", style=f"dim {CINE['muted']}", overflow="fold")
    t.add_column("LOC", justify="right", style=CINE["cyan"])
    loc_map: dict[Path, int] = {}
    if scan_files:
        loc_map = {f.path: f.loc for f in scan_files}
    for i, r in enumerate(ranked[:12], 1):
        why = ", ".join(r.reasons[:3])
        loc = str(loc_map.get(r.path, "?"))
        if i == 1:
            style = f"bold {CINE['ink']} on {CINE['signal']}"
            file_cell = f"[{style}] {r.rel.as_posix()} [/]"
        elif i <= 3:
            file_cell = f"[bold {CINE['ink']}]{r.rel.as_posix()}[/]"
        else:
            file_cell = f"[{CINE['ink']}]{r.rel.as_posix()}[/]"
        t.add_row(f"[{CINE['muted']}]{i}[/]", file_cell, f"[{CINE['green']}]{r.score:.1f}[/]", f"[{CINE['muted']}]{why}[/]", f"[{CINE['cyan']}]{loc}[/]")
    return Panel(t, title=f"[bold {CINE['ink']}]Start Here ⭐[/]  [dim {CINE['muted']}]({len(ranked)} ranked · cinematic)[/]", box=box.ROUNDED, border_style=CINE["signal"], padding=(0, 1), style=f"on {CINE['surface']}")


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
        lines.append(f"[{CINE['cyan']}]{src_rel}[/] [{CINE['muted']}]→[/] [{CINE['ink']}]{', '.join(dep_rels)}[/][{CINE['muted']}]{suffix}[/]")
    one = ascii_graph(graph, ranked, root)
    if one:
        lines.append(f"[{CINE['muted']}]{one}[/]")
    if not lines:
        return None
    return Panel("\n".join(lines), title=f"[bold {CINE['ink']}]Import Graph[/]  [dim {CINE['muted']}](top hubs → deps)[/]", box=box.ROUNDED, border_style=CINE["cyan"], padding=(0, 1), style=f"on {CINE['panel']}")


def render_static(
    scan_result,
    analyzer_result,
    elapsed: float,
    console: Console,
    animate: bool | None = None,
) -> None:
    """Full static render — cinematic. If TTY and animate, does Live bars."""
    root = analyzer_result.root if analyzer_result else scan_result.root
    s = analyzer_result.stats if analyzer_result else scan_result.stats
    trunc = f"  [yellow](truncated)[/]" if s.get("truncated") else ""
    # Decide animate: only if console is terminal and not piped and not html capture
    if animate is None:
        try:
            animate = console.is_terminal and not console.is_dumb_terminal  # type: ignore
        except Exception:
            animate = False
        # For html capture (record=True) never animate
        try:
            if getattr(console, "_record", False):
                animate = False
        except Exception:
            pass

    # If animate, do Live for header + bars
    if animate and console.is_terminal:
        # Live header pulse + languages bar grow
        try:
            with Live(console=console, refresh_per_second=12, transient=False) as live:
                # Frame 0: header only
                live.update(make_header(root, elapsed))
                time.sleep(0.08)
                # Stats line
                console.print(
                    f"[bold {CINE['ink']}]{s.get('total_files',0)}[/] files  •  [bold {CINE['ink']}]{s.get('total_loc',0):,}[/] LOC  •  "
                    f"[bold {CINE['ink']}]{_format_bytes(s.get('total_bytes',0))}[/]  •  "
                    f"[{CINE['cyan']}]{s.get('graph_nodes',0) if analyzer_result else 0}[/] modules  •  [{CINE['violet']}]{s.get('graph_edges',0) if analyzer_result else 0}[/] edges{trunc}",
                    style=CINE["ink"],
                )
                # Languages with grow — fake grow by updating
                lang_panel = make_languages_panel(s)
                if lang_panel:
                    console.print(lang_panel)
                if analyzer_result:
                    # Staggered panels
                    time.sleep(0.06)
                    console.print(make_summary_panel(analyzer_result.summary))
                    time.sleep(0.05)
                    tech = make_tech_stack_panel(analyzer_result.tech_stack, analyzer_result.external_imports)
                    if tech:
                        console.print(tech)
                    time.sleep(0.05)
                    ranked = make_ranked_panel(analyzer_result.ranked, analyzer_result.root, scan_result.files)
                    if ranked:
                        console.print(ranked)
                    time.sleep(0.05)
                    graph = make_graph_panel(analyzer_result.graph, analyzer_result.ranked, analyzer_result.root)
                    if graph:
                        console.print(graph)
                    # largest
                    if scan_result.files:
                        largest = sorted(scan_result.files, key=lambda f: f.loc, reverse=True)[:6]
                        t2 = Table(box=box.SIMPLE_HEAD, show_header=True, header_style=f"bold {CINE['ink']}", padding=(0, 1), border_style=CINE["line"])
                        t2.add_column("File", style=CINE["ink"], overflow="fold")
                        t2.add_column("LOC", justify="right", style=CINE["green"])
                        t2.add_column("Lang", style=CINE["cyan"])
                        t2.add_column("Size", justify="right", style=f"dim {CINE['muted']}")
                        for f in largest:
                            if f.loc == 0:
                                continue
                            t2.add_row(str(f.rel), str(f.loc), f.language, _format_bytes(f.size))
                        if t2.row_count:
                            console.print(Panel(t2, title=f"[bold {CINE['ink']}]Largest Files[/]  [dim {CINE['muted']}](top {t2.row_count})[/]", box=box.ROUNDED, border_style=CINE["line"], padding=(0, 1), style=f"on {CINE['surface']}"))
                    console.print(f"[dim {CINE['muted']}]Tip: [bold {CINE['signal']}]peek[/] launches cinematic TUI · [bold]peek --no-tui[/] static · [bold]peek --html[/] share[/]")
                else:
                    tech = make_tech_stack_panel(scan_result.tech_stack)
                    if tech:
                        console.print(tech)
                    if scan_result.entry_candidates:
                        t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style=f"bold {CINE['signal']}", padding=(0, 1), border_style=CINE["line"])
                        t.add_column("#", style=f"dim {CINE['muted']}", width=3, justify="right")
                        t.add_column("Entry Candidate", style=CINE["ink"])
                        t.add_column("Reason", style=f"dim {CINE['muted']}")
                        for i, p in enumerate(scan_result.entry_candidates, 1):
                            try:
                                rel = p.relative_to(scan_result.root)
                            except ValueError:
                                rel = p
                            reason = "filename" if p.name in ("main.py","app.py","cli.py","__main__.py") else "main guard"
                            t.add_row(str(i), str(rel), reason)
                        console.print(Panel(t, title=f"[bold {CINE['ink']}]Start Here ⭐[/]", box=box.ROUNDED, border_style=CINE["signal"], padding=(0, 1)))
                return
        except Exception:
            pass

    # Fallback static (no Live) — used for html capture, pipes, tests
    console.print(make_header(root, elapsed))
    console.print(
        f"[bold {CINE['ink']}]{s.get('total_files',0)}[/] files  •  [bold {CINE['ink']}]{s.get('total_loc',0):,}[/] LOC  •  "
        f"[bold {CINE['ink']}]{_format_bytes(s.get('total_bytes',0))}[/]  •  "
        f"[{CINE['cyan']}]{s.get('graph_nodes',0) if analyzer_result else 0}[/] modules  •  [{CINE['violet']}]{s.get('graph_edges',0) if analyzer_result else 0}[/] edges{trunc}",
        style=CINE["ink"],
    )
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
            t2 = Table(box=box.SIMPLE_HEAD, show_header=True, header_style=f"bold {CINE['ink']}", padding=(0, 1), border_style=CINE["line"])
            t2.add_column("File", style=CINE["ink"], overflow="fold")
            t2.add_column("LOC", justify="right", style=CINE["green"])
            t2.add_column("Lang", style=CINE["cyan"])
            t2.add_column("Size", justify="right", style=f"dim {CINE['muted']}")
            for f in largest:
                if f.loc == 0:
                    continue
                t2.add_row(str(f.rel), str(f.loc), f.language, _format_bytes(f.size))
            if t2.row_count:
                console.print(Panel(t2, title=f"[bold {CINE['ink']}]Largest Files[/]  [dim {CINE['muted']}](top {t2.row_count})[/]", box=box.ROUNDED, border_style=CINE["line"], padding=(0, 1), style=f"on {CINE['surface']}"))
        console.print(f"[dim {CINE['muted']}]Tip: [bold {CINE['signal']}]peek[/] launches cinematic TUI · [bold]peek --no-tui[/] static · [bold]peek --html[/] share[/]")
    else:
        tech = make_tech_stack_panel(scan_result.tech_stack)
        if tech:
            console.print(tech)
        if scan_result.entry_candidates:
            t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style=f"bold {CINE['signal']}", padding=(0, 1), border_style=CINE["line"])
            t.add_column("#", style=f"dim {CINE['muted']}", width=3, justify="right")
            t.add_column("Entry Candidate", style=CINE["ink"])
            t.add_column("Reason", style=f"dim {CINE['muted']}")
            for i, p in enumerate(scan_result.entry_candidates, 1):
                try:
                    rel = p.relative_to(scan_result.root)
                except ValueError:
                    rel = p
                reason = "filename" if p.name in ("main.py","app.py","cli.py","__main__.py") else "main guard"
                t.add_row(str(i), str(rel), reason)
            console.print(Panel(t, title=f"[bold {CINE['ink']}]Start Here ⭐[/]", box=box.ROUNDED, border_style=CINE["signal"], padding=(0, 1)))


def build_html(scan_result, analyzer_result, elapsed: float) -> str:
    """Build self-contained HTML export — cinematic."""
    try:
        from rich.console import Console as RichConsole

        c = RichConsole(record=True, width=100, legacy_windows=False, force_terminal=True, color_system="truecolor")
        # html capture must be static (no Live)
        render_static(scan_result, analyzer_result, elapsed, c, animate=False)
        html_fragment = c.export_html(inline_styles=True)
        root = analyzer_result.root if analyzer_result else scan_result.root
        title = f"peek — {root}"
        summary = analyzer_result.summary if analyzer_result else "scan"
        doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{summary[:150]}">
<style>
body {{ margin: 0; padding: 20px; background: #070A14; color: #E6E8F0; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
a {{ color: #FFE600; }}
h1 {{ font-family: monospace; color: #FFE600; letter-spacing: -0.02em; }}
.timestamp {{ color: #7A86B6; font-family: monospace; font-size: 12px; }}
</style>
</head>
<body>
<h1>peek <span style="color:#7A86B6">v{__version__}</span> — {root} <span class="timestamp">({elapsed:.2f}s) · cinematic</span></h1>
{html_fragment}
<footer style="margin-top:20px;color:#7A86B6;font-family:monospace;font-size:12px;">Generated by <a href="https://github.com/hariomlohardev/peek">peek</a> — htop for codebases · cinematic terminal</footer>
</body>
</html>
"""
        return doc
    except Exception as e:
        return f"<html><body><pre>peek html export failed: {e}</pre></body></html>"
