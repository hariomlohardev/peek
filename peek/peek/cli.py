"""CLI — Typer app for peek.

Day 4: P1 features — --html, --pack, find, --llm
  peek [PATH]            — full TUI (default, viral)
  peek [PATH] --no-tui   — static Rich
  peek [PATH] --html -o out.html
  peek [PATH] --pack [--ask QUERY] [-o out.txt]
  peek scan [PATH]       — scan + stats
  peek analyze [PATH]    — graph + ranking
  peek find <query> [PATH]
  peek --help
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Optional

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from peek import __version__
from peek.analyzer import analyze
from peek.scanner import scan

# Cinematic tokens for CLI spinner
CINE_CLI = {
    "signal": "#FFE600",
    "muted": "#7A86B6",
    "ink": "#E6E8F0",
}


def _scan_with_spinner(path: Path, max_files: int = 2000, label: str = "Scanning"):
    """Scan with cinematic spinner if TTY, else plain."""
    try:
        # Only animate if terminal and not piped
        if sys.stdout.isatty() and sys.stderr.isatty():
            from rich.progress import Progress, SpinnerColumn, TextColumn
            import time as _t

            with Progress(
                SpinnerColumn(style=CINE_CLI["signal"]),
                TextColumn(f"[bold {CINE_CLI['ink']}]{label}[/] [dim {CINE_CLI['muted']}]{{task.fields[path]}}[/]"),
                TextColumn(f"[{CINE_CLI['signal']}]{{task.fields[extra]}}[/]"),
                console=err_console,
                transient=True,
            ) as progress:
                task = progress.add_task(label, path=str(path), extra="· cinematic scan")
                # Run scan in thread? For now, run and update
                # Since scan is fast, we fake progress
                import threading

                result = {}

                def _do():
                    result["scan"] = scan(path, max_files=max_files)

                t = threading.Thread(target=_do, daemon=True)
                t.start()
                # Animate for at least 0.18s to show spinner (viral feel)
                start = _t.perf_counter()
                while t.is_alive() or (_t.perf_counter() - start) < 0.18:
                    progress.update(task, extra="· walking · ignoring · counting")
                    _t.sleep(0.04)
                    if not t.is_alive() and (_t.perf_counter() - start) >= 0.18:
                        break
                t.join()
                progress.update(task, extra="· done")
                return result["scan"]
    except Exception:
        pass
    # Fallback plain
    return scan(path, max_files=max_files)

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
console = Console(legacy_windows=False)
err_console = Console(stderr=True, legacy_windows=False)


# ---------------------------------------------------------------------------
# Helpers — pretty printing
# ---------------------------------------------------------------------------

def _format_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n/1024:.1f} KB"
    return f"{n/(1024*1024):.1f} MB"


def _print_scan_result(root: Path, result, elapsed: float) -> None:
    """Rich rendering for `peek scan`."""
    rel_root = result.root
    header = Text()
    header.append("peek", style="bold magenta")
    header.append(f"  v{__version__}", style="dim")
    header.append(f"  —  {rel_root}", style="cyan")
    header.append(f"  ({elapsed:.2f}s)", style="dim")
    console.print(Panel(header, box=box.ROUNDED, border_style="magenta", padding=(0, 1)))

    s = result.stats
    trunc_note = "  [yellow](truncated at 2000 files)[/]" if s.get("truncated") else ""
    console.print(
        f"[bold]{s['total_files']}[/] files  •  [bold]{s['total_loc']:,}[/] LOC  •  "
        f"[bold]{_format_bytes(s['total_bytes'])}[/]{trunc_note}",
        style="white",
    )

    by_lang = s.get("by_lang", {})
    if by_lang:
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

    ts = result.tech_stack
    if ts:
        lines: list[str] = []
        if ts.get("primary") and ts["primary"] != "unknown":
            lines.append(f"[bold cyan]Primary:[/] {ts['primary']}")
        if ts.get("frameworks"):
            lines.append(f"[bold cyan]Frameworks:[/] {', '.join(ts['frameworks'])}")
        if ts.get("configs"):
            cfgs = ", ".join(ts["configs"][:6])
            lines.append(f"[bold cyan]Configs:[/] {cfgs}")
        if ts.get("deps"):
            deps_preview = ", ".join(ts["deps"][:8])
            if len(ts["deps"]) > 8:
                deps_preview += f"  [dim](+{len(ts['deps'])-8} more)[/]"
            lines.append(f"[bold cyan]Deps:[/] {deps_preview}")
        if lines:
            console.print(Panel("\n".join(lines), title="[bold]Tech Stack[/]", box=box.ROUNDED, border_style="green", padding=(0, 1)))

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

    if result.files:
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

    console.print("[dim]Next: [bold]peek analyze .[/] adds import graph + ranked Start Here.  [bold]peek .[/] TUI.[/]")


def _print_analyze_result(scan_result, analyzer_result, elapsed: float) -> None:
    """Rich rendering for `peek analyze`."""
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

    console.print(Panel(analyzer_result.summary, title="[bold]Summary[/]", box=box.ROUNDED, border_style="green", padding=(0, 1)))

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

    ranked = analyzer_result.ranked
    if ranked:
        t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold yellow", padding=(0, 1))
        t.add_column("#", style="dim", width=3, justify="right")
        t.add_column("File", style="white", overflow="fold")
        t.add_column("Score", justify="right", style="green")
        t.add_column("Why", style="dim", overflow="fold")
        t.add_column("LOC", justify="right", style="cyan")
        loc_map = {f.path: f.loc for f in scan_result.files}
        for i, r in enumerate(ranked[:10], 1):
            why = ", ".join(r.reasons[:3])
            loc = str(loc_map.get(r.path, "?"))
            style = "bold white" if i <= 3 else "white"
            t.add_row(str(i), f"[{style}]{r.rel.as_posix()}[/]", f"{r.score:.1f}", why, loc)
        console.print(Panel(t, title=f"[bold]Start Here ⭐[/]  [dim](ranked — PageRank + in-degree + entry bonus • {len(ranked)} modules)[/]", box=box.ROUNDED, border_style="yellow", padding=(0, 1)))
        if analyzer_result.graph:
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

    console.print("[dim]Next: [bold]peek .[/] TUI  [bold]peek --html -o out.html[/]  [bold]peek --pack[/][/]")


def _print_find_result(matches: list[dict], query: str, elapsed: float) -> None:
    header = Text()
    header.append("peek find", style="bold magenta")
    header.append(f"  v{__version__}", style="dim")
    header.append(f"  —  query: ", style="dim")
    header.append(f'"{query}"', style="cyan")
    header.append(f"  ({elapsed:.2f}s)", style="dim")
    console.print(Panel(header, box=box.ROUNDED, border_style="magenta", padding=(0, 1)))

    if not matches:
        console.print(Panel(f"[dim]No matches for [bold]{query!r}[/] — try broader term.[/]", title="[bold]Find[/]", box=box.ROUNDED, border_style="yellow"))
        return

    t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold yellow", padding=(0, 1))
    t.add_column("#", style="dim", width=3, justify="right")
    t.add_column("File", style="white", overflow="fold")
    t.add_column("Score", justify="right", style="green")
    t.add_column("Reason", style="dim", overflow="fold")
    t.add_column("LOC", justify="right", style="cyan")
    for i, m in enumerate(matches, 1):
        style = "bold white" if i <= 3 else "white"
        t.add_row(str(i), f"[{style}]{m['rel'].as_posix()}[/]", f"{m['score']:.1f}", m["reason"], str(m["loc"]))
    console.print(Panel(t, title=f"[bold]Matches[/]  [dim]({len(matches)} files)[/]", box=box.ROUNDED, border_style="yellow", padding=(0, 1)))

    # Preview lines
    for m in matches[:5]:
        if m["preview"]:
            preview_text = "\n".join(m["preview"])
            # highlight query roughly
            console.print(Panel(preview_text, title=f"[bold]{m['rel'].as_posix()}[/]  [dim]preview[/]", box=box.ROUNDED, border_style="white", padding=(0, 1)))

    console.print(f"[dim]Tip: [bold]peek --pack --ask \"{query}\"[/] to pack matches for LLM.[/]")


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
    html: bool = typer.Option(False, "--html", help="Export to HTML (use -o to specify file)."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file for --html/--pack."),
) -> None:
    """Scan a repo and show file stats, tech stack, and entry points."""
    t0 = time.perf_counter()
    root = path.resolve() if path.exists() else Path.cwd() / path
    if root.is_file():
        root = root.parent

    # Cinematic scan with spinner if TTY and not json/html
    if not json_output and not html and sys.stdout.isatty():
        result = _scan_with_spinner(root, max_files=max_files, label="Scanning")
    else:
        result = scan(root, max_files=max_files)
    elapsed = time.perf_counter() - t0

    if html:
        from peek.renderer import build_html
        # need dummy analyzer for scan-only html? create minimal
        from unittest.mock import MagicMock as _MM
        # Actually build html with scan only — use renderer's build_html which expects analyzer
        # We'll create a minimal analyzer wrapper
        fake_analyzer = type("obj", (), {"root": result.root, "summary": "scan only", "tech_stack": result.tech_stack, "external_imports": set(), "stats": result.stats, "ranked": [], "graph": {}})()
        html_str = build_html(result, fake_analyzer, elapsed)
        if output:
            output.write_text(html_str, encoding="utf-8")
            console.print(f"[green]HTML written to[/] [bold]{output}[/] ({len(html_str)} bytes)")
        else:
            # default to peek.html
            out = Path("peek.html")
            out.write_text(html_str, encoding="utf-8")
            console.print(f"[green]HTML written to[/] [bold]{out}[/] — use -o to specify path")
        return

    if json_output:
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
    html: bool = typer.Option(False, "--html", help="Export to HTML (use -o to specify file)."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file for --html."),
    llm: bool = typer.Option(False, "--llm", help="Try LLM summary if API key set."),
) -> None:
    """Build import graph, rank files, and summarize the codebase."""
    t0 = time.perf_counter()
    root = path.resolve() if path.exists() else Path.cwd() / path
    if root.is_file():
        root = root.parent

    # Cinematic: spinner for scan+analyze if TTY
    if not json_output and not html and sys.stdout.isatty():
        scan_result = _scan_with_spinner(root, max_files=max_files, label="Scanning")
        # Analyze with brief spinner
        try:
            from rich.progress import Progress, SpinnerColumn, TextColumn

            with Progress(
                SpinnerColumn(style=CINE_CLI["signal"]),
                TextColumn(f"[bold {CINE_CLI['ink']}]Analyzing[/] [dim {CINE_CLI['muted']}]graph · rank · summary[/]"),
                console=err_console,
                transient=True,
            ) as p:
                task = p.add_task("analyze")
                import threading

                res = {}

                def _do():
                    res["ar"] = analyze(scan_result)

                th = threading.Thread(target=_do, daemon=True)
                th.start()
                import time as _t

                start = _t.perf_counter()
                while th.is_alive() or (_t.perf_counter() - start) < 0.15:
                    _t.sleep(0.03)
                    if not th.is_alive() and (_t.perf_counter() - start) >= 0.15:
                        break
                th.join()
                result = res["ar"]
        except Exception:
            result = analyze(scan_result)
    else:
        scan_result = scan(root, max_files=max_files)
        result = analyze(scan_result)
    elapsed = time.perf_counter() - t0

    # LLM optional
    if llm:
        try:
            from peek.llm import try_llm_summary
            llm_text = try_llm_summary(scan_result, result, force=True)
            if llm_text:
                result.summary = llm_text + "\n[dim](via LLM)[/]"
                console.print("[green]LLM summary:[/] ", llm_text)
        except Exception as e:
            err_console.print(f"[yellow]LLM failed: {e}[/]")

    if html:
        from peek.renderer import build_html
        html_str = build_html(scan_result, result, elapsed)
        if output:
            output.write_text(html_str, encoding="utf-8")
            console.print(f"[green]HTML written to[/] [bold]{output}[/] ({len(html_str)} bytes)")
        else:
            out = Path("peek.html")
            out.write_text(html_str, encoding="utf-8")
            console.print(f"[green]HTML written to[/] [bold]{out}[/] — use -o to specify path")
        return

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


@app.command("find")
def find_command(
    query: str = typer.Argument(..., help="Keyword to search (filename or content)."),
    path: Path = typer.Argument(
        Path("."),
        help="Path to repo/directory to search (default: current dir).",
        exists=False,
    ),
    limit: int = typer.Option(20, "--limit", help="Max results."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
    max_files: int = typer.Option(2000, "--max-files", help="Hard cap on files scanned."),
) -> None:
    """Find files by keyword — filename + content, ranked by relevance."""
    t0 = time.perf_counter()
    root = path.resolve() if path.exists() else Path.cwd() / path
    if root.is_file():
        root = root.parent
    scan_result = scan(root, max_files=max_files)
    analyzer_result = analyze(scan_result)
    from peek.find import find_matches
    matches = find_matches(query, scan_result, analyzer_result, limit=limit)
    elapsed = time.perf_counter() - t0

    if json_output:
        payload = {
            "root": str(scan_result.root),
            "query": query,
            "elapsed": round(elapsed, 3),
            "matches": [
                {"path": str(m["rel"]), "score": m["score"], "reason": m["reason"], "preview": m["preview"]}
                for m in matches
            ],
        }
        console.print_json(data=payload)
        return

    _print_find_result(matches, query, elapsed)


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-V", help="Show version and exit."),
    no_tui: bool = typer.Option(False, "--no-tui", help="Static output only (no TUI)."),
    html: bool = typer.Option(False, "--html", help="Export to HTML (use -o to specify file)."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file for --html/--pack."),
    pack: bool = typer.Option(False, "--pack", help="LLM pack: concatenate top files for clipboard/LLM."),
    ask: Optional[str] = typer.Option(None, "--ask", help="Filter --pack by keyword (e.g. --ask auth)."),
    llm: bool = typer.Option(False, "--llm", help="Try LLM summary if API key set."),
    find: Optional[str] = typer.Option(None, "--find", help="Find keyword (alternative to `peek find`)."),
) -> None:
    """peek — htop for codebases. Understand any repo in 5 seconds.

    Default (no subcommand) launches the TUI: `peek` or `peek [PATH]`.
    Use `--no-tui` for static Rich output (pipeable, screenshot-ready).
    Use `--html -o out.html` for HTML export.
    Use `--pack [--ask QUERY]` to pack top files for LLM.
    Use `peek find <query>` to search.
    """
    if version:
        console.print(f"peek v{__version__}")
        raise typer.Exit(0)

    if ctx.invoked_subcommand is not None:
        return

    # No subcommand: this is `peek` or `peek [PATH]` — handle flags
    # Collect extra args for path + --no-tui in ctx.args (e.g. `peek . --no-tui`)
    extra = list(ctx.args) if ctx.args else []
    # Typer already parsed some flags, but also check raw args for aliases
    for flag in ("--no-tui", "--html"):
        if flag in extra:
            if flag == "--no-tui":
                no_tui = True
            if flag == "--html":
                html = True
            extra = [a for a in extra if a != flag]
    # Also handle --pack/--ask/--llm/--find present as raw? Typer already parsed, but keep
    if "--pack" in extra:
        pack = True
        extra = [a for a in extra if a != "--pack"]
    if "--llm" in extra:
        llm = True
        extra = [a for a in extra if a != "--llm"]

    # Handle --find QUERY in raw args (alternative to option)
    # If Typer parsed --find already, `find` var is set; else check extra
    if find is None and "--find" in extra:
        try:
            idx = extra.index("--find")
            if idx + 1 < len(extra):
                find = extra[idx + 1]
                extra = [a for i, a in enumerate(extra) if i not in (idx, idx + 1)]
            else:
                extra = [a for a in extra if a != "--find"]
        except ValueError:
            pass

    # Also handle --ask in raw (if not parsed)
    if ask is None and "--ask" in extra:
        try:
            idx = extra.index("--ask")
            if idx + 1 < len(extra):
                ask = extra[idx + 1]
                extra = [a for i, a in enumerate(extra) if i not in (idx, idx + 1)]
        except ValueError:
            pass
    if output is None and ("-o" in extra or "--output" in extra):
        # Typer already parsed -o, but check raw
        for flag in ("-o", "--output"):
            if flag in extra:
                try:
                    idx = extra.index(flag)
                    if idx + 1 < len(extra):
                        output = Path(extra[idx + 1])
                        extra = [a for i, a in enumerate(extra) if i not in (idx, idx + 1)]
                except ValueError:
                    pass

    # Help
    if extra and extra[0] in ("--help", "-h"):
        console.print("[dim]peek — htop for codebases. Use [bold]peek --help[/] for usage.[/]")
        try:
            console.print(app.get_help(ctx))
        except Exception:
            pass
        raise typer.Exit(0)

    # Determine path
    path = Path.cwd()
    if extra:
        cand = extra[0]
        if cand not in ("--help", "-h"):
            try:
                p = Path(cand)
                if p.exists() or cand in (".", "..") or cand.startswith("./") or cand.startswith("../"):
                    path = p
                elif cand.startswith("/") or cand.startswith("\\"):
                    path = p
            except Exception:
                pass

    # --find mode takes precedence (like `peek --find auth .`)
    if find:
        t0 = time.perf_counter()
        root = path.resolve() if path.exists() else Path.cwd() / path
        if root.is_file():
            root = root.parent
        scan_result = scan(root)
        analyzer_result = analyze(scan_result)
        from peek.find import find_matches
        matches = find_matches(find, scan_result, analyzer_result, limit=20)
        elapsed = time.perf_counter() - t0
        _print_find_result(matches, find, elapsed)
        raise typer.Exit(0)

    # For pack/html/llm/static we need scan+analyze
    # If pack requested, we handle it before TUI
    t0 = time.perf_counter()
    try:
        # Cinematic spinner if TTY and not html/pack/find
        do_animate = sys.stdout.isatty() and not html and not pack and not find
        if do_animate:
            scan_result = _scan_with_spinner(path, label="Scanning")
            # Analyze with spinner
            try:
                from rich.progress import Progress, SpinnerColumn, TextColumn

                with Progress(
                    SpinnerColumn(style=CINE_CLI["signal"]),
                    TextColumn(f"[bold {CINE_CLI['ink']}]Analyzing[/] [dim {CINE_CLI['muted']}]graph · rank · signal[/]"),
                    console=err_console,
                    transient=True,
                ) as p:
                    task = p.add_task("analyze")
                    import threading

                    res = {}

                    def _do2():
                        res["ar"] = analyze(scan_result)

                    th = threading.Thread(target=_do2, daemon=True)
                    th.start()
                    import time as _t

                    start = _t.perf_counter()
                    while th.is_alive() or (_t.perf_counter() - start) < 0.14:
                        _t.sleep(0.03)
                        if not th.is_alive() and (_t.perf_counter() - start) >= 0.14:
                            break
                    th.join()
                    analyzer_result = res["ar"]
            except Exception:
                analyzer_result = analyze(scan_result)
        else:
            scan_result = scan(path)
            analyzer_result = analyze(scan_result)
        elapsed = time.perf_counter() - t0
    except Exception as e:
        err_console.print(f"[red]Failed to analyze {path}: {e}[/]")
        raise typer.Exit(1)

    # LLM: enrich summary if requested
    if llm:
        try:
            from peek.llm import try_llm_summary
            llm_text = try_llm_summary(scan_result, analyzer_result, force=True)
            if llm_text:
                analyzer_result.summary = llm_text + "\n[dim](via LLM)[/]"
                console.print(f"[green]LLM summary[/]: {llm_text}\n")
            else:
                err_console.print("[yellow]LLM not available — no API key or package. Using heuristic summary.[/]")
        except Exception as e:
            err_console.print(f"[yellow]LLM failed: {e}[/]")

    # --html
    if html:
        from peek.renderer import build_html
        html_str = build_html(scan_result, analyzer_result, elapsed)
        if output:
            output.write_text(html_str, encoding="utf-8")
            console.print(f"[green]HTML written to[/] [bold]{output}[/] ({len(html_str)} bytes)")
        else:
            out = Path("peek.html")
            out.write_text(html_str, encoding="utf-8")
            console.print(f"[green]HTML written to[/] [bold]{out}[/] — use -o to specify path")
        raise typer.Exit(0)

    # --pack
    if pack:
        from peek.pack import build_pack
        # ask may be provided via --ask
        packed, included, tokens = build_pack(scan_result, analyzer_result, query=ask)
        if not packed.strip() or not included:
            err_console.print(f"[yellow]No files for pack (query={ask!r} yielded no matches).[/]")
            raise typer.Exit(0)
        if output:
            output.write_text(packed, encoding="utf-8")
            console.print(f"[green]Pack written to[/] [bold]{output}[/] • {len(included)} files • ~{tokens} tokens")
        else:
            # Write to stdout (so `peek --pack | pbcopy` works)
            # Use sys.stdout directly to avoid Rich markup
            try:
                sys.stdout.write(packed)
                sys.stdout.flush()
            except Exception:
                console.print(packed)
            # Also hint
            err_console.print(f"\n[dim]— pack: {len(included)} files • ~{tokens} tokens • query={ask or 'none'} —[/]")
        raise typer.Exit(0)

    # --no-tui or not a tty → static render
    wants_static = no_tui
    if not wants_static:
        try:
            if not sys.stdout.isatty() and not sys.stderr.isatty():
                wants_static = True
        except Exception:
            pass

    if wants_static:
        try:
            from peek.renderer import render_static
            render_static(scan_result, analyzer_result, elapsed, console)
        except Exception as e:
            err_console.print(f"[dim]renderer fallback: {e}[/]")
            _print_analyze_result(scan_result, analyzer_result, elapsed)
        raise typer.Exit(0)

    # Try TUI
    try:
        from peek.tui import run_tui, TEXTUAL_AVAILABLE
        if not TEXTUAL_AVAILABLE:
            err_console.print("[yellow]Textual not installed — falling back to static.[/]  [dim]pip install textual[/]")
            from peek.renderer import render_static
            render_static(scan_result, analyzer_result, elapsed, console)
            raise typer.Exit(0)
        code = run_tui(path, scan_result, analyzer_result, elapsed)
        raise typer.Exit(code if isinstance(code, int) else 0)
    except SystemExit:
        raise
    except typer.Exit:
        raise
    except Exception as e:
        err_console.print(f"[yellow]TUI failed ({e}) — falling back to static.[/]")
        try:
            from peek.renderer import render_static
            render_static(scan_result, analyzer_result, elapsed, console)
        except Exception:
            _print_analyze_result(scan_result, analyzer_result, elapsed)
        raise typer.Exit(0)


if __name__ == "__main__":
    app()
