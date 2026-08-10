"""TUI — Anthropic Pro for peek

Professional, editorial, warm. Feels like Claude Code in the terminal.
Animations are subtle: 140ms fade, 180ms slide, stagger 18ms — never flashy.
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

ANTHRO = {
    "bg": "#141413",
    "bg2": "#1C1C19",
    "surface": "#232320",
    "panel": "#2A2A27",
    "line": "#3A3936",
    "ink": "#E8E6E3",
    "muted": "#9A9590",
    "accent": "#D4A27F",
    "accent2": "#C4896A",
    "cyan": "#8AB4B8",
}


def _detail_for(path: Path, graph, reverse_graph, root: Path) -> RenderableType:
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
            lines.append(f"[bold {ANTHRO['ink']}]Imports:[/] [{ANTHRO['cyan']}]{deps}{suffix}[/]")
        else:
            lines.append(f"[dim {ANTHRO['muted']}]Imports: none[/]")
        if imported_by:
            ib = ", ".join(_rel(p) for p in sorted(imported_by, key=lambda x: x.name)[:5])
            suffix = f" (+{len(imported_by)-5} more)" if len(imported_by) > 5 else ""
            lines.append(f"[bold {ANTHRO['ink']}]Imported by:[/] [{ANTHRO['accent']}]{ib}{suffix}[/]")
        else:
            lines.append(f"[dim {ANTHRO['muted']}]Imported by: none — leaf[/]")
        try:
            size = path.stat().st_size
            lines.append(f"[dim {ANTHRO['muted']}]Size: {size} bytes · {path.suffix or 'no ext'}[/]")
        except Exception:
            pass
        return Panel(
            "\n".join(lines),
            title=f"[bold {ANTHRO['ink']}]{_rel(path)}[/]",
            subtitle=f"[{ANTHRO['muted']}]detail — anthropic pro[/]",
            border_style=ANTHRO["line"],
            padding=(0, 1),
            style=f"on {ANTHRO['panel']}",
        )
    except Exception as e:
        return Panel(f"[{ANTHRO['accent2']}]Error: {e}[/]", title="Detail", border_style=ANTHRO["line"])


if TEXTUAL_AVAILABLE:

    class PeekApp(App):  # type: ignore
        TITLE = "peek — anthropic pro — htop for codebases"
        SUB_TITLE = "Professional · Warm · Precise"

        CSS = f"""
        Screen {{
            background: {ANTHRO['bg']};
            color: {ANTHRO['ink']};
        }}
        Header {{
            background: {ANTHRO['bg2']};
            color: {ANTHRO['ink']};
            dock: top;
            height: 3;
            border-bottom: solid {ANTHRO['line']};
        }}
        HeaderTitle {{
            color: {ANTHRO['ink']};
        }}
        #main {{
            layout: horizontal;
            height: 1fr;
            background: {ANTHRO['bg']};
        }}
        #left {{
            width: 1.28fr;
            min-width: 46;
            height: 1fr;
            overflow-y: auto;
            padding-right: 1;
            background: {ANTHRO['bg']};
            opacity: 0;
            transition: opacity 220ms ease-out;
        }}
        #left.in {{
            opacity: 1;
        }}
        #right {{
            width: 1fr;
            min-width: 34;
            height: 1fr;
            border: solid {ANTHRO['line']};
            background: {ANTHRO['surface']};
            opacity: 0;
            transition: opacity 220ms ease-out 60ms;
        }}
        #right.in {{
            opacity: 1;
        }}
        #right-title {{
            width: 100%;
            height: 3;
            background: {ANTHRO['panel']};
            color: {ANTHRO['muted']};
            text-style: bold;
            padding: 0 1;
            content-align: center middle;
            border-bottom: solid {ANTHRO['line']};
        }}
        #detail {{
            height: auto;
            max-height: 9;
            dock: bottom;
            border: solid {ANTHRO['line']};
            background: {ANTHRO['panel']};
            opacity: 0;
            transition: opacity 180ms ease-out;
        }}
        #detail.in {{
            opacity: 1;
        }}
        ListView {{
            height: 1fr;
            background: {ANTHRO['surface']};
        }}
        ListView > ListItem {{
            color: {ANTHRO['ink']};
            background: {ANTHRO['surface']};
            border-bottom: solid {ANTHRO['line']};
            opacity: 0;
            transition: opacity 160ms ease-out, background 120ms ease-out;
        }}
        ListView > ListItem.in {{
            opacity: 1;
        }}
        ListView > ListItem.-highlight {{
            background: {ANTHRO['panel']};
            color: {ANTHRO['ink']};
            border-left: solid {ANTHRO['accent']};
        }}
        ListView:focus > ListItem.-highlight {{
            background: {ANTHRO['accent']};
            color: {ANTHRO['bg']};
        }}
        #filter-input {{
            display: none;
            dock: top;
            height: 3;
            border: solid {ANTHRO['accent']};
            background: {ANTHRO['panel']};
        }}
        #filter-input.visible {{
            display: block;
        }}
        Input {{
            background: {ANTHRO['bg2']};
            border: solid {ANTHRO['line']};
        }}
        Input:focus {{
            border: solid {ANTHRO['accent']};
        }}
        Footer {{
            background: {ANTHRO['bg2']};
            color: {ANTHRO['muted']};
            border-top: solid {ANTHRO['line']};
        }}
        """

        BINDINGS = [
            Binding("q", "quit", "Quit"),
            Binding("o", "open_file", "Open"),
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
            self.title = f"peek — {root.name}"
            self.sub_title = f"{scan_result.stats.get('total_files',0)} files · {elapsed:.2f}s · anthropic pro"

        def compose(self) -> ComposeResult:
            yield Header(show_clock=False)
            yield Input(placeholder="Filter — try 'auth' — Enter to apply, Esc to clear", id="filter-input")
            with Horizontal(id="main"):
                with VerticalScroll(id="left"):
                    yield Static(self._summary_renderable(), id="summary")
                    yield Static(self._tech_renderable(), id="tech")
                    yield Static(self._graph_renderable(), id="graph")
                    yield Static(self._languages_renderable(), id="langs")
                    yield Static(self._initial_detail(), id="detail")
                with Vertical(id="right"):
                    yield Label(f" Start Here  ·  {len(self._all_ranked)} ranked", id="right-title")
                    yield ListView(*self._make_list_items(self._all_ranked), id="ranked-list")
            yield Footer()

        def on_mount(self) -> None:
            # Subtle entrance: fade panels, stagger list
            self.set_timer(0.05, self._reveal_panels)
            self.set_timer(0.12, self._stagger_list)

        def _reveal_panels(self) -> None:
            try:
                self.query_one("#left").add_class("in")
                self.query_one("#right").add_class("in")
                self.query_one("#detail").add_class("in")
            except Exception:
                pass

        def _stagger_list(self) -> None:
            lv = self.query_one("#ranked-list", ListView)
            items = list(lv.query("ListItem"))
            import asyncio

            async def _stagger():
                for idx, it in enumerate(items):
                    await asyncio.sleep(0.016 + idx * 0.008)
                    try:
                        it.add_class("in")
                    except Exception:
                        pass

            self.run_worker(_stagger(), exclusive=True)

        def _summary_renderable(self):
            from rich import box
            from rich.panel import Panel

            s = self.analyzer_result.summary if self.analyzer_result else "No analysis"
            return Panel(
                f"[{ANTHRO['ink']}]{s}[/]",
                title=f"[bold {ANTHRO['ink']}]Summary[/]",
                subtitle=f"[{ANTHRO['muted']}]anthropic pro[/]",
                box=box.ROUNDED,
                border_style=ANTHRO["line"],
                padding=(0, 1),
                style=f"on {ANTHRO['panel']}",
            )

        def _tech_renderable(self):
            from rich import box
            from rich.panel import Panel

            ts = self.analyzer_result.tech_stack if self.analyzer_result else {}
            ext = self.analyzer_result.external_imports if self.analyzer_result else set()
            lines: list[str] = []
            if ts.get("primary") and ts["primary"] != "unknown":
                lines.append(f"[bold {ANTHRO['ink']}]Primary:[/] {ts['primary']}")
            if ts.get("frameworks"):
                lines.append(f"[bold {ANTHRO['ink']}]Frameworks:[/] {', '.join(ts['frameworks'])}")
            if ext:
                preview = ", ".join(sorted(ext)[:6])
                if len(ext) > 6:
                    preview += f" (+{len(ext)-6})"
                lines.append(f"[dim {ANTHRO['muted']}]External:[/] {preview}")
            if ts.get("configs"):
                lines.append(f"[dim {ANTHRO['muted']}]Configs:[/] {', '.join(ts['configs'][:5])}")
            if not lines:
                return Panel(f"[dim {ANTHRO['muted']}]No stack detected[/]", title="[bold]Tech Stack[/]", box=box.ROUNDED, border_style=ANTHRO["line"])
            return Panel("\n".join(lines), title=f"[bold {ANTHRO['ink']}]Tech Stack[/]", box=box.ROUNDED, border_style=ANTHRO["line"], padding=(0, 1), style=f"on {ANTHRO['panel']}")

        def _graph_renderable(self):
            from rich import box
            from rich.panel import Panel

            g = self.analyzer_result.graph if self.analyzer_result else {}
            r = self.analyzer_result.ranked if self.analyzer_result else []
            if not g:
                return Panel(f"[dim {ANTHRO['muted']}]No graph[/]", title=f"[bold {ANTHRO['ink']}]Import Graph[/]", box=box.ROUNDED, border_style=ANTHRO["line"])
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
                lines.append(f"[{ANTHRO['cyan']}]{src_rel}[/] [{ANTHRO['muted']}]→[/] {', '.join(dep_rels)}{suffix}")
            try:
                from peek._ascii_graph import ascii_graph

                one = ascii_graph(g, r, self.root)
                if one:
                    lines.append(f"[dim {ANTHRO['muted']}]{one}[/]")
            except Exception:
                pass
            if not lines:
                lines = [f"[dim {ANTHRO['muted']}]No edges[/]"]
            return Panel("\n".join(lines), title=f"[bold {ANTHRO['ink']}]Import Graph[/]", box=box.ROUNDED, border_style=ANTHRO["line"], padding=(0, 1))

        def _languages_renderable(self):
            from rich import box
            from rich.panel import Panel
            from rich.table import Table

            stats = self.scan_result.stats
            by_lang = stats.get("by_lang", {})
            if not by_lang:
                return Static("")
            t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style=f"bold {ANTHRO['muted']}", padding=(0, 1), border_style=ANTHRO["line"])
            t.add_column("Lang", style=ANTHRO["ink"])
            t.add_column("Files", justify="right", style=ANTHRO["ink"])
            t.add_column("Bar", style=ANTHRO["accent"])
            sorted_langs = sorted(by_lang.items(), key=lambda x: x[1], reverse=True)[:5]
            max_c = sorted_langs[0][1] if sorted_langs else 1
            for lang, cnt in sorted_langs:
                bar_len = int(cnt / max_c * 14) if max_c else 0
                bar = "█" * bar_len + "░" * (14 - bar_len)
                t.add_row(lang, str(cnt), bar)
            return Panel(t, title=f"[bold {ANTHRO['ink']}]Languages[/]", box=box.ROUNDED, border_style=ANTHRO["line"], padding=(0, 1))

        def _initial_detail(self):
            if not self._all_ranked:
                return Panel(f"[dim {ANTHRO['muted']}]No modules[/]", title=f"[bold {ANTHRO['ink']}]Detail[/]", border_style=ANTHRO["line"])
            first = self._all_ranked[0]
            return _detail_for(first.path, self.analyzer_result.graph, self.analyzer_result.reverse_graph, self.root)

        def _make_list_items(self, ranked):
            items: list[ListItem] = []
            for i, r in enumerate(ranked, 1):
                why = ", ".join(r.reasons[:2])
                # Professional: no signal wash, just left accent on highlight via CSS
                label = Label(f"[dim {ANTHRO['muted']}]{i:>2}[/] [{ANTHRO['ink']}]{r.rel.as_posix()}[/]  [dim {ANTHRO['muted']}]{r.score:.1f} · {why}[/]")
                item = ListItem(label, id=f"item-{i}")
                item._peek_path = r.path  # type: ignore[attr-defined]
                item._peek_ranked = r  # type: ignore[attr-defined]
                items.append(item)
            if not items:
                items.append(ListItem(Label(f"[dim {ANTHRO['muted']}]No files — try filter[/]")))
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
            self.notify("Anthropic Pro — q quit · j/k nav · o open · / filter · enter details · esc clear", timeout=4)

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
            self.notify(f"{r.rel.as_posix()} — {', '.join(r.reasons)} · {r.score:.1f}")

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
                # stagger in
                for idx, it in enumerate(items):
                    await asyncio.sleep(0.012)
                    try:
                        it.add_class("in")
                    except Exception:
                        pass
                title = self.query_one("#right-title", Label)
                title.update(f" Start Here  ·  {len(filtered)}/{len(self._all_ranked)} filtered" if q else f" Start Here  ·  {len(filtered)} ranked")
                if filtered:
                    detail = self.query_one("#detail", Static)
                    detail.update(_detail_for(filtered[0].path, self.analyzer_result.graph, self.analyzer_result.reverse_graph, self.root))

            self.run_worker(_rebuild(), exclusive=True)


else:

    class PeekApp:  # type: ignore
        def __init__(self, *a, **k):
            raise RuntimeError("Textual not installed — run `pip install textual`")


def run_tui(root: Path | str, scan_result=None, analyzer_result=None, elapsed: float = 0.0) -> int:
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
        console.print("\n[dim]Install TUI: [bold]pip install textual[/] for anthropic pro.[/]")
        return 0

    if not sys.stdout.isatty() and not sys.stderr.isatty():
        from rich.console import Console

        console = Console(legacy_windows=False)
        from peek.renderer import render_static

        render_static(scan_result, analyzer_result, elapsed, console)
        return 0

    app = PeekApp(root, scan_result, analyzer_result, elapsed)
    return app.run() or 0
