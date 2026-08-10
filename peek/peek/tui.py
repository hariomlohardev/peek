"""TUI — Textual app for peek · Lab Notebook No.01

`peek` (no args) launches interactive lab notebook.
Every sheet is paper on graph-paper, tape holds it, signal highlighter marks the one thing.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from rich.console import RenderableType
from rich.panel import Panel

try:
    from textual import on
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Horizontal, Vertical, VerticalScroll
    from textual.widgets import Footer, Header, Input, Label, ListItem, ListView, Static

    TEXTUAL_AVAILABLE = True
except Exception:  # pragma: no cover
    TEXTUAL_AVAILABLE = False
    App = object  # type: ignore
    ComposeResult = None  # type: ignore


# Lab tokens — duplicated from overview.html (do not edit values)
LAB = {
    "paper": "#FFFEFB",
    "paper2": "#F3F0E8",
    "sheet": "#FFFFFF",
    "ink": "#0B1220",
    "ink2": "#1A2744",
    "muted": "#6E7D9A",
    "line": "#D9E2EF",
    "line2": "#B9C8E2",
    "signal": "#FFD400",
    "signal_soft": "#FFF4B3",
    "red": "#E10600",
    "blue": "#0050FF",
    "green": "#0E9F6E",
}


def _detail_for(path: Path, graph, reverse_graph, root: Path) -> RenderableType:
    """Lab sheet detail — washi tape + ink border."""
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
            lines.append(f"[bold {LAB['ink']}]Imports:[/] [{LAB['ink2']}]{deps}{suffix}[/]")
        else:
            lines.append(f"[dim {LAB['muted']}]Imports: none[/]")
        if imported_by:
            ib = ", ".join(_rel(p) for p in sorted(imported_by, key=lambda x: x.name)[:5])
            suffix = f" (+{len(imported_by)-5} more)" if len(imported_by) > 5 else ""
            lines.append(f"[bold {LAB['ink']}]Imported by:[/] [{LAB['blue']}]{ib}{suffix}[/]")
        else:
            lines.append(f"[dim {LAB['muted']}]Imported by: none (leaf / entry)[/]")
        try:
            size = path.stat().st_size
            lines.append(f"[dim {LAB['muted']}]Size: {size} bytes · {path.suffix or 'no ext'} · sheet on paper[/]")
        except Exception:
            pass
        return Panel(
            "\n".join(lines),
            title=f"[bold {LAB['ink']} on {LAB['signal']} ] {_rel(path)} [/]",
            subtitle=f"[{LAB['muted']}]tape · ink · signal[/]",
            border_style=LAB["ink"],
            padding=(0, 1),
            style=f"on {LAB['sheet']}",
        )
    except Exception as e:
        return Panel(f"[{LAB['red']}]Error: {e}[/]", title="Detail", border_style=LAB["red"])


if TEXTUAL_AVAILABLE:

    class PeekApp(App):  # type: ignore
        """Peek TUI — Lab Notebook No.01 · htop for codebases."""

        TITLE = "peek — Lab Notebook No.01"
        SUB_TITLE = "Graph Paper · Sheet · Tape · Signal"

        # Lab Notebook — Graph-paper background via solid paper, sheets with ink borders, signal tape
        CSS = f"""
        Screen {{
            background: {LAB['paper']};
            color: {LAB['ink']};
        }}
        Header {{
            background: rgba(255,254,251,0.88);
            color: {LAB['ink']};
            border-bottom: tall {LAB['line']};
            dock: top;
            height: 3;
        }}
        HeaderTitle {{
            color: {LAB['ink']};
        }}
        #main {{
            layout: horizontal;
            height: 1fr;
            background: {LAB['paper']};
            /* graph-paper is web-only; TUI uses solid paper + ink borders to evoke same */
        }}
        #left {{
            width: 1.2fr;
            min-width: 42;
            height: 1fr;
            overflow-y: auto;
            padding-right: 1;
            background: {LAB['paper']};
        }}
        #right {{
            width: 1fr;
            min-width: 32;
            height: 1fr;
            border: tall {LAB['ink']};
            background: {LAB['sheet']};
        }}
        #right-title {{
            width: 100%;
            height: 3;
            background: {LAB['ink']};
            color: {LAB['signal']};
            text-style: bold;
            padding: 0 1;
            content-align: center middle;
        }}
        #detail {{
            height: auto;
            max-height: 9;
            dock: bottom;
            border: tall {LAB['ink']};
            background: {LAB['sheet']};
        }}
        ListView {{
            height: 1fr;
            background: {LAB['sheet']};
        }}
        ListView > ListItem {{
            color: {LAB['ink']};
            background: {LAB['sheet']};
            border-bottom: solid {LAB['line']};
        }}
        ListView > ListItem.-highlight {{
            color: {LAB['ink']};
            background: {LAB['signal_soft']};
            border-bottom: solid {LAB['signal']};
        }}
        ListView:focus > ListItem.-highlight {{
            background: {LAB['signal']};
            color: {LAB['ink']};
            text-style: bold;
        }}
        ListItem {{
            padding: 0 1;
            height: auto;
        }}
        #filter-input {{
            display: none;
            dock: top;
            height: 3;
            border: tall {LAB['ink']};
            background: {LAB['sheet']};
        }}
        #filter-input.visible {{
            display: block;
        }}
        Input {{
            border: tall {LAB['line']};
            background: {LAB['paper']};
        }}
        Input:focus {{
            border: tall {LAB['ink']};
        }}
        Footer {{
            background: {LAB['paper2']};
            color: {LAB['muted']};
            border-top: tall {LAB['ink']};
        }}
        Label {{
            color: {LAB['ink']};
        }}
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
            self.title = f"◈ PEEK — LAB 01 — {root.name} — {elapsed:.2f}s"
            self.sub_title = f"{scan_result.stats.get('total_files',0)} files · {analyzer_result.stats.get('graph_nodes',0) if analyzer_result else 0} modules · signal tape"

        def compose(self) -> ComposeResult:
            yield Header(show_clock=False)
            yield Input(placeholder="Filter files (e.g. auth) — Enter to apply, Esc to clear · graph-paper · sheet · tape", id="filter-input")
            with Horizontal(id="main"):
                with VerticalScroll(id="left"):
                    yield Static(self._summary_renderable(), id="summary")
                    yield Static(self._tech_renderable(), id="tech")
                    yield Static(self._graph_renderable(), id="graph")
                    yield Static(self._languages_renderable(), id="langs")
                    yield Static(self._initial_detail(), id="detail")
                with Vertical(id="right"):
                    yield Label(f" Start Here ⭐  Lab — {len(self._all_ranked)} ranked · washi tape", id="right-title")
                    yield ListView(*self._make_list_items(self._all_ranked), id="ranked-list")
            yield Footer()

        def _summary_renderable(self):
            from rich import box
            from rich.panel import Panel

            s = self.analyzer_result.summary if self.analyzer_result else "No analysis"
            return Panel(
                f"[{LAB['ink']}]{s}[/]",
                title=f"[bold {LAB['ink']} on {LAB['signal']}] SUMMARY [/]",
                subtitle=f"[{LAB['muted']}]highlighter · signal[/]",
                box=box.ROUNDED,
                border_style=LAB["ink"],
                padding=(0, 1),
                style=f"on {LAB['sheet']}",
            )

        def _tech_renderable(self):
            from rich import box
            from rich.panel import Panel

            ts = self.analyzer_result.tech_stack if self.analyzer_result else {}
            ext = self.analyzer_result.external_imports if self.analyzer_result else set()
            lines: list[str] = []
            if ts.get("primary") and ts["primary"] != "unknown":
                lines.append(f"[bold {LAB['ink']}]Primary:[/] [{LAB['ink2']}]{ts['primary']}[/]")
            if ts.get("frameworks"):
                lines.append(f"[bold {LAB['ink']}]Frameworks:[/] [{LAB['blue']}]{', '.join(ts['frameworks'])}[/]")
            if ext:
                preview = ", ".join(sorted(ext)[:6])
                if len(ext) > 6:
                    preview += f" (+{len(ext)-6})"
                lines.append(f"[bold {LAB['ink']}]External:[/] [{LAB['muted']}]{preview}[/]")
            if ts.get("configs"):
                lines.append(f"[bold {LAB['ink']}]Configs:[/] [{LAB['muted']}]{', '.join(ts['configs'][:5])}[/]")
            if not lines:
                return Panel(f"[dim {LAB['muted']}]No stack detected[/]", title=f"[bold {LAB['ink']}]Tech Stack[/]", box=box.ROUNDED, border_style=LAB["ink"])
            return Panel("\n".join(lines), title=f"[bold {LAB['ink']}]Tech Stack[/]", subtitle=f"[{LAB['muted']}]sheet · paper-2[/]", box=box.ROUNDED, border_style=LAB["ink"], padding=(0, 1))

        def _graph_renderable(self):
            from rich import box
            from rich.panel import Panel

            g = self.analyzer_result.graph if self.analyzer_result else {}
            r = self.analyzer_result.ranked if self.analyzer_result else []
            if not g:
                return Panel(f"[dim {LAB['muted']}]No graph[/]", title=f"[bold {LAB['ink']}]Import Graph[/]", box=box.ROUNDED, border_style=LAB["ink"])
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
                lines.append(f"[{LAB['blue']}]{src_rel}[/] [{LAB['muted']}]→[/] [{LAB['ink']}]{', '.join(dep_rels)}[/][{LAB['muted']}]{suffix}[/]")
            try:
                from peek._ascii_graph import ascii_graph

                one = ascii_graph(g, r, self.root)
                if one:
                    lines.append(f"[dim {LAB['muted']}]{one}[/]")
            except Exception:
                pass
            if not lines:
                lines = [f"[dim {LAB['muted']}]No edges[/]"]
            return Panel("\n".join(lines), title=f"[bold {LAB['ink']}]Import Graph[/]", box=box.ROUNDED, border_style=LAB["ink"], padding=(0, 1))

        def _languages_renderable(self):
            from rich import box
            from rich.panel import Panel
            from rich.table import Table

            stats = self.scan_result.stats
            by_lang = stats.get("by_lang", {})
            if not by_lang:
                return Static("")
            t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style=f"bold {LAB['ink']}", padding=(0, 1), border_style=LAB["line"])
            t.add_column("Lang", style=LAB["ink"])
            t.add_column("Files", justify="right", style=LAB["green"])
            t.add_column("Bar", style=LAB["signal"])
            sorted_langs = sorted(by_lang.items(), key=lambda x: x[1], reverse=True)[:5]
            max_c = sorted_langs[0][1] if sorted_langs else 1
            for lang, cnt in sorted_langs:
                bar_len = int(cnt / max_c * 10) if max_c else 0
                bar = "█" * bar_len + "░" * (10 - bar_len)
                t.add_row(lang, str(cnt), f"[{LAB['signal']}]{bar}[/]")
            return Panel(t, title=f"[bold {LAB['ink']}]Languages[/]", box=box.ROUNDED, border_style=LAB["ink"], padding=(0, 1))

        def _initial_detail(self):
            if not self._all_ranked:
                return Panel(f"[dim {LAB['muted']}]No modules[/]", title=f"[bold {LAB['ink']}]Detail[/]", border_style=LAB["ink"])
            first = self._all_ranked[0]
            return _detail_for(first.path, self.analyzer_result.graph, self.analyzer_result.reverse_graph, self.root)

        def _make_list_items(self, ranked):
            items: list[ListItem] = []
            for i, r in enumerate(ranked, 1):
                why = ", ".join(r.reasons[:2])
                # signal wash for top 1
                if i == 1:
                    label = Label(f"[bold {LAB['ink']} on {LAB['signal']}]{i:>2}[/] [{LAB['ink']}]{r.rel.as_posix()}[/]  [{LAB['green']}]{r.score:.1f}[/] [dim {LAB['muted']}]{why}[/]")
                else:
                    label = Label(f"[bold {LAB['muted']}]{i:>2}[/] [{LAB['ink']}]{r.rel.as_posix()}[/]  [{LAB['green']}]{r.score:.1f}[/] [dim {LAB['muted']}]{why}[/]")
                item = ListItem(label, id=f"item-{i}")
                item._peek_path = r.path  # type: ignore[attr-defined]
                item._peek_ranked = r  # type: ignore[attr-defined]
                items.append(item)
            if not items:
                items.append(ListItem(Label(f"[dim {LAB['muted']}]No files — try filter[/]")))
            return items

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

        def action_help(self) -> None:
            self.notify("Lab Notebook — q quit · j/k nav · o open · / filter · enter details · esc clear · tape holds the truth", timeout=5)

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
            item = event.item
            if not item or not hasattr(item, "_peek_path"):
                return
            r = item._peek_ranked  # type: ignore
            self.notify(f"{r.rel.as_posix()} — {', '.join(r.reasons)} · score {r.score:.1f}")

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

            async def _rebuild():
                await lv.clear()
                items = self._make_list_items(filtered)
                await lv.extend(items)
                lv.index = 0 if filtered else None
                title = self.query_one("#right-title", Label)
                title.update(f" Start Here ⭐  Lab — {len(filtered)}/{len(self._all_ranked)} filtered" if q else f" Start Here ⭐  Lab — {len(filtered)} ranked · washi tape")
                if filtered:
                    detail = self.query_one("#detail", Static)
                    detail.update(_detail_for(filtered[0].path, self.analyzer_result.graph, self.analyzer_result.reverse_graph, self.root))

            self.run_worker(_rebuild(), exclusive=True)


else:  # fallback if textual not installed

    class PeekApp:  # type: ignore
        def __init__(self, *a, **k):
            raise RuntimeError("Textual not installed — run `pip install textual`")


def run_tui(root: Path | str, scan_result=None, analyzer_result=None, elapsed: float = 0.0) -> int:
    """Entry point for `peek [PATH]` TUI — Lab Notebook."""
    from pathlib import Path as _P
    import time

    from rich.console import Console

    root = _P(root).resolve() if isinstance(root, (str, Path)) else _P.cwd()
    if root.is_file():
        root = root.parent

    if scan_result is None or analyzer_result is None:
        from peek.scanner import scan
        from peek.analyzer import analyze

        t0 = time.perf_counter()
        sr = scan(root)
        ar = analyze(sr)
        elapsed = time.perf_counter() - t0
        scan_result, analyzer_result = sr, ar

    if not TEXTUAL_AVAILABLE:
        from rich.console import Console

        console = Console(legacy_windows=False)
        from peek.renderer import render_static

        render_static(scan_result, analyzer_result, elapsed, console)
        console.print("\n[dim]Install TUI: [bold]pip install textual[/] for Lab Notebook mode.[/]")
        return 0

    if not sys.stdout.isatty() and not sys.stderr.isatty():
        from rich.console import Console

        console = Console(legacy_windows=False)
        from peek.renderer import render_static

        render_static(scan_result, analyzer_result, elapsed, console)
        return 0

    app = PeekApp(root, scan_result, analyzer_result, elapsed)
    return app.run() or 0
