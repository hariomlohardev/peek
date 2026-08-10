"""CLI — Typer app for peek.

Day 1 scope:
  peek scan [PATH]       — scan + stats (Rich table)
  peek --help / scan --help

Future (Day 2+):
  peek analyze [PATH]
  peek [PATH]            — full TUI
  peek --find, --pack, --html etc.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from peek import __version__
from peek.analyzer import analyze
from peek.scanner import scan

# Windows: force UTF-8 so Rich can render █, ─, ╭ etc. without cp1252 errors.
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

app = typer.Typer(
    name="peek",
    help="The htop for codebases — understand any repo in 5 seconds.",
    add_completion=False,
    no_args_is_help=False,
)
# legacy_windows=False avoids the Win32 legacy renderer that chokes on Unicode;
# with stdout now UTF-8, Rich can emit true Unicode and Windows Terminal renders it.
console = Console(legacy_windows=False)
err_console = Console(stderr=True, legacy_windows=False)


# ---------------------------------------------------------------------------
# Helpers — pretty printing for Day 1
# ---------------------------------------------------------------------------

def _format_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n/1024:.1f} KB"
    return f"{n/(1024*1024):.1f} MB"


def _print_scan_result(root: Path, result, elapsed: float) -> None:
    """Rich rendering for `peek scan` Day 1 output."""
    # Header
    rel_root = result.root
    header = Text()
    header.append("peek", style="bold magenta")
    header.append(f"  v{__version__}", style="dim")
    header.append(f"  —  {rel_root}", style="cyan")
    header.append(f"  ({elapsed:.2f}s)", style="dim")
    console.print(Panel(header, box=box.ROUNDED, border_style="magenta", padding=(0, 1)))

    # Stats row
    s = result.stats
    trunc_note = "  [yellow](truncated at 2000 files)[/]" if s.get("truncated") else ""
    console.print(
        f"[bold]{s['total_files']}[/] files  •  [bold]{s['total_loc']:,}[/] LOC  •  "
        f"[bold]{_format_bytes(s['total_bytes'])}[/]{trunc_note}",
        style="white",
    )

    # Language breakdown
    by_lang = s.get("by_lang", {})
    if by_lang:
        # Sort by count desc, show top 6
        sorted_langs = sorted(by_lang.items(), key=lambda x: x[1], reverse=True)[:6]
        total = sum(by_lang.values())
        lang_table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold cyan", padding=(0, 1))
        lang_table.add_column("Language", style="white")
        lang_table.add_column("Files", justify="right", style="green")
        lang_table.add_column("Share", justify="right", style="dim")
        lang_table.add_column("Bar", style="magenta")
        max_count = sorted_langs[0][1] if sorted_langs else 1
        for lang, count in sorted_langs:
            pct = count / total * 100 if total else 0
            bar_len = int(count / max_count * 16) if max_count else 0
            bar = "█" * bar_len + "░" * (16 - bar_len)
            lang_table.add_row(lang, str(count), f"{pct:.0f}%", bar)
        console.print(Panel(lang_table, title="[bold]Languages[/]", box=box.ROUNDED, border_style="cyan", padding=(0, 1)))

    # Tech stack
    ts = result.tech_stack
    if ts:
        lines: list[str] = []
        if ts.get("primary") and ts["primary"] != "unknown":
            lines.append(f"[bold cyan]Primary:[/] {ts['primary']}")
        if ts.get("frameworks"):
            lines.append(f"[bold cyan]Frameworks:[/] {', '.join(ts['frameworks'])}")
        if ts.get("configs"):
            # Show top configs
            cfgs = ", ".join(ts["configs"][:6])
            lines.append(f"[bold cyan]Configs:[/] {cfgs}")
        if ts.get("deps"):
            deps_preview = ", ".join(ts["deps"][:8])
            if len(ts["deps"]) > 8:
                deps_preview += f"  [dim](+{len(ts['deps'])-8} more)[/]"
            lines.append(f"[bold cyan]Deps:[/] {deps_preview}")
        if lines:
            console.print(Panel("\n".join(lines), title="[bold]Tech Stack[/]", box=box.ROUNDED, border_style="green", padding=(0, 1)))

    # Entry points
    entries = result.entry_candidates
    if entries:
        t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold yellow", padding=(0, 1))
        t.add_column("#", style="dim", width=3, justify="right")
        t.add_column("Entry Candidate", style="white")
        t.add_column("Reason", style="dim")
        for i, p in enumerate(entries, 1):
            try:
                rel = p.relative_to(result.root)
            except ValueError:
                rel = p
            # Simple reason from detection — filename vs main guard
            reason = ""
            if p.name in ("main.py", "app.py", "cli.py", "__main__.py", "manage.py", "server.py", "api.py"):
                reason = "filename"
            elif p.name == "__main__.py":
                reason = "package entry"
            else:
                reason = "main guard"
            t.add_row(str(i), str(rel), reason)
        console.print(Panel(t, title="[bold]Start Here ⭐[/]  [dim](ranked entry points)[/]", box=box.ROUNDED, border_style="yellow", padding=(0, 1)))
    else:
        console.print(Panel("[dim]No clear entry point detected — check README or pyproject.toml [project.scripts][/]", title="[bold]Start Here[/]", box=box.ROUNDED, border_style="yellow"))

    # File preview — top 15 files by LOC (largest first)
    if result.files:
        # Show largest files — quick hint where bulk is
        largest = sorted(result.files, key=lambda f: f.loc, reverse=True)[:10]
        t2 = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold white", padding=(0, 1))
        t2.add_column("File", style="white", overflow="fold")
        t2.add_column("LOC", justify="right", style="green")
        t2.add_column("Lang", style="cyan")
        t2.add_column("Size", justify="right", style="dim")
        for f in largest:
            if f.loc == 0:
                continue
            t2.add_row(str(f.rel), str(f.loc), f.language, _format_bytes(f.size))
        if t2.row_count > 0:
            console.print(Panel(t2, title=f"[bold]Largest Files[/]  [dim](top {t2.row_count} by LOC, {len(result.files)} total)[/]", box=box.ROUNDED, border_style="white", padding=(0, 1)))

    # Footer hint
    console.print("[dim]Next: [bold]peek analyze .[/] adds import graph + ranked Start Here.  [bold]peek .[/] (Day 3) adds the TUI.[/]")


def _print_analyze_result(scan_result, analyzer_result, elapsed: float) -> None:
    """Rich rendering for `peek analyze` Day 2 output."""
    root = analyzer_result.root
    header = Text()
    header.append("peek", style="bold magenta")
    header.append(f"  v{__version__}", style="dim")
    header.append(f"  —  {root}", style="cyan")
    header.append(f"  ({elapsed:.2f}s)", style="dim")
    console.print(Panel(header, box=box.ROUNDED, border_style="magenta", padding=(0, 1)))

    s = analyzer_result.stats
    trunc_note = "  [yellow](truncated)[/]" if s.get("truncated") else ""
    console.print(
        f"[bold]{s.get('total_files',0)}[/] files  •  [bold]{s.get('total_loc',0):,}[/] LOC  •  "
        f"[bold]{_format_bytes(s.get('total_bytes',0))}[/]  •  "
        f"[cyan]{s.get('graph_nodes',0)}[/] modules  •  [cyan]{s.get('graph_edges',0)}[/] edges{trunc_note}",
        style="white",
    )

    # Summary panel (the star)
    console.print(Panel(analyzer_result.summary, title="[bold]Summary[/]", box=box.ROUNDED, border_style="green", padding=(0, 1)))

    # Tech stack reuse — compact
    ts = analyzer_result.tech_stack
    if ts:
        lines: list[str] = []
        if ts.get("primary") and ts["primary"] != "unknown":
            lines.append(f"[bold cyan]Primary:[/] {ts['primary']}")
        if ts.get("frameworks"):
            lines.append(f"[bold cyan]Frameworks:[/] {', '.join(ts['frameworks'])}")
        if analyzer_result.external_imports:
            ext_preview = ", ".join(sorted(analyzer_result.external_imports)[:8])
            if len(analyzer_result.external_imports) > 8:
                ext_preview += f"  [dim](+{len(analyzer_result.external_imports)-8} more)[/]"
            lines.append(f"[bold cyan]External imports:[/] {ext_preview}")
        if ts.get("configs"):
            lines.append(f"[bold cyan]Configs:[/] {', '.join(ts['configs'][:6])}")
        if lines:
            console.print(Panel("\n".join(lines), title="[bold]Tech Stack[/]", box=box.ROUNDED, border_style="cyan", padding=(0, 1)))

    # Ranked Start Here — main Day 2 feature
    ranked = analyzer_result.ranked
    if ranked:
        t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold yellow", padding=(0, 1))
        t.add_column("#", style="dim", width=3, justify="right")
        t.add_column("File", style="white", overflow="fold")
        t.add_column("Score", justify="right", style="green")
        t.add_column("Why", style="dim", overflow="fold")
        t.add_column("LOC", justify="right", style="cyan")
        # Find loc for each ranked
        loc_map = {f.path: f.loc for f in scan_result.files}
        # Show top 10
        for i, r in enumerate(ranked[:10], 1):
            why = ", ".join(r.reasons[:3])
            loc = str(loc_map.get(r.path, "?"))
            # Style top 3 bold
            style = "bold white" if i <= 3 else "white"
            # shorten file display
            t.add_row(str(i), f"[{style}]{r.rel.as_posix()}[/]", f"{r.score:.1f}", why, loc)
        # Bar hint
        console.print(Panel(t, title=f"[bold]Start Here ⭐[/]  [dim](ranked — PageRank + in-degree + entry bonus • {len(ranked)} modules)[/]", box=box.ROUNDED, border_style="yellow", padding=(0, 1)))
        # Graph edges preview — top hubs
        if analyzer_result.graph:
            # Show most connected
            most_connected = sorted(analyzer_result.graph.items(), key=lambda kv: len(kv[1]), reverse=True)[:3]
            edges_lines = []
            for src, deps in most_connected:
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
                edges_lines.append(f"[cyan]{src_rel}[/] → {', '.join(dep_rels)}{suffix}")
            if edges_lines:
                console.print(Panel("\n".join(edges_lines), title="[bold]Import Graph[/]  [dim](top hubs → deps)[/]", box=box.ROUNDED, border_style="white", padding=(0, 1)))
    else:
        console.print(Panel("[dim]No Python modules found — nothing to rank.[/]", title="[bold]Start Here[/]", box=box.ROUNDED, border_style="yellow"))

    console.print("[dim]Next: [bold]peek .[/] (Day 3) adds the TUI.  [bold]peek scan .[/] for file stats only.[/]")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@app.command("scan")
def scan_command(
    path: Path = typer.Argument(
        Path("."),
        help="Path to repo/directory to scan (default: current dir).",
        exists=False,
    ),
    max_files: int = typer.Option(2000, "--max-files", help="Hard cap on files scanned (perf guard)."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON instead of Rich table."),
) -> None:
    """Scan a repo and show file stats, tech stack, and entry points."""
    t0 = time.perf_counter()
    root = path.resolve() if path.exists() else Path.cwd() / path
    # If user passes a file, scan its parent
    if root.is_file():
        root = root.parent

    result = scan(root, max_files=max_files)
    elapsed = time.perf_counter() - t0

    if json_output:
        import json

        # Minimal JSON for --json mode
        payload = {
            "root": str(result.root),
            "elapsed": round(elapsed, 3),
            "stats": result.stats,
            "tech_stack": result.tech_stack,
            "entry_candidates": [str(p) for p in result.entry_candidates],
            "files": [{"path": str(f.rel), "loc": f.loc, "lang": f.language, "size": f.size} for f in result.files[:100]],
        }
        console.print_json(data=payload)
        return

    if result.total_files == 0:
        err_console.print(f"[yellow]No files found in[/] [bold]{path}[/] (empty or all ignored).")
        # Still show stats
    _print_scan_result(path, result, elapsed)


@app.command("analyze")
def analyze_command(
    path: Path = typer.Argument(
        Path("."),
        help="Path to repo/directory to analyze (default: current dir).",
        exists=False,
    ),
    max_files: int = typer.Option(2000, "--max-files", help="Hard cap on files scanned."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON instead of Rich table."),
) -> None:
    """Build import graph, rank files, and summarize the codebase."""
    t0 = time.perf_counter()
    root = path.resolve() if path.exists() else Path.cwd() / path
    if root.is_file():
        root = root.parent

    scan_result = scan(root, max_files=max_files)
    result = analyze(scan_result)
    elapsed = time.perf_counter() - t0

    if json_output:
        payload = {
            "root": str(result.root),
            "elapsed": round(elapsed, 3),
            "stats": result.stats,
            "tech_stack": result.tech_stack,
            "summary": result.summary,
            "external_imports": sorted(result.external_imports),
            "ranked": [
                {"path": str(r.rel), "score": round(r.score, 2), "reasons": r.reasons}
                for r in result.ranked[:20]
            ],
            "graph": {
                "nodes": len(result.graph),
                "edges": sum(len(v) for v in result.graph.values()),
                "edges_detail": {
                    k.relative_to(result.root).as_posix() if k.is_relative_to(result.root) else k.name: [
                        p.relative_to(result.root).as_posix() if p.is_relative_to(result.root) else p.name
                        for p in v
                    ]
                    for k, v in list(result.graph.items())[:30]
                },
            },
        }
        console.print_json(data=payload)
        return

    if scan_result.total_files == 0:
        err_console.print(f"[yellow]No files found in[/] [bold]{path}[/] (empty or all ignored).")
    _print_analyze_result(scan_result, result, elapsed)


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-V", help="Show version and exit."),
    no_tui: bool = typer.Option(False, "--no-tui", help="Static output only (no TUI). Day 3+."),
) -> None:
    """peek — htop for codebases. Understand any repo in 5 seconds."""
    if version:
        console.print(f"peek v{__version__}")
        raise typer.Exit(0)

    # If no subcommand, scan current dir (Day 1: bare `peek` = scan cwd)
    # Note: `peek .` alias for Day 3 will be added later — for Day 1 use `peek scan .`
    if ctx.invoked_subcommand is None:
        if version:
            return
        # Handle stray path arg like `peek .` gracefully (Day 3 compat)
        # Typer would otherwise error "unexpected extra arg" — we catch via context
        # For now, bare `peek` scans cwd; `peek scan <path>` is the explicit way
        console.print("[dim]peek — htop for codebases. Scanning current directory...[/]\n")
        t0 = time.perf_counter()
        result = scan(Path.cwd(), max_files=2000)
        elapsed = time.perf_counter() - t0
        _print_scan_result(Path("."), result, elapsed)
        console.print("\n[dim]Run [bold]peek scan .[/] for explicit path, or [bold]peek --help[/] for all commands.[/]")
        # If user passed `peek .`, that `.` is in ctx.args when allow_extra_args — handle it
        if ctx.args:
            # Try to scan the extra path if it looks like a path
            extra = ctx.args[0] if ctx.args else None
            if extra and extra not in ("--help", "-h"):
                try:
                    p = Path(extra)
                    if p.exists():
                        console.print(f"\n[dim]Note: explicit path [bold]{extra}[/] detected — use [bold]peek scan {extra}[/] (Day 3 will support [bold]peek {extra}[/] directly).[/]")
                except Exception:
                    pass


if __name__ == "__main__":
    app()
