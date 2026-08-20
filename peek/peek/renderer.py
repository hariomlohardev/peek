"""Renderer — themed for peek

Supports 10 themes via peek.themes. Same layout, only tokens change.
Used by `peek --no-tui` (staggered when TTY) and `peek --html` (static capture).
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from peek import __version__
from peek._ascii_graph import ascii_graph

# Backward compat: ANTHRO remains as default tokens
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


def _tokens(theme: Any | None) -> dict[str, str]:
    if theme is None:
        return ANTHRO
    # Theme dataclass has .tokens dict, but also support plain dict
    if hasattr(theme, "tokens"):
        return theme.tokens  # type: ignore[return-value]
    if isinstance(theme, dict):
        return theme
    return ANTHRO


def _theme_label(theme: Any | None) -> str:
    if theme is None:
        return "anthropic pro"
    if hasattr(theme, "id"):
        return str(getattr(theme, "id"))
    return "anthropic pro"


def _format_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n/1024:.1f} KB"
    return f"{n/(1024*1024):.1f} MB"


def make_header(root: Path, elapsed: float, theme: Any | None = None) -> Panel:
    t = _tokens(theme)
    label = _theme_label(theme)
    txt = Text()
    txt.append("peek", style=f"bold {t['ink']}")
    txt.append(f"  v{__version__}", style=f"dim {t['muted']}")
    txt.append(f"  —  {root}", style=t["accent"])
    txt.append(f"  {elapsed:.2f}s", style=f"dim {t['muted']}")
    return Panel(
        txt,
        box=box.ROUNDED,
        border_style=t["line"],
        padding=(0, 1),
        style=f"on {t['bg2']}",
        title=f"[bold {t['muted']}]{label}[/]",
    )


def make_languages_panel(stats: dict, theme: Any | None = None) -> Panel | None:
    t = _tokens(theme)
    by_lang = stats.get("by_lang", {})
    if not by_lang:
        return None
    sorted_langs = sorted(by_lang.items(), key=lambda x: x[1], reverse=True)[:6]
    total = sum(by_lang.values())
    tbl = Table(box=box.SIMPLE_HEAD, show_header=True, header_style=f"bold {t['muted']}", padding=(0, 1), border_style=t["line"])
    tbl.add_column("Lang", style=t["ink"])
    tbl.add_column("Files", justify="right", style=t["ink"])
    tbl.add_column("Share", justify="right", style=f"dim {t['muted']}")
    tbl.add_column("Bar", style=t["accent"])
    max_c = sorted_langs[0][1] if sorted_langs else 1
    for lang, cnt in sorted_langs:
        pct = cnt / total * 100 if total else 0
        bar_len = int(cnt / max_c * 14) if max_c else 0
        filled = "█" * bar_len
        empty = "░" * (14 - bar_len)
        bar = f"[{t['accent']}]{filled}[/][{t['muted']}]{empty}[/]"
        tbl.add_row(lang, str(cnt), f"{pct:.0f}%", bar)
    return Panel(tbl, title=f"[bold {t['ink']}]Languages[/]", box=box.ROUNDED, border_style=t["line"], padding=(0, 1), style=f"on {t['surface']}")


def make_tech_stack_panel(tech_stack: dict, external_imports: set[str] | None = None, theme: Any | None = None) -> Panel | None:
    t = _tokens(theme)
    if not tech_stack:
        return None
    lines: list[str] = []
    if tech_stack.get("primary") and tech_stack["primary"] != "unknown":
        lines.append(f"[bold {t['ink']}]Primary:[/] {tech_stack['primary']}")
    if tech_stack.get("frameworks"):
        lines.append(f"[{t['muted']}]Frameworks:[/] {', '.join(tech_stack['frameworks'])}")
    if external_imports:
        preview = ", ".join(sorted(external_imports)[:8])
        if len(external_imports) > 8:
            preview += f"  [dim {t['muted']}](+{len(external_imports)-8} more)[/]"
        lines.append(f"[dim {t['muted']}]External:[/] {preview}")
    if tech_stack.get("configs"):
        lines.append(f"[dim {t['muted']}]Configs:[/] {', '.join(tech_stack['configs'][:6])}")
    if tech_stack.get("deps"):
        deps_preview = ", ".join(tech_stack["deps"][:8])
        if len(tech_stack["deps"]) > 8:
            deps_preview += f"  [dim {t['muted']}](+{len(tech_stack['deps'])-8} more)[/]"
        lines.append(f"[dim {t['muted']}]Deps:[/] {deps_preview}")
    if not lines:
        return None
    return Panel("\n".join(lines), title=f"[bold {t['ink']}]Tech Stack[/]", box=box.ROUNDED, border_style=t["line"], padding=(0, 1), style=f"on {t['panel']}")


def make_summary_panel(summary: str, theme: Any | None = None) -> Panel:
    t = _tokens(theme)
    return Panel(
        f"[{t['ink']}]{summary}[/]",
        title=f"[bold {t['ink']}]Summary[/]",
        box=box.ROUNDED,
        border_style=t["line"],
        padding=(0, 1),
        style=f"on {t['panel']}",
    )


def make_ranked_panel(ranked, root: Path, scan_files=None, theme: Any | None = None) -> Panel | None:
    t = _tokens(theme)
    if not ranked:
        return Panel(f"[dim {t['muted']}]No Python modules found — nothing to rank.[/]", title=f"[bold {t['ink']}]Start Here[/]", box=box.ROUNDED, border_style=t["line"])
    tbl = Table(box=box.SIMPLE_HEAD, show_header=True, header_style=f"bold {t['muted']}", padding=(0, 1), border_style=t["line"])
    tbl.add_column("#", style=f"dim {t['muted']}", width=3, justify="right")
    tbl.add_column("File", style=t["ink"], overflow="fold")
    tbl.add_column("Score", justify="right", style=t["accent"])
    tbl.add_column("Why", style=f"dim {t['muted']}", overflow="fold")
    tbl.add_column("LOC", justify="right", style=t["cyan"])
    loc_map: dict[Path, int] = {}
    if scan_files:
        loc_map = {f.path: f.loc for f in scan_files}
    for i, r in enumerate(ranked[:12], 1):
        why = ", ".join(r.reasons[:3])
        loc = str(loc_map.get(r.path, "?"))
        tbl.add_row(f"[dim {t['muted']}]{i}[/]", f"[{t['ink']}]{r.rel.as_posix()}[/]", f"[{t['accent']}]{r.score:.1f}[/]", f"[{t['muted']}]{why}[/]", f"[{t['cyan']}]{loc}[/]")
    return Panel(tbl, title=f"[bold {t['ink']}]Start Here[/]  [dim {t['muted']}]({len(ranked)} ranked)[/]", box=box.ROUNDED, border_style=t["line"], padding=(0, 1), style=f"on {t['surface']}")


def make_graph_panel(graph: dict[Path, set[Path]], ranked, root: Path, theme: Any | None = None) -> Panel | None:
    t = _tokens(theme)
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
        lines.append(f"[{t['cyan']}]{src_rel}[/] [{t['muted']}]→[/] {', '.join(dep_rels)}{suffix}")
    one = ascii_graph(graph, ranked, root)
    if one:
        lines.append(f"[{t['muted']}]{one}[/]")
    if not lines:
        return None
    return Panel("\n".join(lines), title=f"[bold {t['ink']}]Import Graph[/]", box=box.ROUNDED, border_style=t["line"], padding=(0, 1), style=f"on {t['panel']}")


def render_static(
    scan_result,
    analyzer_result,
    elapsed: float,
    console: Console,
    animate: bool | None = None,
    theme: Any | None = None,
) -> None:
    """Themed static — subtle staggered reveal when TTY."""
    if os.getenv("NO_COLOR"):
        console.no_color = True
    t = _tokens(theme)
    root = analyzer_result.root if analyzer_result else scan_result.root
    s = analyzer_result.stats if analyzer_result else scan_result.stats
    trunc = f"  [dim {t['muted']}](truncated)[/]" if s.get("truncated") else ""
    if animate is None:
        try:
            animate = console.is_terminal and not getattr(console, "_record", False)
        except Exception:
            animate = False

    if animate and console.is_terminal:
        try:
            console.print(make_header(root, elapsed, theme))
            time.sleep(0.04)
            console.print(
                f"[bold {t['ink']}]{s.get('total_files',0)}[/] files  •  [bold {t['ink']}]{s.get('total_loc',0):,}[/] LOC  •  "
                f"[bold {t['ink']}]{_format_bytes(s.get('total_bytes',0))}[/]  •  "
                f"[{t['cyan']}]{s.get('graph_nodes',0) if analyzer_result else 0}[/] modules  •  [{t['muted']}]{s.get('graph_edges',0) if analyzer_result else 0}[/] edges{trunc}",
            )
            lp = make_languages_panel(s, theme)
            if lp:
                time.sleep(0.03)
                console.print(lp)
            if analyzer_result:
                time.sleep(0.03)
                console.print(make_summary_panel(analyzer_result.summary, theme))
                time.sleep(0.03)
                tech = make_tech_stack_panel(analyzer_result.tech_stack, analyzer_result.external_imports, theme)
                if tech:
                    console.print(tech)
                time.sleep(0.03)
                ranked = make_ranked_panel(analyzer_result.ranked, analyzer_result.root, scan_result.files, theme)
                if ranked:
                    console.print(ranked)
                time.sleep(0.03)
                graph = make_graph_panel(analyzer_result.graph, analyzer_result.ranked, analyzer_result.root, theme)
                if graph:
                    console.print(graph)
                if scan_result.files:
                    largest = sorted(scan_result.files, key=lambda f: f.loc, reverse=True)[:6]
                    t2 = Table(box=box.SIMPLE_HEAD, show_header=True, header_style=f"bold {t['muted']}", padding=(0, 1), border_style=t["line"])
                    t2.add_column("File", style=t["ink"], overflow="fold")
                    t2.add_column("LOC", justify="right", style=t["accent"])
                    t2.add_column("Lang", style=t["cyan"])
                    t2.add_column("Size", justify="right", style=f"dim {t['muted']}")
                    for f in largest:
                        if f.loc == 0:
                            continue
                        t2.add_row(str(f.rel), str(f.loc), f.language, _format_bytes(f.size))
                    if t2.row_count:
                        time.sleep(0.02)
                        console.print(Panel(t2, title=f"[bold {t['ink']}]Largest Files[/]", box=box.ROUNDED, border_style=t["line"], padding=(0, 1), style=f"on {t['surface']}"))
                time.sleep(0.02)
                console.print(f"[dim {t['muted']}]Tip: [bold {t['ink']}]peek[/] { _theme_label(theme)} · [bold]peek --no-tui[/] static · [bold]peek --html[/] share[/]")
            else:
                tech = make_tech_stack_panel(scan_result.tech_stack, theme=theme)
                if tech:
                    time.sleep(0.02)
                    console.print(tech)
            return
        except Exception:
            pass

    # Fallback static
    console.print(make_header(root, elapsed, theme))
    console.print(
        f"[bold {t['ink']}]{s.get('total_files',0)}[/] files  •  [bold {t['ink']}]{s.get('total_loc',0):,}[/] LOC  •  "
        f"[bold {t['ink']}]{_format_bytes(s.get('total_bytes',0))}[/]  •  "
        f"[{t['cyan']}]{s.get('graph_nodes',0) if analyzer_result else 0}[/] modules  •  [{t['muted']}]{s.get('graph_edges',0) if analyzer_result else 0}[/] edges{trunc}",
    )
    lp = make_languages_panel(s, theme)
    if lp:
        console.print(lp)
    if analyzer_result:
        console.print(make_summary_panel(analyzer_result.summary, theme))
        tech = make_tech_stack_panel(analyzer_result.tech_stack, analyzer_result.external_imports, theme)
        if tech:
            console.print(tech)
        ranked = make_ranked_panel(analyzer_result.ranked, analyzer_result.root, scan_result.files, theme)
        if ranked:
            console.print(ranked)
        graph = make_graph_panel(analyzer_result.graph, analyzer_result.ranked, analyzer_result.root, theme)
        if graph:
            console.print(graph)
        if scan_result.files:
            largest = sorted(scan_result.files, key=lambda f: f.loc, reverse=True)[:6]
            t2 = Table(box=box.SIMPLE_HEAD, show_header=True, header_style=f"bold {t['muted']}", padding=(0, 1), border_style=t["line"])
            t2.add_column("File", style=t["ink"], overflow="fold")
            t2.add_column("LOC", justify="right", style=t["accent"])
            t2.add_column("Lang", style=t["cyan"])
            t2.add_column("Size", justify="right", style=f"dim {t['muted']}")
            for f in largest:
                if f.loc == 0:
                    continue
                t2.add_row(str(f.rel), str(f.loc), f.language, _format_bytes(f.size))
            if t2.row_count:
                console.print(Panel(t2, title=f"[bold {t['ink']}]Largest Files[/]", box=box.ROUNDED, border_style=t["line"], padding=(0, 1), style=f"on {t['surface']}"))
        console.print(f"[dim {t['muted']}]Tip: [bold {t['ink']}]peek[/] {_theme_label(theme)} · [bold]peek --no-tui[/] static · [bold]peek --html[/] share[/]")
    else:
        tech = make_tech_stack_panel(scan_result.tech_stack, theme=theme)
        if tech:
            console.print(tech)
        if scan_result.entry_candidates:
            tbl = Table(box=box.SIMPLE_HEAD, show_header=True, header_style=f"bold {t['muted']}", padding=(0, 1), border_style=t["line"])
            tbl.add_column("#", style=f"dim {t['muted']}", width=3, justify="right")
            tbl.add_column("Entry Candidate", style=t["ink"])
            tbl.add_column("Reason", style=f"dim {t['muted']}")
            for i, p in enumerate(scan_result.entry_candidates, 1):
                try:
                    rel = p.relative_to(scan_result.root)
                except ValueError:
                    rel = p
                reason = "filename" if p.name in ("main.py","app.py","cli.py","__main__.py") else "main guard"
                tbl.add_row(str(i), str(rel), reason)
            console.print(Panel(tbl, title=f"[bold {t['ink']}]Start Here[/]", box=box.ROUNDED, border_style=t["line"], padding=(0, 1)))


def build_html(scan_result, analyzer_result, elapsed: float, theme: Any | None = None) -> str:
    try:
        from rich.console import Console as RichConsole

        c = RichConsole(record=True, width=100, legacy_windows=False, force_terminal=True, color_system="truecolor")
        render_static(scan_result, analyzer_result, elapsed, c, animate=False, theme=theme)
        html_fragment = c.export_html(inline_styles=True)
        root = analyzer_result.root if analyzer_result else scan_result.root
        title = f"peek — {root}"
        summary = analyzer_result.summary if analyzer_result else "scan"
        t = _tokens(theme)
        label = _theme_label(theme)
        doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{summary[:150]}">
<style>
body {{ margin: 0; padding: 24px; background: {t['bg']}; color: {t['ink']}; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
a {{ color: {t['accent']}; }}
h1 {{ font-family: monospace; color: {t['ink']}; font-weight: 600; letter-spacing: -0.02em; }}
.timestamp {{ color: {t['muted']}; font-size: 12px; }}
</style>
</head>
<body>
<h1>peek <span style="color:{t['muted']}">v{__version__}</span> — {root} <span class="timestamp">({elapsed:.2f}s) · {label}</span></h1>
{html_fragment}
<footer style="margin-top:24px;color:{t['muted']};font-family:monospace;font-size:12px;">Generated by <a href="https://github.com/hariomlohardev/peek">peek</a> — htop for codebases · {label}</footer>
</body>
</html>
"""
        return doc
    except Exception as e:
        return f"<html><body><pre>peek html export failed: {e}</pre></body></html>"
