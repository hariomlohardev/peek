"""TUI — Textual app for peek.

Day 3 scope: `peek` (no args) launches interactive TUI.
- Header + Summary + Tech Stack + Graph (left)
- Ranked Start Here list (right, navigable)
- Footer with bindings: q quit, j/k nav, o open, / filter, enter details

MVP: nav + quit + open + filter (future). Falls back to static if not tty.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

try:
    from textual import on
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Horizontal, Vertical, VerticalScroll
    from textual.widgets import Footer, Header, Input, Label, ListItem, ListView, Static

    TEXTUAL_AVAILABLE = True
except Exception:  # pragma: no cover
    TEXTUAL_AVAILABLE = False
    # Dummy names for type checking when not installed
    App = object  # type: ignore
    ComposeResult = None  # type: ignore


def _detail_for(path: Path, graph, reverse_graph, root: Path) -> RenderableType:
    """Build detail renderable for selected file."""
    try:
        imports = graph.get(path, set())
        imported_by = reverse_graph.get(path, set())

        def _rel(p: Path) -> str:
            try:
                return p.relative_to(root).as_posix()
            except ValueError:
                return p.name

        lines: list[str] = []
        if imports:
            deps = ", ".join(_rel(p) for p in sorted(imports, key=lambda x: x.name)[:5])
            suffix = f" (+{len(imports)-5} more)" if len(imports) > 5 else ""
            lines.append(f"[bold cyan]Imports:[/] {deps}{suffix}")
        else:
            lines.append("[dim]Imports: none[/]")
        if imported_by:
            ib = ", ".join(_rel(p) for p in sorted(imported_by, key=lambda x: x.name)[:5])
            suffix = f" (+{len(imported_by)-5} more)" if len(imported_by) > 5 else ""
            lines.append(f"[bold yellow]Imported by:[/] {ib}{suffix}")
        else:
            lines.append("[dim]Imported by: none (leaf / entry)[/]")
        # size
        try:
            size = path.stat().st_size
            lines.append(f"[dim]Size: {size} bytes • {path.suffix or 'no ext'}[/]")
        except Exception:
            pass
        return Panel("\n".join(lines), title=f"[bold]{_rel(path)}[/]", border_style="yellow")
    except Exception as e:
        return Panel(f"[red]Error: {e}[/]", title="Detail")


if TEXTUAL_AVAILABLE:

    class PeekApp(App):  # type: ignore
        """Peek TUI — htop for codebases."""

        TITLE = "peek — htop for codebases"
        SUB_TITLE = "Understand any repo in 5 seconds"

        CSS = """
        Screen {
            layout: vertical;
        }
        #main {
            layout: horizontal;
            height: 1fr;
        }
        #left {
            width: 1.2fr;
            min-width: 42;
            height: 1fr;
            overflow-y: auto;
            padding-right: 1;
        }
        #right {
            width: 1fr;
            min-width: 32;
            height: 1fr;
            border: tall $primary;
            background: $surface;
        }
        #detail {
            height: auto;
            max-height: 8;
            dock: bottom;
            border: tall $primary 50%;
            background: $panel;
        }
        ListView {
            height: 1fr;
        }
        ListItem {
            padding: 0 1;
        }
        #filter-input {
            display: none;
            dock: top;
            height: 3;
        }
        #filter-input.visible {
            display: block;
        }
        """

        BINDINGS = [
            Binding("q", "quit", "Quit"),
            Binding("o", "open_file", "Open in $EDITOR"),
            Binding("/", "filter", "Filter"),
            Binding("?", "help", "Help"),
            Binding("escape", "clear_filter", "Clear", show=False),
            Binding("j", "cursor_down", "Down", show=False),
            Binding("k", "cursor_up", "Up", show=False),
        ]

        def __init__(self, root: Path, scan_result, analyzer_result, elapsed: float):
            super().__init__()
            self.root = root
            self.scan_result = scan_result
            self.analyzer_result = analyzer_result
            self.elapsed = elapsed
            self._filter = ""
            self._all_ranked = list(analyzer_result.ranked) if analyzer_result else []
            self.title = f"peek — {root}"
            self.sub_title = f"{scan_result.stats.get('total_files',0)} files • {analyzer_result.stats.get('graph_nodes',0) if analyzer_result else 0} modules • {elapsed:.2f}s"

        def compose(self) -> ComposeResult:
            yield Header(show_clock=False)
            yield Input(placeholder="Filter files (e.g. auth) — Enter to apply, Esc to clear", id="filter-input")
            with Horizontal(id="main"):
                with VerticalScroll(id="left"):
                    # Summary
                    yield Static(self._summary_renderable(), id="summary")
                    # Tech stack
                    yield Static(self._tech_renderable(), id="tech")
                    # Graph
                    yield Static(self._graph_renderable(), id="graph")
                    # Languages
                    yield Static(self._languages_renderable(), id="langs")
                    # Detail for selected
                    yield Static(self._initial_detail(), id="detail")
                with Vertical(id="right"):
                    yield Label(f" Start Here ⭐  ({len(self._all_ranked)} ranked)", id="right-title")
                    yield ListView(*self._make_list_items(self._all_ranked), id="ranked-list")
            yield Footer()

        # -- render helpers (Rich) --

        def _summary_renderable(self):
            from rich import box
            from rich.panel import Panel

            s = self.analyzer_result.summary if self.analyzer_result else "No analysis"
            return Panel(s, title="[bold]Summary[/]", box=box.ROUNDED, border_style="green", padding=(0, 1))

        def _tech_renderable(self):
            from rich import box
            from rich.panel import Panel

            ts = self.analyzer_result.tech_stack if self.analyzer_result else {}
            ext = self.analyzer_result.external_imports if self.analyzer_result else set()
            lines: list[str] = []
            if ts.get("primary") and ts["primary"] != "unknown":
                lines.append(f"[bold cyan]Primary:[/] {ts['primary']}")
            if ts.get("frameworks"):
                lines.append(f"[bold cyan]Frameworks:[/] {', '.join(ts['frameworks'])}")
            if ext:
                preview = ", ".join(sorted(ext)[:6])
                if len(ext) > 6:
                    preview += f" (+{len(ext)-6})"
                lines.append(f"[bold cyan]External:[/] {preview}")
            if ts.get("configs"):
                lines.append(f"[bold cyan]Configs:[/] {', '.join(ts['configs'][:5])}")
            if not lines:
                return Panel("[dim]No stack detected[/]", title="[bold]Tech Stack[/]", box=box.ROUNDED, border_style="cyan")
            return Panel("\n".join(lines), title="[bold]Tech Stack[/]", box=box.ROUNDED, border_style="cyan", padding=(0, 1))

        def _graph_renderable(self):
            from rich import box
            from rich.panel import Panel

            g = self.analyzer_result.graph if self.analyzer_result else {}
            r = self.analyzer_result.ranked if self.analyzer_result else []
            if not g:
                return Panel("[dim]No graph[/]", title="[bold]Import Graph[/]", box=box.ROUNDED, border_style="white")
            # top hubs
            most = sorted(g.items(), key=lambda kv: len(kv[1]), reverse=True)[:3]
            lines: list[str] = []
            for src, deps in most:
                if not deps:
                    continue
                try:
                    src_rel = src.relative_to(self.root).as_posix()
                except ValueError:
                    src_rel = src.name
                dep_rels = []
                for d in list(deps)[:3]:
                    try:
                        dep_rels.append(d.relative_to(self.root).as_posix())
                    except ValueError:
                        dep_rels.append(d.name)
                suffix = f" (+{len(deps)-3})" if len(deps) > 3 else ""
                lines.append(f"[cyan]{src_rel}[/] → {', '.join(dep_rels)}{suffix}")
            # ascii one-liner
            try:
                from peek._ascii_graph import ascii_graph

                one = ascii_graph(g, r, self.root)
                if one:
                    lines.append(f"[dim]{one}[/]")
            except Exception:
                pass
            if not lines:
                lines = ["[dim]No edges[/]"]
            return Panel("\n".join(lines), title="[bold]Import Graph[/]", box=box.ROUNDED, border_style="white", padding=(0, 1))

        def _languages_renderable(self):
            from rich import box
            from rich.panel import Panel
            from rich.table import Table

            stats = self.scan_result.stats
            by_lang = stats.get("by_lang", {})
            if not by_lang:
                return Static("")
            t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold cyan", padding=(0, 1))
            t.add_column("Lang", style="white")
            t.add_column("Files", justify="right", style="green")
            t.add_column("Bar", style="magenta")
            sorted_langs = sorted(by_lang.items(), key=lambda x: x[1], reverse=True)[:5]
            max_c = sorted_langs[0][1] if sorted_langs else 1
            for lang, cnt in sorted_langs:
                bar_len = int(cnt / max_c * 10) if max_c else 0
                bar = "█" * bar_len + "░" * (10 - bar_len)
                t.add_row(lang, str(cnt), bar)
            return Panel(t, title="[bold]Languages[/]", box=box.ROUNDED, border_style="cyan", padding=(0, 1))

        def _initial_detail(self):
            # detail for first ranked
            if not self._all_ranked:
                return Panel("[dim]No modules[/]", title="[bold]Detail[/]", border_style="yellow")
            first = self._all_ranked[0]
            return _detail_for(first.path, self.analyzer_result.graph, self.analyzer_result.reverse_graph, self.root)

        def _make_list_items(self, ranked):
            items: list[ListItem] = []
            for i, r in enumerate(ranked, 1):
                # score bar hint
                why = ", ".join(r.reasons[:2])
                # Use Label with markup
                label = Label(f"[bold]{i:>2}[/] [white]{r.rel.as_posix()}[/]  [green]{r.score:.1f}[/] [dim]{why}[/]")
                # store path on item for retrieval
                item = ListItem(label, id=f"item-{i}")
                # attach path as attribute (Textual widget allows arbitrary)
                item._peek_path = r.path  # type: ignore[attr-defined]
                item._peek_ranked = r  # type: ignore[attr-defined]
                items.append(item)
            if not items:
                items.append(ListItem(Label("[dim]No files — try filter[/]")))
            return items

        # -- actions --

        def action_quit(self) -> None:
            self.exit()

        def action_cursor_down(self) -> None:
            lv = self.query_one("#ranked-list", ListView)
            lv.action_cursor_down()

        def action_cursor_up(self) -> None:
            lv = self.query_one("#ranked-list", ListView)
            lv.action_cursor_up()

        def action_open_file(self) -> None:
            lv = self.query_one("#ranked-list", ListView)
            item = lv.highlighted_child
            if not item or not hasattr(item, "_peek_path"):
                self.notify("No file selected", severity="warning")
                return
            path: Path = item._peek_path  # type: ignore
            editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or ("notepad" if sys.platform == "win32" else "vi")
            try:
                if sys.platform == "win32" and editor.lower() == "notepad":
                    subprocess.Popen(["notepad", str(path)])
                else:
                    # textual suspend to run editor in terminal
                    with self.suspend():
                        subprocess.call([editor, str(path)])
                self.notify(f"Opened {path.name} in {editor}")
            except Exception as e:
                self.notify(f"Failed to open: {e}", severity="error")

        def action_filter(self) -> None:
            inp = self.query_one("#filter-input", Input)
            inp.add_class("visible")
            inp.focus()
            inp.value = self._filter

        def action_clear_filter(self) -> None:
            inp = self.query_one("#filter-input", Input)
            if "visible" in inp.classes:
                inp.remove_class("visible")
                inp.value = ""
                self._filter = ""
                self._apply_filter()
                self.query_one("#ranked-list", ListView).focus()
            else:
                # if not filtering, quit like q
                pass

        def action_help(self) -> None:
            self.notify("q quit • j/k nav • o open • / filter • enter details • esc clear", timeout=5)

        # -- events --

        @on(ListView.Highlighted)
        def on_highlighted(self, event: ListView.Highlighted) -> None:
            item = event.item
            if not item or not hasattr(item, "_peek_path"):
                return
            path: Path = item._peek_path  # type: ignore
            detail = self.query_one("#detail", Static)
            detail.update(_detail_for(path, self.analyzer_result.graph, self.analyzer_result.reverse_graph, self.root))

        @on(ListView.Selected)
        def on_selected(self, event: ListView.Selected) -> None:
            # same as highlighted but also notify
            item = event.item
            if not item or not hasattr(item, "_peek_path"):
                return
            r = item._peek_ranked  # type: ignore
            self.notify(f"{r.rel.as_posix()} — {', '.join(r.reasons)} • score {r.score:.1f}")

        @on(Input.Submitted)
        def on_input_submitted(self, event: Input.Submitted) -> None:
            self._filter = event.value.strip()
            inp = self.query_one("#filter-input", Input)
            inp.remove_class("visible")
            self._apply_filter()
            self.query_one("#ranked-list", ListView).focus()

        def _apply_filter(self) -> None:
            q = self._filter.lower()
            if not q:
                filtered = self._all_ranked
            else:
                filtered = [r for r in self._all_ranked if q in r.rel.as_posix().lower() or any(q in reason.lower() for reason in r.reasons)]
            lv = self.query_one("#ranked-list", ListView)
            # clear and repopulate
            # textual ListView clear is async but we can do via mount

            async def _rebuild():
                await lv.clear()
                items = self._make_list_items(filtered)
                await lv.extend(items)
                lv.index = 0 if filtered else None
                # update title
                title = self.query_one("#right-title", Label)
                title.update(f" Start Here ⭐  ({len(filtered)}/{len(self._all_ranked)} filtered)" if q else f" Start Here ⭐  ({len(filtered)} ranked)")
                # update detail
                if filtered:
                    detail = self.query_one("#detail", Static)
                    detail.update(_detail_for(filtered[0].path, self.analyzer_result.graph, self.analyzer_result.reverse_graph, self.root))

            self.run_worker(_rebuild(), exclusive=True)


else:  # fallback if textual not installed

    class PeekApp:  # type: ignore
        def __init__(self, *a, **k):
            raise RuntimeError("Textual not installed — run `pip install textual`")


def run_tui(root: Path | str, scan_result=None, analyzer_result=None, elapsed: float = 0.0) -> int:
    """Entry point for `peek [PATH]` TUI. Returns exit code.

    If not a TTY or textual missing, falls back to static render.
    """
    from pathlib import Path as _P
    import time

    from rich.console import Console

    root = _P(root).resolve() if isinstance(root, (str, Path)) else _P.cwd()
    if root.is_file():
        root = root.parent

    # Lazy scan/analyze if not provided
    if scan_result is None or analyzer_result is None:
        from peek.scanner import scan
        from peek.analyzer import analyze

        t0 = time.perf_counter()
        sr = scan(root)
        ar = analyze(sr)
        elapsed = time.perf_counter() - t0
        scan_result, analyzer_result = sr, ar

    # Not a TTY or no textual? Fall back to static
    if not TEXTUAL_AVAILABLE:
        from rich.console import Console

        console = Console(legacy_windows=False)
        from peek.renderer import render_static

        render_static(scan_result, analyzer_result, elapsed, console)
        console.print("\n[dim]Install TUI: [bold]pip install textual[/] for interactive mode.[/]")
        return 0

    # Check if stdout is a tty — if not, don't launch TUI (CI / pipe)
    if not sys.stdout.isatty() and not sys.stderr.isatty():
        # Still launch? But for piped usage, static is better
        # We respect --no-tui fallback; caller should have checked.
        # For now, render static if not tty and return
        from rich.console import Console

        console = Console(legacy_windows=False)
        from peek.renderer import render_static

        render_static(scan_result, analyzer_result, elapsed, console)
        return 0

    app = PeekApp(root, scan_result, analyzer_result, elapsed)
    return app.run() or 0
