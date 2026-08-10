"""Renderer — Anthropic Pro for peek

Professional, warm, editorial. Subtle animations: bars grow, panels fade.
Used by `peek --no-tui` (Live when TTY) and `peek --html` (static capture).
"""

from __future__ import annotations

import time
from pathlib import Path

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from peek import __version__
from peek._ascii_graph import ascii_graph

ANTHRO = {
    "bg": "#141413",
    "bg2": "#1C1C19",
    "surface": "#232320",
    "panel": "#2A2A27",
    "line": "#3A3936",
    "ink": "#E8E6E3",
    "muted": "#9A9590",
    "accent": "#D4A27F",
    "cyan": "#8AB4B8",
    "violet": "#9A8FBF",
    "green": "#8BA888",
}


def _format_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n/1024:.1f} KB"
    return f"{n/(1024*1024):.1f} MB"


def make_header(root: Path, elapsed: float) -> Panel:
    t = Text()
    t.append("peek", style=f"bold {ANTHRO['ink']}")
    t.append(f"  v{__version__}", style=f"dim {ANTHRO['muted']}")
    t.append(f"  —  {root}", style=ANTHRO["accent"])
    t.append(f"  {elapsed:.2f}s", style=f"dim {ANTHRO['muted']}")
    return Panel(
        t,
        box=box.ROUNDED,
        border_style=ANTHRO["line"],
        padding=(0, 1),
        style=f"on {ANTHRO['bg2']}",
        title=f"[bold {ANTHRO['muted']}]anthropic pro[/]",
    )


def make_languages_panel(stats: dict) -> Panel | None:
    by_lang = stats.get("by_lang", {})
    if not by_lang:
        return None
    sorted_langs = sorted(by_lang.items(), key=lambda x: x[1], reverse=True)[:6]
    total = sum(by_lang.values())
    t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style=f"bold {ANTHRO['muted']}", padding=(0, 1), border_style=ANTHRO["line"])
    t.add_column("Lang", style=ANTHRO["ink"])
    t.add_column("Files", justify="right", style=ANTHRO["ink"])
    t.add_column("Share", justify="right", style=f"dim {ANTHRO['muted']}")
    t.add_column("Bar", style=ANTHRO["accent"])
    max_c = sorted_langs[0][1] if sorted_langs else 1
    for lang, cnt in sorted_langs:
        pct = cnt / total * 100 if total else 0
        bar_len = int(cnt / max_c * 14) if max_c else 0
        filled = "█" * bar_len
        empty = "░" * (14 - bar_len)
        bar = f"[{ANTHRO['accent']}]{filled}[/][{ANTHRO['muted']}]{empty}[/]"
        t.add_row(lang, str(cnt), f"{pct:.0f}%", bar)
    return Panel(t, title=f"[bold {ANTHRO['ink']}]Languages[/]", box=box.ROUNDED, border_style=ANTHRO["line"], padding=(0, 1), style=f"on {ANTHRO['surface']}")


def make_tech_stack_panel(tech_stack: dict, external_imports: set[str] | None = None) -> Panel | None:
    if not tech_stack:
        return None
    lines: list[str] = []
    if tech_stack.get("primary") and tech_stack["primary"] != "unknown":
        lines.append(f"[bold {ANTHRO['ink']}]Primary:[/] {tech_stack['primary']}")
    if tech_stack.get("frameworks"):
        lines.append(f"[{ANTHRO['muted']}]Frameworks:[/] {', '.join(tech_stack['frameworks'])}")
    if external_imports:
        preview = ", ".join(sorted(external_imports)[:8])
        if len(external_imports) > 8:
            preview += f"  [dim {ANTHRO['muted']}](+{len(external_imports)-8} more)[/]"
        lines.append(f"[dim {ANTHRO['muted']}]External:[/] {preview}")
    if tech_stack.get("configs"):
        lines.append(f"[dim {ANTHRO['muted']}]Configs:[/] {', '.join(tech_stack['configs'][:6])}")
    if tech_stack.get("deps"):
        deps_preview = ", ".join(tech_stack["deps"][:8])
        if len(tech_stack["deps"]) > 8:
            deps_preview += f"  [dim {ANTHRO['muted']}](+{len(tech_stack['deps'])-8} more)[/]"
        lines.append(f"[dim {ANTHRO['muted']}]Deps:[/] {deps_preview}")
    if not lines:
        return None
    return Panel("\n".join(lines), title=f"[bold {ANTHRO['ink']}]Tech Stack[/]", box=box.ROUNDED, border_style=ANTHRO["line"], padding=(0, 1), style=f"on {ANTHRO['panel']}")


def make_summary_panel(summary: str) -> Panel:
    return Panel(
        f"[{ANTHRO['ink']}]{summary}[/]",
        title=f"[bold {ANTHRO['ink']}]Summary[/]",
        box=box.ROUNDED,
        border_style=ANTHRO["line"],
        padding=(0, 1),
        style=f"on {ANTHRO['panel']}",
    )


def make_ranked_panel(ranked, root: Path, scan_files=None) -> Panel | None:
    if not ranked:
        return Panel(f"[dim {ANTHRO['muted']}]No Python modules found — nothing to rank.[/]", title=f"[bold {ANTHRO['ink']}]Start Here[/]", box=box.ROUNDED, border_style=ANTHRO["line"])
    t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style=f"bold {ANTHRO['muted']}", padding=(0, 1), border_style=ANTHRO["line"])
    t.add_column("#", style=f"dim {ANTHRO['muted']}", width=3, justify="right")
    t.add_column("File", style=ANTHRO["ink"], overflow="fold")
    t.add_column("Score", justify="right", style=ANTHRO["accent"])
    t.add_column("Why", style=f"dim {ANTHRO['muted']}", overflow="fold")
    t.add_column("LOC", justify="right", style=ANTHRO["cyan"])
    loc_map: dict[Path, int] = {}
    if scan_files:
        loc_map = {f.path: f.loc for f in scan_files}
    for i, r in enumerate(ranked[:12], 1):
        why = ", ".join(r.reasons[:3])
        loc = str(loc_map.get(r.path, "?"))
        # Professional: no highlight wash, just muted number
        t.add_row(f"[dim {ANTHRO['muted']}]{i}[/]", f"[{ANTHRO['ink']}]{r.rel.as_posix()}[/]", f"[{ANTHRO['accent']}]{r.score:.1f}[/]", f"[{ANTHRO['muted']}]{why}[/]", f"[{ANTHRO['cyan']}]{loc}[/]")
    return Panel(t, title=f"[bold {ANTHRO['ink']}]Start Here[/]  [dim {ANTHRO['muted']}]({len(ranked)} ranked)[/]", box=box.ROUNDED, border_style=ANTHRO["line"], padding=(0, 1), style=f"on {ANTHRO['surface']}")


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
        lines.append(f"[{ANTHRO['cyan']}]{src_rel}[/] [{ANTHRO['muted']}]→[/] {', '.join(dep_rels)}{suffix}")
    one = ascii_graph(graph, ranked, root)
    if one:
        lines.append(f"[{ANTHRO['muted']}]{one}[/]")
    if not lines:
        return None
    return Panel("\n".join(lines), title=f"[bold {ANTHRO['ink']}]Import Graph[/]", box=box.ROUNDED, border_style=ANTHRO["line"], padding=(0, 1), style=f"on {ANTHRO['panel']}")


def render_static(
    scan_result,
    analyzer_result,
    elapsed: float,
    console: Console,
    animate: bool | None = None,
) -> None:
    """Anthropic Pro static — subtle staggered reveal when TTY."""
    root = analyzer_result.root if analyzer_result else scan_result.root
    s = analyzer_result.stats if analyzer_result else scan_result.stats
    trunc = f"  [dim {ANTHRO['muted']}](truncated)[/]" if s.get("truncated") else ""
    if animate is None:
        try:
            animate = console.is_terminal and not getattr(console, "_record", False)
        except Exception:
            animate = False

    # Anthropic-style: no flashy Live — just a gentle 40–60ms stagger between panels
    # when on a real terminal. Feels precise, not viral.
    if animate and console.is_terminal:
        try:
            console.print(make_header(root, elapsed))
            time.sleep(0.04)
            console.print(
                f"[bold {ANTHRO['ink']}]{s.get('total_files',0)}[/] files  •  [bold {ANTHRO['ink']}]{s.get('total_loc',0):,}[/] LOC  •  "
                f"[bold {ANTHRO['ink']}]{_format_bytes(s.get('total_bytes',0))}[/]  •  "
                f"[{ANTHRO['cyan']}]{s.get('graph_nodes',0) if analyzer_result else 0}[/] modules  •  [{ANTHRO['muted']}]{s.get('graph_edges',0) if analyzer_result else 0}[/] edges{trunc}",
            )
            lp = make_languages_panel(s)
            if lp:
                time.sleep(0.03)
                console.print(lp)
            if analyzer_result:
                time.sleep(0.03)
                console.print(make_summary_panel(analyzer_result.summary))
                time.sleep(0.03)
                tech = make_tech_stack_panel(analyzer_result.tech_stack, analyzer_result.external_imports)
                if tech:
                    console.print(tech)
                time.sleep(0.03)
                ranked = make_ranked_panel(analyzer_result.ranked, analyzer_result.root, scan_result.files)
                if ranked:
                    console.print(ranked)
                time.sleep(0.03)
                graph = make_graph_panel(analyzer_result.graph, analyzer_result.ranked, analyzer_result.root)
                if graph:
                    console.print(graph)
                if scan_result.files:
                    largest = sorted(scan_result.files, key=lambda f: f.loc, reverse=True)[:6]
                    t2 = Table(box=box.SIMPLE_HEAD, show_header=True, header_style=f"bold {ANTHRO['muted']}", padding=(0, 1), border_style=ANTHRO["line"])
                    t2.add_column("File", style=ANTHRO["ink"], overflow="fold")
                    t2.add_column("LOC", justify="right", style=ANTHRO["accent"])
                    t2.add_column("Lang", style=ANTHRO["cyan"])
                    t2.add_column("Size", justify="right", style=f"dim {ANTHRO['muted']}")
                    for f in largest:
                        if f.loc == 0:
                            continue
                        t2.add_row(str(f.rel), str(f.loc), f.language, _format_bytes(f.size))
                    if t2.row_count:
                        time.sleep(0.02)
                        console.print(Panel(t2, title=f"[bold {ANTHRO['ink']}]Largest Files[/]", box=box.ROUNDED, border_style=ANTHRO["line"], padding=(0, 1), style=f"on {ANTHRO['surface']}"))
                time.sleep(0.02)
                console.print(f"[dim {ANTHRO['muted']}]Tip: [bold {ANTHRO['ink']}]peek[/] pro TUI · [bold]peek --no-tui[/] static · [bold]peek --html[/] share[/]")
            else:
                tech = make_tech_stack_panel(scan_result.tech_stack)
                if tech:
                    time.sleep(0.02)
                    console.print(tech)
            return
        except Exception:
            pass

    # Fallback static
    console.print(make_header(root, elapsed))
    console.print(
        f"[bold {ANTHRO['ink']}]{s.get('total_files',0)}[/] files  •  [bold {ANTHRO['ink']}]{s.get('total_loc',0):,}[/] LOC  •  "
        f"[bold {ANTHRO['ink']}]{_format_bytes(s.get('total_bytes',0))}[/]  •  "
        f"[{ANTHRO['cyan']}]{s.get('graph_nodes',0) if analyzer_result else 0}[/] modules  •  [{ANTHRO['muted']}]{s.get('graph_edges',0) if analyzer_result else 0}[/] edges{trunc}",
    )
    lp = make_languages_panel(s)
    if lp:
        console.print(lp)
    if analyzer_result:
        console.print(make_summary_panel(analyzer_result.summary))
        tech = make_tech_stack_panel(analyzer_result.tech_stack, analyzer_result.external_imports)
        if tech:
            console.print(tech)
        ranked = make_ranked_panel(analyzer_result.ranked, analyzer_result.root, scan_result.files)
        if ranked:
            console.print(ranked)
        graph = make_graph_panel(analyzer_result.graph, analyzer_result.ranked, analyzer_result.root)
        if graph:
            console.print(graph)
        if scan_result.files:
            largest = sorted(scan_result.files, key=lambda f: f.loc, reverse=True)[:6]
            t2 = Table(box=box.SIMPLE_HEAD, show_header=True, header_style=f"bold {ANTHRO['muted']}", padding=(0, 1), border_style=ANTHRO["line"])
            t2.add_column("File", style=ANTHRO["ink"], overflow="fold")
            t2.add_column("LOC", justify="right", style=ANTHRO["accent"])
            t2.add_column("Lang", style=ANTHRO["cyan"])
            t2.add_column("Size", justify="right", style=f"dim {ANTHRO['muted']}")
            for f in largest:
                if f.loc == 0:
                    continue
                t2.add_row(str(f.rel), str(f.loc), f.language, _format_bytes(f.size))
            if t2.row_count:
                console.print(Panel(t2, title=f"[bold {ANTHRO['ink']}]Largest Files[/]", box=box.ROUNDED, border_style=ANTHRO["line"], padding=(0, 1), style=f"on {ANTHRO['surface']}"))
        console.print(f"[dim {ANTHRO['muted']}]Tip: [bold {ANTHRO['ink']}]peek[/] pro TUI · [bold]peek --no-tui[/] static · [bold]peek --html[/] share[/]")
    else:
        tech = make_tech_stack_panel(scan_result.tech_stack)
        if tech:
            console.print(tech)
        if scan_result.entry_candidates:
            t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style=f"bold {ANTHRO['muted']}", padding=(0, 1), border_style=ANTHRO["line"])
            t.add_column("#", style=f"dim {ANTHRO['muted']}", width=3, justify="right")
            t.add_column("Entry Candidate", style=ANTHRO["ink"])
            t.add_column("Reason", style=f"dim {ANTHRO['muted']}")
            for i, p in enumerate(scan_result.entry_candidates, 1):
                try:
                    rel = p.relative_to(scan_result.root)
                except ValueError:
                    rel = p
                reason = "filename" if p.name in ("main.py","app.py","cli.py","__main__.py") else "main guard"
                t.add_row(str(i), str(rel), reason)
            console.print(Panel(t, title=f"[bold {ANTHRO['ink']}]Start Here[/]", box=box.ROUNDED, border_style=ANTHRO["line"], padding=(0, 1)))


def build_html(scan_result, analyzer_result, elapsed: float) -> str:
    try:
        from rich.console import Console as RichConsole

        c = RichConsole(record=True, width=100, legacy_windows=False, force_terminal=True, color_system="truecolor")
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
body {{ margin: 0; padding: 24px; background: #141413; color: #E8E6E3; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
a {{ color: #D4A27F; }}
h1 {{ font-family: monospace; color: #E8E6E3; font-weight: 600; letter-spacing: -0.02em; }}
.timestamp {{ color: #9A9590; font-size: 12px; }}
</style>
</head>
<body>
<h1>peek <span style="color:#9A9590">v{__version__}</span> — {root} <span class="timestamp">({elapsed:.2f}s) · anthropic pro</span></h1>
{html_fragment}
<footer style="margin-top:24px;color:#9A9590;font-family:monospace;font-size:12px;">Generated by <a href="https://github.com/hariomlohardev/peek">peek</a> — htop for codebases · anthropic pro</footer>
</body>
</html>
"""
        return doc
    except Exception as e:
        return f"<html><body><pre>peek html export failed: {e}</pre></body></html>"
