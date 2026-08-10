"""Renderer — static Rich output for peek.

Day 3 scope: beautiful `peek .` static mode (pipeable, screenshot-ready).
Used by both `peek scan`/`peek analyze` and `peek --no-tui`.

Keeps Rich panels centralized so TUI and CLI share style.
"""

from __future__ import annotations

from pathlib import Path

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from peek import __version__
from peek._ascii_graph import ascii_graph


def _format_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n/1024:.1f} KB"
    return f"{n/(1024*1024):.1f} MB"


def make_header(root: Path, elapsed: float) -> Panel:
    header = Text()
    header.append("peek", style="bold magenta")
    header.append(f"  v{__version__}", style="dim")
    header.append(f"  —  {root}", style="cyan")
    header.append(f"  ({elapsed:.2f}s)", style="dim")
    return Panel(header, box=box.ROUNDED, border_style="magenta", padding=(0, 1))


def make_languages_panel(stats: dict) -> Panel | None:
    by_lang = stats.get("by_lang", {})
    if not by_lang:
        return None
    sorted_langs = sorted(by_lang.items(), key=lambda x: x[1], reverse=True)[:6]
    total = sum(by_lang.values())
    t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold cyan", padding=(0, 1))
    t.add_column("Language", style="white")
    t.add_column("Files", justify="right", style="green")
    t.add_column("Share", justify="right", style="dim")
    t.add_column("Bar", style="magenta")
    max_count = sorted_langs[0][1] if sorted_langs else 1
    for lang, count in sorted_langs:
        pct = count / total * 100 if total else 0
        bar_len = int(count / max_count * 16) if max_count else 0
        bar = "█" * bar_len + "░" * (16 - bar_len)
        t.add_row(lang, str(count), f"{pct:.0f}%", bar)
    return Panel(t, title="[bold]Languages[/]", box=box.ROUNDED, border_style="cyan", padding=(0, 1))


def make_tech_stack_panel(tech_stack: dict, external_imports: set[str] | None = None) -> Panel | None:
    if not tech_stack:
        return None
    lines: list[str] = []
    if tech_stack.get("primary") and tech_stack["primary"] != "unknown":
        lines.append(f"[bold cyan]Primary:[/] {tech_stack['primary']}")
    if tech_stack.get("frameworks"):
        lines.append(f"[bold cyan]Frameworks:[/] {', '.join(tech_stack['frameworks'])}")
    if external_imports:
        preview = ", ".join(sorted(external_imports)[:8])
        if len(external_imports) > 8:
            preview += f"  [dim](+{len(external_imports)-8} more)[/]"
        lines.append(f"[bold cyan]External:[/] {preview}")
    if tech_stack.get("configs"):
        lines.append(f"[bold cyan]Configs:[/] {', '.join(tech_stack['configs'][:6])}")
    if tech_stack.get("deps"):
        deps_preview = ", ".join(tech_stack["deps"][:8])
        if len(tech_stack["deps"]) > 8:
            deps_preview += f"  [dim](+{len(tech_stack['deps'])-8} more)[/]"
        lines.append(f"[bold cyan]Deps:[/] {deps_preview}")
    if not lines:
        return None
    return Panel("\n".join(lines), title="[bold]Tech Stack[/]", box=box.ROUNDED, border_style="green", padding=(0, 1))


def make_summary_panel(summary: str) -> Panel:
    return Panel(summary, title="[bold]Summary[/]", box=box.ROUNDED, border_style="green", padding=(0, 1))


def make_ranked_panel(ranked, root: Path, scan_files=None) -> Panel | None:
    if not ranked:
        return Panel("[dim]No Python modules found — nothing to rank.[/]", title="[bold]Start Here[/]", box=box.ROUNDED, border_style="yellow")
    t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold yellow", padding=(0, 1))
    t.add_column("#", style="dim", width=3, justify="right")
    t.add_column("File", style="white", overflow="fold")
    t.add_column("Score", justify="right", style="green")
    t.add_column("Why", style="dim", overflow="fold")
    t.add_column("LOC", justify="right", style="cyan")
    # map path -> loc
    loc_map: dict[Path, int] = {}
    if scan_files:
        loc_map = {f.path: f.loc for f in scan_files}
    for i, r in enumerate(ranked[:12], 1):
        why = ", ".join(r.reasons[:3])
        loc = str(loc_map.get(r.path, "?"))
        style = "bold white" if i <= 3 else "white"
        t.add_row(str(i), f"[{style}]{r.rel.as_posix()}[/]", f"{r.score:.1f}", why, loc)
    return Panel(t, title=f"[bold]Start Here ⭐[/]  [dim]({len(ranked)} modules ranked)[/]", box=box.ROUNDED, border_style="yellow", padding=(0, 1))


def make_graph_panel(graph: dict[Path, set[Path]], ranked, root: Path) -> Panel | None:
    if not graph:
        return None
    # top hubs
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
        lines.append(f"[cyan]{src_rel}[/] → {', '.join(dep_rels)}{suffix}")
    # also show ascii one-liner
    one = ascii_graph(graph, ranked, root)
    if one:
        lines.append(f"[dim]{one}[/]")
    if not lines:
        return None
    return Panel("\n".join(lines), title="[bold]Import Graph[/]  [dim](top hubs → deps)[/]", box=box.ROUNDED, border_style="white", padding=(0, 1))


def render_static(
    scan_result,
    analyzer_result,
    elapsed: float,
    console: Console,
) -> None:
    """Full static render — used by `peek --no-tui` and Day 3 default fallback."""
    root = analyzer_result.root if analyzer_result else scan_result.root
    # header
    console.print(make_header(root, elapsed))
    # stats row
    s = analyzer_result.stats if analyzer_result else scan_result.stats
    trunc = "  [yellow](truncated)[/]" if s.get("truncated") else ""
    if analyzer_result:
        console.print(
            f"[bold]{s.get('total_files',0)}[/] files  •  [bold]{s.get('total_loc',0):,}[/] LOC  •  "
            f"[bold]{_format_bytes(s.get('total_bytes',0))}[/]  •  "
            f"[cyan]{s.get('graph_nodes',0)}[/] modules  •  [cyan]{s.get('graph_edges',0)}[/] edges{trunc}",
            style="white",
        )
    else:
        console.print(
            f"[bold]{s['total_files']}[/] files  •  [bold]{s['total_loc']:,}[/] LOC  •  [bold]{_format_bytes(s['total_bytes'])}[/]{trunc}",
            style="white",
        )

    # languages
    lang_panel = make_languages_panel(s)
    if lang_panel:
        console.print(lang_panel)

    # summary (if analyzer)
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
        # largest files preview (top 6)
        if scan_result.files:
            largest = sorted(scan_result.files, key=lambda f: f.loc, reverse=True)[:6]
            t2 = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold white", padding=(0, 1))
            t2.add_column("File", style="white", overflow="fold")
            t2.add_column("LOC", justify="right", style="green")
            t2.add_column("Lang", style="cyan")
            t2.add_column("Size", justify="right", style="dim")
            for f in largest:
                if f.loc == 0:
                    continue
                t2.add_row(str(f.rel), str(f.loc), f.language, _format_bytes(f.size))
            if t2.row_count:
                console.print(Panel(t2, title=f"[bold]Largest Files[/]  [dim](top {t2.row_count})[/]", box=box.ROUNDED, border_style="white", padding=(0, 1)))
        console.print("[dim]Tip: [bold]peek[/] launches TUI • [bold]peek --no-tui[/] static • [bold]peek scan .[/] files only[/]")
    else:
        # scan-only fallback (no analyzer)
        tech = make_tech_stack_panel(scan_result.tech_stack)
        if tech:
            console.print(tech)
        # entry candidates as ranked fallback
        # (scan_result.entry_candidates already ranked)
        from peek.analyzer import RankedFile as RF  # lazy to avoid cycle
        # Instead build simple panel from entry candidates
        if scan_result.entry_candidates:
            t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold yellow", padding=(0, 1))
            t.add_column("#", style="dim", width=3, justify="right")
            t.add_column("Entry Candidate", style="white")
            t.add_column("Reason", style="dim")
            for i, p in enumerate(scan_result.entry_candidates, 1):
                try:
                    rel = p.relative_to(scan_result.root)
                except ValueError:
                    rel = p
                reason = "filename" if p.name in ("main.py","app.py","cli.py","__main__.py") else "main guard"
                t.add_row(str(i), str(rel), reason)
            console.print(Panel(t, title="[bold]Start Here ⭐[/]", box=box.ROUNDED, border_style="yellow", padding=(0, 1)))


def build_html(scan_result, analyzer_result, elapsed: float) -> str:
    """Build self-contained HTML export.

    Captures Rich render to HTML via Console.export_html.
    Returns full HTML document string. Never raises.
    """
    try:
        from rich.console import Console as RichConsole
        import io

        # Record console
        c = RichConsole(record=True, width=100, legacy_windows=False, force_terminal=True, color_system="truecolor")
        render_static(scan_result, analyzer_result, elapsed, c)
        html_fragment = c.export_html(inline_styles=True)
        # Wrap in full document with header
        root = analyzer_result.root if analyzer_result else scan_result.root
        title = f"peek — {root}"
        summary = analyzer_result.summary if analyzer_result else "scan"
        # Minimal template — Rich's export is already styled, we just add wrapper
        doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{summary[:150]}">
<style>
body {{ margin: 0; padding: 20px; background: #0f0f0f; }}
a {{ color: #ff7ed8; }}
h1 {{ font-family: monospace; color: #ff7ed8; }}
.timestamp {{ color: #888; font-family: monospace; font-size: 12px; }}
</style>
</head>
<body>
<h1>peek <span style="color:#888">v{__version__}</span> — {root} <span class="timestamp">({elapsed:.2f}s)</span></h1>
{html_fragment}
<footer style="margin-top:20px;color:#666;font-family:monospace;font-size:12px;">Generated by <a href="https://github.com/hariomlohardev/peek">peek</a> — htop for codebases</footer>
</body>
</html>
"""
        return doc
    except Exception as e:
        return f"<html><body><pre>peek html export failed: {e}</pre></body></html>"

