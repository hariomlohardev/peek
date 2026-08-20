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

try:
    from peek.themes import get_theme, list_themes, resolve_theme
except Exception:  # fallback if themes not yet loaded
    get_theme = list_themes = resolve_theme = None  # type: ignore

ANTHRO_CLI = {"accent": "#D4A27F", "muted": "#9A9590", "ink": "#E8E6E3"}

# Theme-aware spinner accent helper
def _theme_accent(theme=None) -> str:
    try:
        if theme and hasattr(theme, "tokens"):
            return theme.tokens.get("accent", ANTHRO_CLI["accent"])
    except Exception:
        pass
    return ANTHRO_CLI["accent"]

def _scan_with_spinner(path: Path, max_files: int = 2000, label: str = "Scanning", theme=None):
    """Anthropic-style subtle spinner — only when TTY, else plain scan."""
    try:
        is_tty = False
        try:
            is_tty = sys.stderr.isatty()
        except Exception:
            pass
        if is_tty:
            from rich.progress import Progress, SpinnerColumn, TextColumn
            import time as _t
            import threading

            with Progress(
                SpinnerColumn(spinner_name="dots", style=_theme_accent(theme)),
                TextColumn(f"[bold {ANTHRO_CLI['ink']}]{label}[/] [dim {ANTHRO_CLI['muted']}]{{task.fields[path]}}[/]"),
                console=err_console,
                transient=True,
            ) as progress:
                task = progress.add_task(label, path=str(path))
                result: dict = {}

                def _do():
                    result["scan"] = scan(path, max_files=max_files)

                t = threading.Thread(target=_do, daemon=True)
                t.start()
                start = _t.perf_counter()
                # Ensure spinner visible at least 120ms so it doesn't flash
                while t.is_alive() or (_t.perf_counter() - start) < 0.12:
                    _t.sleep(0.03)
                    if not t.is_alive() and (_t.perf_counter() - start) >= 0.12:
                        break
                t.join()
                return result["scan"]
    except Exception:
        pass
    return scan(path, max_files=max_files)


def _should_animate() -> bool:
    try:
        return sys.stdout.isatty() and sys.stderr.isatty()
    except Exception:
        return False

def _write_output_safely(path: Path, content: str) -> Path:
    try:
        import tempfile
        orig = path
        if sys.platform == "win32":
            posix = orig.as_posix()
            if posix.startswith("/tmp/") or posix.startswith("\\tmp\\"):
                path = Path(tempfile.gettempdir()) / orig.name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path
    except Exception:
        fallback = Path.cwd() / "peek.html"
        fallback.write_text(content, encoding="utf-8")
        return fallback

# Windows: force UTF-8 so Rich can render █, ─, ╭ etc. without cp1252 errors.
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import click as _click
except ImportError:
    from typer import _click  # typer 0.27+ vendors click
from typer.core import TyperGroup

class _PeekGroup(TyperGroup):
    def parse_args(self, ctx, args):
        # Let Click handle --help / --version normally (eager options)
        if any(a in ("--help", "-h", "--version", "-V") for a in args):
            return super().parse_args(ctx, args)
        if not args and self.no_args_is_help and not ctx.resilient_parsing:
            raise _click.exceptions.NoArgsIsHelpError(ctx)
        # Use click.Command parse to get leftover args (options already parsed)
        rest = _click.Command.parse_args(self, ctx, args)
        if rest:
            first = rest[0]
            known = {"scan", "analyze", "find", "watch", "wtf", "config", "graph", "index", "mcp", "log", "diff", "hot", "blame", "git", "trace"}
            is_option = first.startswith("-")
            is_known_cmd = first in known
            # Options like --help, --theme, --no-tui etc. should not be treated as subcommand
            if is_option:
                ctx.args = rest
                ctx._protected_args = []
                return ctx.args
            # Path-like: ".", "..", "./", "../", "/", contains slash/dot, or exists as file/dir
            is_path = False
            if first in (".", ".."):
                is_path = True
            elif first.startswith(("./", "../", "/", "\\")):
                is_path = True
            elif not is_known_cmd:
                # Treat as path only if it looks like a path (contains . or / or \ or exists)
                # This keeps `peek myrepo` (existing dir) working, but `peek typo123` still errors as unknown command
                if "." in first or "/" in first or "\\" in first or Path(first).exists():
                    is_path = True
            if is_path and not is_known_cmd:
                ctx.args = rest
                ctx._protected_args = []
                return ctx.args
            ctx._protected_args, ctx.args = rest[:1], rest[1:]
        return ctx.args

    def get_command(self, ctx, cmd_name):
        # Fallback: if somehow a path slipped to get_command, don't error
        if cmd_name in (".", ".."):
            return None
        if cmd_name.startswith(("./", "../", "/", "\\")):
            return None
        try:
            if Path(cmd_name).exists():
                return None
        except Exception:
            pass
        return super().get_command(ctx, cmd_name)

app = typer.Typer(
    name="peek",
    help="The htop for codebases — understand any repo in 5 seconds.",
    add_completion=False,
    no_args_is_help=False,
    cls=_PeekGroup,
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
console = Console(legacy_windows=False)
err_console = Console(stderr=True, legacy_windows=False)


# ---------------------------------------------------------------------------
# Helpers — pretty printing
# ---------------------------------------------------------------------------

def _warn_no_files(path: Path) -> None:
    """Report an empty scan, and point at the next thing to try.

    "No files found" reads like a failure the user caused. Usually it is not:
    the directory is genuinely empty, or everything in it is ignored. Naming
    both causes and offering `peek --help` gives them somewhere to go, which a
    bare statement does not.

    Shared by `scan` and `analyze` so the two cannot drift apart.
    """
    err_console.print(
        f"[yellow]No files found in[/] [bold]{path}[/] (empty or all ignored). "
        "[dim]Try:[/] [bold]peek --help[/]"
    )


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
    theme: Optional[str] = typer.Option(None, "--theme", help="Theme: anthropic-pro, cinematic, dracula, nord, catppuccin-mocha, tokyo-night, solarized-dark, github-dark, monokai, minimal-mono"),
) -> None:
    """Scan a repo and show file stats, tech stack, and entry points."""
    # Fix #80: resolve theme fresh (no cache) — respects --theme and PEEK_THEME env
    resolved_theme = None
    if theme and resolve_theme:
        try:
            resolved_theme = resolve_theme(theme)
        except ValueError as e:
            err_console.print(f"[red]{e}[/]")
            raise typer.Exit(2)
    elif resolve_theme:
        try:
            resolved_theme = resolve_theme(None)
        except ValueError as e:
            err_console.print(f"[red]{e}[/]")
            raise typer.Exit(2)
    t0 = time.perf_counter()
    root = path.resolve() if path.exists() else Path.cwd() / path
    if root.is_file():
        root = root.parent

    # Subtle spinner only when TTY and not json/html
    if not json_output and not html and _should_animate():
        result = _scan_with_spinner(root, max_files=max_files, label="Scanning", theme=resolved_theme)
    else:
        result = scan(root, max_files=max_files)
    elapsed = time.perf_counter() - t0

    if html:
        from peek.renderer import build_html
        fake_analyzer = type("obj", (), {"root": result.root, "summary": "scan only", "tech_stack": result.tech_stack, "external_imports": set(), "stats": result.stats, "ranked": [], "graph": {}})()
        html_str = build_html(result, fake_analyzer, elapsed, theme=resolved_theme)
        if output:
            actual = _write_output_safely(output, html_str)
            console.print(f"[green]HTML written to[/] [bold]{actual}[/] ({len(html_str)} bytes)")
        else:
            out = Path("peek.html")
            actual = _write_output_safely(out, html_str)
            console.print(f"[green]HTML written to[/] [bold]{actual}[/] — use -o to specify path")
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
        _warn_no_files(path)
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
    theme: Optional[str] = typer.Option(None, "--theme", help="Theme: anthropic-pro, cinematic, dracula, nord, catppuccin-mocha, tokyo-night, solarized-dark, github-dark, monokai, minimal-mono"),
) -> None:
    """Build import graph, rank files, and summarize the codebase."""
    # Fix #80: resolve theme fresh (no cache) — respects --theme and PEEK_THEME env
    resolved_theme = None
    if theme and resolve_theme:
        try:
            resolved_theme = resolve_theme(theme)
        except ValueError as e:
            err_console.print(f"[red]{e}[/]")
            raise typer.Exit(2)
    elif resolve_theme:
        try:
            resolved_theme = resolve_theme(None)
        except ValueError as e:
            err_console.print(f"[red]{e}[/]")
            raise typer.Exit(2)
    t0 = time.perf_counter()
    root = path.resolve() if path.exists() else Path.cwd() / path
    if root.is_file():
        root = root.parent

    if not json_output and not html and _should_animate():
        scan_result = _scan_with_spinner(root, max_files=max_files, label="Analyzing", theme=resolved_theme)
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
        html_str = build_html(scan_result, result, elapsed, theme=resolved_theme)
        if output:
            actual = _write_output_safely(output, html_str)
            console.print(f"[green]HTML written to[/] [bold]{actual}[/] ({len(html_str)} bytes)")
        else:
            out = Path("peek.html")
            actual = _write_output_safely(out, html_str)
            console.print(f"[green]HTML written to[/] [bold]{actual}[/] — use -o to specify path")
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
        _warn_no_files(path)
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
    """Find files by keyword — filename + content, ranked by relevance.

    \b
    Examples:
        peek find "auth" . --limit 5
        peek find "TODO" src/
    """
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


@app.command("graph")
def graph_command(
    path: Path = typer.Argument(Path("."), help="Path to repo"),
    format: str = typer.Option("dot", "--format", help="dot|svg|html|mermaid"),
    output: Path = typer.Option(None, "--output", "-o"),
):
    from peek.scanner import scan; from peek.analyzer import analyze
    from peek.graph import export_graph
    sr = scan(path.resolve()); ar = analyze(sr)
    try:
        out = export_graph(ar, format=format)
    except ValueError as e:
        err_console.print(f"[red]{e}[/]")
        raise typer.Exit(2)
    if output:
        p = Path(output)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        p.write_text(out, encoding="utf-8")
        console.print(f"[green]Graph written to {output}[/]")
    else:
        # raw output — avoid Rich markup stripping brackets in DOT
        try:
            console.print(out, markup=False)
        except TypeError:
            # fallback for older Rich
            import sys
            sys.stdout.write(out)
            sys.stdout.write("\n")
            sys.stdout.flush()


@app.command("trace")
def trace_command(
    symbol: str = typer.Argument(None, help="Function to trace: name, qualname (MyClass.method), file::func, or use --at FILE:LINE. Python only for now."),
    path: Path = typer.Argument(Path("."), help="Repo path (default: current dir)."),
    depth: int = typer.Option(3, "--depth", "-d", help="Depth of tree (1-6, default 3)."),
    direction: str = typer.Option("callees", "--direction", help="callees | callers | both (default callees)."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON instead of tree."),
    output: Path = typer.Option(None, "--output", "-o", help="Write output to file (for --json, --html or text)."),
    at: str = typer.Option(None, "--at", help="Locate function by FILE:LINE (e.g. --at peek/scanner.py:601) instead of symbol."),
    cross_file: bool = typer.Option(True, "--cross-file/--local", help="Follow cross-file calls (default --cross-file). Use --local for intra-file only."),
    show_externals: bool = typer.Option(False, "--show-externals", help="Include external/builtin leaf nodes."),
    html: bool = typer.Option(False, "--html", help="Open polished HTML in browser (temp file + webbrowser, filter, theme, expand)."),
    theme: str = typer.Option(None, "--theme", help="Theme: anthropic-pro, cinematic, dracula, etc."),
) -> None:
    """Trace a Python function — show its call tree (what it takes & where it goes).

    Different from TUI — this is a **flag/command** that prints a tree to stdout (or --json).
    Python only for now; other languages later.

    \b
    Examples:
        peek trace scan --depth 3
        peek trace "MyClass.method" ./src --depth 4
        peek trace --at peek/scanner.py:601 --depth 2 --local
        peek trace scan --json | jq
        peek trace scan --direction callers --show-externals
        peek trace "peek/scanner.py::scan" --depth 3 --output tree.txt
    """
    import json as _json

    # Resolve theme early
    resolved_theme = None
    if theme and resolve_theme:
        try:
            resolved_theme = resolve_theme(theme)
        except ValueError as e:
            err_console.print(f"[red]{e}[/]")
            raise typer.Exit(2)
    elif resolve_theme:
        try:
            resolved_theme = resolve_theme(None)
        except Exception:
            resolved_theme = None

    # Paths
    # Handle case where symbol positional consumed the path when --at is used
    # e.g. `peek trace --at C:\tmp\x.py:5 C:\tmp` -> typer assigns C:\tmp to symbol (first positional) and leaves path as default "."
    # Detect and shift: if at is set, symbol looks like a path, and path is still default "."
    if at is not None and symbol is not None and path == Path("."):
        # Don't shift if symbol looks like a qualified symbol (contains ::)
        if "::" not in symbol:
            # Check if symbol looks like a path (exists or contains slash/backslash or is "."/"..")
            is_path_like = False
            try:
                if Path(symbol).exists():
                    is_path_like = True
                elif "/" in symbol or "\\" in symbol or symbol in (".", "..") or symbol.startswith("./") or symbol.startswith("../"):
                    is_path_like = True
                # Also handle Windows absolute like C:\ or C:/
                elif len(symbol) >= 2 and symbol[1] == ":" and (symbol[2:3] == "\\" or symbol[2:3] == "/"):
                    is_path_like = True
            except Exception:
                pass
            if is_path_like:
                path = Path(symbol)
                symbol = None

    root = path.resolve() if path.exists() else Path.cwd() / path
    if root.is_file():
        root = root.parent

    # Validate symbol / at
    if not symbol and not at:
        err_console.print("[red]Provide a symbol or --at FILE:LINE[/]  [dim]e.g. peek trace scan  or  peek trace --at peek/scanner.py:601[/]")
        raise typer.Exit(2)
    if depth < 1 or depth > 6:
        err_console.print("[red]--depth must be 1-6[/]")
        raise typer.Exit(2)
    if direction not in ("callees", "callers", "both"):
        err_console.print("[red]--direction must be callees|callers|both[/]")
        raise typer.Exit(2)

    t0 = time.perf_counter()
    # Scan
    scan_result = scan(root)
    if scan_result.total_files == 0:
        _warn_no_files(root)
        raise typer.Exit(0)

    # Build trace graph (Python only)
    try:
        from peek.trace.builder import build_trace_graph
        from peek.trace.query import find_by_location, find_focals
        from peek.trace.render import render_trace, trace_to_json
        from peek.trace.query import trace as trace_query
    except Exception as e:
        err_console.print(f"[red]Trace failed to load: {e}[/]")
        raise typer.Exit(1)

    graph = build_trace_graph(scan_result)
    if not graph.nodes:
        err_console.print("[yellow]No Python functions found.[/]  [dim]Trace is Python-only for now — ensure the repo has .py files and is not empty/ignored.[/]")
        # Still handle json?
        if json_output:
            payload = {"focal": None, "error": "No Python functions found", "root": str(root), "warnings": graph.warnings}
            out = _json.dumps(payload, indent=2)
            if output:
                _write_output_safely(output, out)
                console.print(f"[green]Written to {output}[/]")
            else:
                console.print_json(data=payload)
            raise typer.Exit(0)
        raise typer.Exit(0)

    # Resolve focal
    focal = None
    candidates: list = []
    if at:
        # at is like "peek/scanner.py:601" or "scanner.py:601"
        if ":" not in at:
            err_console.print("[red]--at must be FILE:LINE e.g. --at peek/scanner.py:601[/]")
            raise typer.Exit(2)
        file_part, line_str = at.rsplit(":", 1)
        try:
            lineno = int(line_str.strip())
        except ValueError:
            err_console.print("[red]--at LINE must be integer[/]")
            raise typer.Exit(2)
        focal = find_by_location(graph, file_part.strip(), lineno)
        if not focal:
            err_console.print(f"[red]No function contains {at}[/]  [dim]Try peek scan to check files, or use symbol name.[/]")
            # List nearby functions in that file for hint
            try:
                rel_hint = file_part.strip()
                nearby = [n for fid, n in graph.nodes.items() if n.rel.as_posix() == rel_hint or n.rel.as_posix().endswith(rel_hint) or n.file.name == rel_hint]
                if not nearby:
                    # try any file containing hint
                    nearby = [n for fid, n in graph.nodes.items() if rel_hint in n.rel.as_posix()]
                if nearby:
                    nearby_sorted = sorted(nearby, key=lambda n: n.lineno)[:5]
                    hint = ", ".join(f"{n.qualname}:{n.lineno}" for n in nearby_sorted)
                    err_console.print(f"[dim]Nearby in {file_part}: {hint}[/]")
            except Exception:
                pass
            raise typer.Exit(1)
    else:
        # symbol resolution
        assert symbol is not None
        candidates = find_focals(graph, symbol, limit=5)
        if not candidates:
            err_console.print(f"[red]No function matches {symbol!r}[/]")
            # Suggest closest by substring
            try:
                # show 3 suggestions
                all_names = sorted({n.name for n in graph.nodes.values()})[:10]
                err_console.print(f"[dim]Available (sample): {', '.join(all_names[:6])} ...[/]")
                err_console.print(f"[dim]Tip: peek trace --at FILE:LINE to pinpoint[/]")
            except Exception:
                pass
            raise typer.Exit(1)
        if len(candidates) > 1:
            # Disambiguate: show table and pick first, but warn
            err_console.print(f"[yellow]Multiple matches for {symbol!r} — showing first, {len(candidates)} total:[/]")
            from rich.table import Table as _T
            t = _T(box=box.SIMPLE_HEAD, show_header=True, header_style="bold cyan", padding=(0,1))
            t.add_column("#", style="dim", width=3, justify="right")
            t.add_column("Qualname", style="white")
            t.add_column("File", style="cyan")
            t.add_column("Line", justify="right", style="green")
            for i, fid in enumerate(candidates[:5], 1):
                n = graph.nodes[fid]
                style = "bold white" if i==1 else "white"
                t.add_row(str(i), f"[{style}]{n.qualname}[/]", n.rel.as_posix(), str(n.lineno))
            err_console.print(t)
            err_console.print(f"[dim]Tip: use qualified name like {graph.nodes[candidates[0]].qualname} or file::func or --at[/]")
        focal = candidates[0]

    # Build tree
    trace_tree = trace_query(graph, focal, depth=depth, direction=direction, cross_file=cross_file, show_externals=show_externals)
    elapsed = time.perf_counter() - t0

    if html:
        try:
            from peek.trace.html import build_trace_html

            html_str = build_trace_html(trace_tree, graph, theme=resolved_theme, root_path=root)
            if output:
                actual = _write_output_safely(output, html_str)
                console.print(f"[green]HTML written to[/] [bold]{actual}[/] ({len(html_str)} bytes)")
                # also try to open if --html without needing temp
                try:
                    import webbrowser

                    webbrowser.open(actual.resolve().as_uri())
                except Exception:
                    pass
            else:
                import tempfile
                import webbrowser

                tmp = Path(tempfile.gettempdir()) / f"peek-trace-{focal.qualname.replace('.', '-').replace('::', '-')}.html"
                try:
                    tmp.write_text(html_str, encoding="utf-8")
                except Exception:
                    tmp = Path.cwd() / f"peek-trace-{focal.qualname.replace('.', '-').replace('::', '-')}.html"
                    tmp.write_text(html_str, encoding="utf-8")
                console.print(f"[green]HTML written to[/] [bold]{tmp}[/] ({len(html_str)} bytes) — opening browser")
                try:
                    webbrowser.open(tmp.as_uri())
                except Exception as e:
                    err_console.print(f"[yellow]Open browser failed: {e}[/]  [dim]Open file://{tmp} manually[/]")
            return
        except Exception as e:
            err_console.print(f"[red]HTML failed: {e}[/]")
            raise typer.Exit(1)

    if json_output:
        payload = trace_to_json(trace_tree, graph)
        payload["elapsed"] = round(elapsed, 3)
        payload["root"] = str(root)
        payload["args"] = {"symbol": symbol, "at": at, "depth": depth, "direction": direction, "cross_file": cross_file, "show_externals": show_externals}
        out = _json.dumps(payload, indent=2, ensure_ascii=False)
        if output:
            actual = _write_output_safely(output, out)
            console.print(f"[green]JSON written to[/] [bold]{actual}[/] ({len(out)} bytes)")
        else:
            # Use plain stdout for jq piping, not console.print_json which adds markup
            try:
                import sys as _sys
                _sys.stdout.write(out + "\n")
                _sys.stdout.flush()
            except Exception:
                console.print_json(data=payload)
        return

    # Render tree
    from peek.trace.render import render_trace as _render

    panel = _render(trace_tree, graph, theme=resolved_theme)
    if output:
        # Capture panel to file for --output (text)
        try:
            from io import StringIO as _SIO

            from rich.console import Console as _RConsole

            buf = _SIO()
            tmp_c = _RConsole(file=buf, force_terminal=False, width=console.width if hasattr(console, "width") else 100)
            tmp_c.print(panel)
            footer = f"— trace: {focal.qualname} at {graph.nodes[focal].rel.as_posix()}:{graph.nodes[focal].lineno} • depth {depth} • {trace_tree.total_nodes} nodes • {elapsed:.2f}s —"
            tmp_c.print(f"[dim]{footer}[/]")
            text = buf.getvalue()
            actual = _write_output_safely(output, text)
            console.print(f"[green]Trace written to[/] [bold]{actual}[/] ({len(text)} bytes)")
        except Exception as e:
            err_console.print(f"[red]Failed to write {output}: {e}[/]")
            raise typer.Exit(1)
        return
    console.print(panel)
    # Footer hints
    if not cross_file and trace_tree.total_nodes < 3:
        console.print("[dim]Tip: try without --local to follow cross-file calls.[/]")
    if direction == "callees" and not trace_tree.root.children:
        console.print("[dim]No callees within depth — try --direction callers or --depth 4, or --show-externals for builtins.[/]")
    # Also show file count
    console.print(f"[dim]— trace: {focal.qualname} at {graph.nodes[focal].rel.as_posix()}:{graph.nodes[focal].lineno} • depth {depth} • {trace_tree.total_nodes} nodes • {elapsed:.2f}s —[/]")


@app.command("index")
def index_command(
    path: Path = typer.Argument(Path("."), help="Path to repo/directory to index"),
    rebuild: bool = typer.Option(False, "--rebuild", help="Force rebuild even if cached"),
):
    """Build semantic index (BM25 + optional fastembed)."""
    import json

    from peek.embeddings import build_index
    from peek.scanner import scan

    root = path.resolve() if path.exists() else Path.cwd() / path
    if root.is_file():
        root = root.parent
    sr = scan(root)
    idx = build_index(sr)
    cache_dir = root / ".peek"
    try:
        cache_dir.mkdir(exist_ok=True)
    except Exception:
        pass
    payload = {"chunks": len(idx.get("chunks", [])), "files": len(sr.files)}
    try:
        (cache_dir / "index.json").write_text(json.dumps(payload), encoding="utf-8")
    except Exception:
        pass
    console.print(f"[green]Indexed {len(idx.get('chunks', []))} chunks[/] at {cache_dir}")


config_app = typer.Typer(help="Config: get/set/list")
app.add_typer(config_app, name="config")


@config_app.command("set")
def config_set(key: str = typer.Argument(...), value: str = typer.Argument(...)):
    from peek.config import set_config_value
    try:
        p = set_config_value(key, value)
        console.print(f"[green]Set {key}={value!r} at {p}[/]")
    except ValueError as e:
        err_console.print(f"[red]{e}[/]")
        raise typer.Exit(2)


@config_app.command("get")
def config_get(key: str = typer.Argument(...)):
    from peek.config import load_config
    console.print(str(load_config().get(key, "")))


@config_app.command("list")
def config_list():
    from peek.config import load_config, config_path
    console.print(f"[dim]{config_path()}[/]")
    console.print_json(data=load_config())


@app.command("watch")
def watch_command(
    path: Path = typer.Argument(Path("."), help="Path to watch"),
) -> None:
    """Watch a repo and re-render on changes (polling). Ctrl+C to quit."""
    from peek.analyzer import analyze
    from peek.scanner import scan
    from peek.watch import watch_repo
    from peek.renderer import render_static
    from rich.console import Console

    console_w = Console(legacy_windows=False)
    root = path.resolve()
    if root.is_file():
        root = root.parent
    t0 = time.perf_counter()
    sr = scan(root)
    ar = analyze(sr)
    elapsed = time.perf_counter() - t0
    render_static(sr, ar, elapsed, console_w)
    console_w.print("[dim]Watching... Ctrl+C to quit[/]")

    def on_change(nsr, nar) -> None:
        try:
            console_w.clear()
        except Exception:
            pass
        render_static(nsr, nar, 0.01, console_w)
        console_w.print("[dim]Updated[/]")

    watcher = watch_repo(root, on_change)
    try:
        import time as _time

        while True:
            _time.sleep(1)
    except KeyboardInterrupt:
        watcher.stop()
    raise typer.Exit(0)


@app.command("wtf")
def wtf_command(
    path: Path = typer.Argument(None, help="File containing traceback, or omit to read stdin pipe"),
    explain: bool = typer.Option(True, "--explain/--no-explain", help="Add heuristic explain with scan"),
) -> None:
    """Explain a Python traceback with scan-aware hints.

    \b
    Examples:
        cat tb.txt | peek wtf
        peek wtf traceback.txt
    """
    import sys

    text = ""
    if path is not None and str(path) != "None":
        try:
            p = Path(path)
            if p.exists() and p.is_file():
                text = p.read_text(encoding="utf-8", errors="ignore")
            else:
                # path given but not a file — try stdin fallback
                text = sys.stdin.read()
        except Exception:
            text = sys.stdin.read()
    else:
        text = sys.stdin.read()

    from peek.wtf import explain_tb, parse_traceback

    from peek.analyzer import analyze
    from peek.scanner import scan

    info = parse_traceback(text)
    if not info:
        err_console.print("[yellow]No traceback found in input.[/]")
        raise typer.Exit(1)
    if explain:
        try:
            sr = scan(Path.cwd())
            ar = analyze(sr)
            console.print(explain_tb(info, sr, ar))
        except Exception as e:
            console.print(info.raw)
            err_console.print(f"[dim]explain failed: {e}[/]")
    else:
        console.print(info.raw)


@app.command("mcp")
def mcp_command() -> None:
    """Start MCP stdio server — exposes peek_scan, peek_rank, peek_pack, peek_find, peek_graph, peek_explain."""
    from peek.mcp_server import main as mcp_main

    mcp_main()


@app.command("log")
def log_command(
    path: Path = typer.Argument(Path("."), help="Path to repo (default '.')"),
    n: int = typer.Option(20, "--n", "-n", help="Number of commits to show"),
    since: Optional[str] = typer.Option(None, "--since", help="Show commits since date (e.g. '1 week ago')"),
    author: Optional[str] = typer.Option(None, "--author", help="Filter by author"),
    no_oneline: bool = typer.Option(False, "--no-oneline", help="Disable oneline"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Show git log — time machine for the repo."""
    from peek.git import git_log

    root = path.resolve() if path.exists() else Path.cwd() / path
    if root.is_file():
        root = root.parent
    try:
        n = int(n)
    except Exception:
        n = 20
    out = git_log(root, n=n, since=since, author=author, oneline=not no_oneline)
    if json_output:
        lines = [l for l in out.splitlines() if l.strip()]
        console.print_json(data={"root": str(root), "commits": lines[:n]})
        return
    if not out or not out.strip():
        err_console.print(f"[yellow]No git log for[/] [bold]{root}[/] (not a git repo or no commits).")
        return
    # Rich panel
    console.print(Panel(out.strip(), title=f"[bold]git log[/]  [dim]({root} • -{n})[/]", box=box.ROUNDED, border_style="cyan", padding=(0, 1)))


@app.command("diff")
def diff_command(
    path: Path = typer.Argument(Path("."), help="Path to repo"),
    base: str = typer.Option("HEAD", "--base", "-b", help="Base to diff against (e.g. HEAD, HEAD~1)"),
    staged: bool = typer.Option(False, "--staged", help="Show staged only (git diff --staged)"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Show changed files — `git diff --name-only`."""
    from peek.git import git_diff

    root = path.resolve() if path.exists() else Path.cwd() / path
    if root.is_file():
        root = root.parent
    files = git_diff(root, base=base, staged=staged)
    if json_output:
        console.print_json(data={"root": str(root), "base": base, "staged": staged, "files": files})
        return
    if not files:
        console.print(f"[dim]No changes vs {base} in[/] [bold]{root}[/] [dim] (or not a git repo)[/]")
        return
    t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold cyan", padding=(0, 1))
    t.add_column("#", style="dim", width=3, justify="right")
    t.add_column("Changed File", style="white")
    for i, f in enumerate(files[:50], 1):
        t.add_row(str(i), f)
    suffix = f" (+{len(files)-50} more)" if len(files) > 50 else ""
    console.print(Panel(t, title=f"[bold]git diff[/]  [dim]({base} • {len(files)} files{suffix})[/]", box=box.ROUNDED, border_style="yellow", padding=(0, 1)))


@app.command("hot")
def hot_command(
    path: Path = typer.Argument(Path("."), help="Path to repo"),
    n: int = typer.Option(50, "--n", "-n", help="Commits to scan for churn"),
    limit: int = typer.Option(10, "--limit", "-l", help="Top N hot files"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Hot files — most churned via `git log --numstat`."""
    from peek.git import git_hot

    root = path.resolve() if path.exists() else Path.cwd() / path
    if root.is_file():
        root = root.parent
    try:
        n = int(n)
    except Exception:
        n = 50
    try:
        limit = int(limit)
    except Exception:
        limit = 10
    hot = git_hot(root, n=n, limit=limit)
    if json_output:
        console.print_json(data={"root": str(root), "n": n, "hot": hot})
        return
    if not hot:
        err_console.print(f"[yellow]No churn data for[/] [bold]{root}[/] (not a git repo or no history).")
        return
    t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold yellow", padding=(0, 1))
    t.add_column("#", style="dim", width=3, justify="right")
    t.add_column("File", style="white", overflow="fold")
    t.add_column("Churn", justify="right", style="green")
    t.add_column("Commits", justify="right", style="cyan")
    t.add_column("Added", justify="right", style="dim")
    t.add_column("Deleted", justify="right", style="dim")
    for i, h in enumerate(hot, 1):
        t.add_row(str(i), h.get("file", "?"), str(h.get("churn", 0)), str(h.get("commits", 0)), str(h.get("added", 0)), str(h.get("deleted", 0)))
    console.print(Panel(t, title=f"[bold]Hot files[/]  [dim](churn over last {n} commits)[/]", box=box.ROUNDED, border_style="magenta", padding=(0, 1)))


@app.command("blame")
def blame_command(
    file: Path = typer.Argument(..., help="File to blame (relative to repo, e.g. peek/scanner.py)"),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Repo path (default '.')"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Git blame — who changed each line."""
    from peek.git import git_blame

    root = path.resolve() if path.exists() else Path.cwd() / path
    if root.is_file():
        root = root.parent
    # file may be absolute or relative; pass as is
    out = git_blame(root, file)
    if json_output:
        console.print_json(data={"root": str(root), "file": str(file), "blame": out[:8000]})
        return
    if not out or not out.strip():
        err_console.print(f"[yellow]No blame for[/] [bold]{file}[/] in [bold]{root}[/] (not a git repo or file not tracked).")
        return
    # Show first 80 lines to avoid flooding
    lines = out.splitlines()
    preview = "\n".join(lines[:80])
    if len(lines) > 80:
        preview += f"\n… (+{len(lines)-80} more lines)"
    console.print(Panel(preview, title=f"[bold]git blame[/]  [dim]{file} • {len(lines)} lines[/]", box=box.ROUNDED, border_style="white", padding=(0, 1)))


# Git sub-app for `peek git log/diff/hot/blame` alias (mirrors top-level)
git_app = typer.Typer(help="Git time machine — log/diff/hot/blame (alias for peek log/diff/hot/blame)")
app.add_typer(git_app, name="git")


@git_app.command("log")
def git_log_cmd(
    path: Path = typer.Argument(Path("."), help="Path to repo"),
    n: int = typer.Option(20, "--n", "-n", help="Number of commits"),
    since: Optional[str] = typer.Option(None, "--since", help="Since date"),
    author: Optional[str] = typer.Option(None, "--author", help="Author"),
    no_oneline: bool = typer.Option(False, "--no-oneline", help="Disable oneline"),
    json_output: bool = typer.Option(False, "--json", help="JSON"),
):
    """Alias for `peek log` via `peek git log`."""
    log_command(path, n, since, author, no_oneline, json_output)


@git_app.command("diff")
def git_diff_cmd(
    path: Path = typer.Argument(Path("."), help="Path to repo"),
    base: str = typer.Option("HEAD", "--base", "-b", help="Base"),
    staged: bool = typer.Option(False, "--staged", help="Staged only"),
    json_output: bool = typer.Option(False, "--json", help="JSON"),
):
    """Alias for `peek diff` via `peek git diff`."""
    diff_command(path, base, staged, json_output)


@git_app.command("hot")
def git_hot_cmd(
    path: Path = typer.Argument(Path("."), help="Path to repo"),
    n: int = typer.Option(50, "--n", "-n", help="Commits to scan"),
    limit: int = typer.Option(10, "--limit", "-l", help="Top N"),
    json_output: bool = typer.Option(False, "--json", help="JSON"),
):
    """Alias for `peek hot` via `peek git hot`."""
    hot_command(path, n, limit, json_output)


@git_app.command("blame")
def git_blame_cmd(
    file: Path = typer.Argument(..., help="File to blame"),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Repo path"),
    json_output: bool = typer.Option(False, "--json", help="JSON"),
):
    """Alias for `peek blame` via `peek git blame`."""
    blame_command(file, path, json_output)


@app.callback(invoke_without_command=True, context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def main_callback(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-V", help="Show version and exit."),
    no_tui: bool = typer.Option(False, "--no-tui", help="Static output only (no TUI)."),
    html: bool = typer.Option(False, "--html", help="Export to HTML (use -o to specify file)."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file for --html/--pack."),
    pack: bool = typer.Option(False, "--pack", help="LLM pack: concatenate top files for clipboard/LLM."),
    ask: Optional[str] = typer.Option(None, "--ask", help="Filter --pack by keyword (e.g. --ask auth)."),
    pack_format: str = typer.Option("md", "--format", help="Pack format: md|xml|txt (with --pack)."),
    pack_budget: int = typer.Option(8000, "--budget", help="Token budget for pack (with --pack)."),
    pack_include: Optional[str] = typer.Option(None, "--include", help="Include glob for pack (with --pack)."),
    pack_exclude: Optional[str] = typer.Option(None, "--exclude", help="Exclude glob for pack (with --pack)."),
    llm: bool = typer.Option(False, "--llm", help="Try LLM summary if API key set."),
    find: Optional[str] = typer.Option(None, "--find", help="Find keyword (alternative to `peek find`)."),
    theme: Optional[str] = typer.Option(None, "--theme", help="Theme: anthropic-pro, cinematic, dracula, nord, catppuccin-mocha, tokyo-night, solarized-dark, github-dark, monokai, minimal-mono"),
    theme_list: bool = typer.Option(False, "--theme-list", help="List available themes and exit"),
    watch: bool = typer.Option(False, "--watch", "-w", help="Watch mode: auto-rescan on changes (TUI)."),
    clip: bool = typer.Option(False, "--clip", help="Copy pack to clipboard (with --pack)."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Dry-run: show table instead of pack (with --pack)."),
    diff: Optional[str] = typer.Option(None, "--diff", help="Pack only diff files (with --pack). e.g. --diff HEAD or --diff main"),
    staged: bool = typer.Option(False, "--staged", help="Pack only staged files (with --pack)."),
) -> None:
    """peek — htop for codebases. Understand any repo in 5 seconds.

    Default (no subcommand) launches the TUI: `peek` or `peek [PATH]`.
    Use `--no-tui` for static Rich output (pipeable, screenshot-ready).
    Use `--html -o out.html` for HTML export.
    Use `--pack [--ask QUERY]` to pack top files for LLM.
    Use `peek find <query>` to search.
    Tip: peek --watch for live TUI, peek watch . for static watch.
    """
    if version:
        console.print(f"peek v{__version__}")
        raise typer.Exit(0)

    # --theme-list early exit (no scan needed)
    if theme_list:
        try:
            from peek.themes import list_themes as _list_themes
            from rich.table import Table as _Table
            tbl = _Table(box=box.ROUNDED, show_header=True, header_style="bold cyan", padding=(0, 1))
            tbl.add_column("■", style="white", width=2, justify="center")
            tbl.add_column("ID", style="cyan")
            tbl.add_column("Label", style="white")
            tbl.add_column("Description", style="dim")
            tbl.add_column("Accent", style="white")
            tbl.add_column("Bg", style="dim")
            for th in _list_themes():
                tbl.add_row(f"[{th.tokens['accent']}]{th.preview}[/]", f"[bold]{th.id}[/]", th.label, th.description, th.tokens["accent"], th.tokens["bg"])
            console.print(Panel(tbl, title="[bold]Available themes[/]  [dim]10 themes • --theme <id> • PEEK_THEME env • config.toml[/]", box=box.ROUNDED, border_style="cyan", padding=(0, 1)))
            # also plain list for scripting
            console.print("[dim]Usage: [bold]peek --theme dracula[/]  or  [bold]PEEK_THEME=dracula peek[/]  or  [bold]theme = \"dracula\"[/] in ~/.peek/config.toml[/]")
        except Exception as e:
            err_console.print(f"[red]Failed to list themes: {e}[/]")
        raise typer.Exit(0)

    # Resolve theme early (before scan) — handle invalid immediately
    # Fix #80: do not cache resolve_theme — must re-evaluate cli_opt and PEEK_THEME
    # on every invocation. Previous caching returned anthropic-pro (#141413) for
    # later `dracula` requests on Windows, causing wrong bg in html export.
    resolved_theme = None
    # Check raw extra for --theme if Typer didn't parse due to ctx.args path handling
    _raw_theme = theme
    if ctx.args:
        for idx, a in enumerate(ctx.args):
            if a == "--theme" and idx + 1 < len(ctx.args):
                _raw_theme = ctx.args[idx + 1]
                break
            if a.startswith("--theme="):
                _raw_theme = a.split("=", 1)[1]
                break
    if _raw_theme or theme:
        _want = _raw_theme or theme
        if resolve_theme:
            try:
                # Always call fresh — no lru_cache, respects env/config changes
                resolved_theme = resolve_theme(_want)
            except ValueError as e:
                err_console.print(f"[red]{e}[/]")
                raise typer.Exit(2)
    else:
        # No cli theme — try env/config via resolve_theme(None) fresh each call
        if resolve_theme:
            try:
                resolved_theme = resolve_theme(None)
            except ValueError as e:
                err_console.print(f"[red]{e}[/]")
                raise typer.Exit(2)

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
    # Clean --theme / --theme-list from extra so path detection works (they were already resolved)
    if "--theme" in extra:
        try:
            idx = extra.index("--theme")
            if idx + 1 < len(extra):
                extra = [a for i, a in enumerate(extra) if i not in (idx, idx + 1)]
            else:
                extra = [a for a in extra if a != "--theme"]
        except ValueError:
            pass
    extra = [a for a in extra if not a.startswith("--theme=")]
    if "--theme-list" in extra:
        extra = [a for a in extra if a != "--theme-list"]
    # Also handle --pack/--ask/--llm/--find present as raw? Typer already parsed, but keep
    if "--pack" in extra:
        pack = True
        extra = [a for a in extra if a != "--pack"]
    if "--llm" in extra:
        llm = True
        extra = [a for a in extra if a != "--llm"]
    # handle --watch in raw
    if "--watch" in extra:
        watch = True
        extra = [a for a in extra if a != "--watch"]
    if "-w" in extra and not any(a.startswith("-") and len(a) > 2 for a in extra):
        # only treat standalone -w; don't confuse combined flags
        if "-w" in extra:
            watch = True
            extra = [a for a in extra if a != "-w"]

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

    # Also handle --format/--budget/--include/--exclude in raw (pack v2)
    # Typer may have parsed, but we also check extra for robustness and --format=xml style
    # Use sentinel: if pack_format is default "md" but extra contains override, use extra
    # Handle --format
    if "--format" in extra:
        try:
            idx = extra.index("--format")
            if idx + 1 < len(extra):
                pack_format = extra[idx + 1]
                extra = [a for i, a in enumerate(extra) if i not in (idx, idx + 1)]
            else:
                extra = [a for a in extra if a != "--format"]
        except ValueError:
            pass
    # --format=xml style
    for a in list(extra):
        if a.startswith("--format="):
            pack_format = a.split("=", 1)[1]
            extra.remove(a)
    # --budget
    if "--budget" in extra:
        try:
            idx = extra.index("--budget")
            if idx + 1 < len(extra):
                try:
                    pack_budget = int(extra[idx + 1])
                except Exception:
                    pass
                extra = [a for i, a in enumerate(extra) if i not in (idx, idx + 1)]
            else:
                extra = [a for a in extra if a != "--budget"]
        except ValueError:
            pass
    for a in list(extra):
        if a.startswith("--budget="):
            try:
                pack_budget = int(a.split("=", 1)[1])
            except Exception:
                pass
            extra.remove(a)
    # --include
    if "--include" in extra:
        try:
            idx = extra.index("--include")
            if idx + 1 < len(extra):
                pack_include = extra[idx + 1]
                extra = [a for i, a in enumerate(extra) if i not in (idx, idx + 1)]
            else:
                extra = [a for a in extra if a != "--include"]
        except ValueError:
            pass
    for a in list(extra):
        if a.startswith("--include="):
            pack_include = a.split("=", 1)[1]
            extra.remove(a)
    # --exclude
    if "--exclude" in extra:
        try:
            idx = extra.index("--exclude")
            if idx + 1 < len(extra):
                pack_exclude = extra[idx + 1]
                extra = [a for i, a in enumerate(extra) if i not in (idx, idx + 1)]
            else:
                extra = [a for a in extra if a != "--exclude"]
        except ValueError:
            pass
    for a in list(extra):
        if a.startswith("--exclude="):
            pack_exclude = a.split("=", 1)[1]
            extra.remove(a)

    # Also handle --clip/--dry-run/--staged and --diff for pack v3.0 (when Typer didn't parse due to allow_extra_args)
    if "--clip" in extra:
        clip = True
        extra = [a for a in extra if a != "--clip"]
    if "--dry-run" in extra:
        dry_run = True
        extra = [a for a in extra if a != "--dry-run"]
    if "--staged" in extra:
        staged = True
        extra = [a for a in extra if a != "--staged"]
    if "--diff" in extra:
        try:
            idx = extra.index("--diff")
            if idx + 1 < len(extra) and not extra[idx + 1].startswith("-"):
                diff = extra[idx + 1]
                extra = [a for i, a in enumerate(extra) if i not in (idx, idx + 1)]
            else:
                diff = "HEAD"
                extra = [a for a in extra if a != "--diff"]
        except ValueError:
            pass
    for a in list(extra):
        if a.startswith("--diff="):
            diff = a.split("=", 1)[1]
            extra.remove(a)

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
        if not pack and not html and not llm and _should_animate() and not no_tui:
            scan_result = _scan_with_spinner(path, label="Scanning", theme=resolved_theme)
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
        html_str = build_html(scan_result, analyzer_result, elapsed, theme=resolved_theme)
        if output:
            actual = _write_output_safely(output, html_str)
            console.print(f"[green]HTML written to[/] [bold]{actual}[/] ({len(html_str)} bytes)")
        else:
            out = Path("peek.html")
            actual = _write_output_safely(out, html_str)
            console.print(f"[green]HTML written to[/] [bold]{actual}[/] — use -o to specify path")
        raise typer.Exit(0)

    # --pack
    if pack:
        from peek.pack import build_pack
        # ask may be provided via --ask, pack_* via --format/--budget/--include/--exclude
        # v3: also dry_run, diff, staged, clip + https:// URL fetch via query
        packed, included, tokens = build_pack(
            scan_result,
            analyzer_result,
            query=ask,
            budget=pack_budget,
            format=pack_format,
            include=pack_include,
            exclude=pack_exclude,
            dry_run=dry_run,
            diff=diff,
            staged=staged,
            clip=clip,
        )
        # For dry_run, even 0 files produces a table, so don't treat as "no files"
        if not dry_run and (not packed.strip() or not included):
            err_console.print(f"[yellow]No files for pack (query={ask!r} yielded no matches).[/]")
            raise typer.Exit(0)
        if dry_run and not packed.strip():
            err_console.print(f"[yellow]No files for pack (query={ask!r} yielded no matches).[/]")
            raise typer.Exit(0)
        if output:
            actual = _write_output_safely(output, packed)
            if dry_run:
                console.print(f"[green]Dry-run table written to[/] [bold]{actual}[/] • {len(included)} files • ~{tokens} tokens")
            else:
                console.print(f"[green]Pack written to[/] [bold]{actual}[/] • {len(included)} files • ~{tokens} tokens")
            if clip:
                err_console.print(f"[dim]— copied to clipboard • {len(included)} files • ~{tokens} tokens —[/]")
        else:
            # Write to stdout (so `peek --pack | pbcopy` works)
            # For dry-run, show table as well
            # Use sys.stdout directly to avoid Rich markup for md pack
            try:
                sys.stdout.write(packed)
                sys.stdout.flush()
            except Exception:
                console.print(packed)
            # Also hint
            if dry_run:
                err_console.print(f"\n[dim]— dry-run: {len(included)} files • ~{tokens} tokens • query={ask or 'none'} —[/]")
            else:
                err_console.print(f"\n[dim]— pack: {len(included)} files • ~{tokens} tokens • query={ask or 'none'} —[/]")
            if clip:
                err_console.print(f"[dim]— copied to clipboard —[/]")
        raise typer.Exit(0)

    # --no-tui or not a tty → static render
    wants_static = no_tui
    if not wants_static:
        try:
            if not sys.stdout.isatty() and not sys.stderr.isatty():
                wants_static = True
        except Exception:
            pass

    # --watch handling
    if watch:
        if wants_static:
            # static watch: render then polling loop
            try:
                from peek.renderer import render_static
                from peek.watch import watch_repo

                render_static(scan_result, analyzer_result, elapsed, console, theme=resolved_theme)
                console.print("[dim]Watching... Ctrl+C to quit[/]")

                def on_change_w(nsr, nar) -> None:
                    try:
                        console.clear()
                    except Exception:
                        pass
                    render_static(nsr, nar, 0.01, console, theme=resolved_theme)
                    console.print("[dim]Updated[/]")

                watcher_w = watch_repo(path.resolve() if path.exists() else Path.cwd(), on_change_w)
                try:
                    import time as _tw

                    while True:
                        _tw.sleep(1)
                except KeyboardInterrupt:
                    watcher_w.stop()
            except Exception as e:
                err_console.print(f"[red]Watch failed: {e}[/]")
            raise typer.Exit(0)
        # TUI watch: launch TUI with watch enabled
        # fall through to TUI block with watch=True
        pass

    if wants_static and not watch:
        try:
            from peek.renderer import render_static
            render_static(scan_result, analyzer_result, elapsed, console, theme=resolved_theme)
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
            render_static(scan_result, analyzer_result, elapsed, console, theme=resolved_theme)
            raise typer.Exit(0)
        # pass watch flag through
        if watch:
            code = run_tui(path, scan_result, analyzer_result, elapsed, theme=resolved_theme, watch=True)
        else:
            code = run_tui(path, scan_result, analyzer_result, elapsed, theme=resolved_theme)
        raise typer.Exit(code if isinstance(code, int) else 0)
    except SystemExit:
        raise
    except typer.Exit:
        raise
    except Exception as e:
        err_console.print(f"[yellow]TUI failed ({e}) — falling back to static.[/]")
        try:
            from peek.renderer import render_static
            render_static(scan_result, analyzer_result, elapsed, console, theme=resolved_theme)
        except Exception:
            _print_analyze_result(scan_result, analyzer_result, elapsed)
        raise typer.Exit(0)


if __name__ == "__main__":
    app()
