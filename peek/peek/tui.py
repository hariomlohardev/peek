"""TUI — themed for peek

Supports 10 themes. CSS templated from theme tokens.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

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

# Fallback tokens for import-time reference (anthropic-pro)
_FALLBACK = {
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

ANTHRO = _FALLBACK  # keep alias for backward compat


def _tok(theme: Any | None) -> dict[str, str]:
    if theme is None:
        return _FALLBACK
    if hasattr(theme, "tokens"):
        return theme.tokens  # type: ignore[return-value]
    if isinstance(theme, dict):
        return theme
    return _FALLBACK


def _label(theme: Any | None) -> str:
    if theme and hasattr(theme, "id"):
        return str(getattr(theme, "id"))
    return "anthropic-pro"


def _detail_for(path: Path, graph, reverse_graph, root: Path, theme: Any | None = None) -> RenderableType:
    t = _tok(theme)
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
            lines.append(f"[bold {t['ink']}]Imports:[/] [{t['cyan']}]{deps}{suffix}[/]")
        else:
            lines.append(f"[dim {t['muted']}]Imports: none[/]")
        if imported_by:
            ib = ", ".join(_rel(p) for p in sorted(imported_by, key=lambda x: x.name)[:5])
            suffix = f" (+{len(imported_by)-5} more)" if len(imported_by) > 5 else ""
            lines.append(f"[bold {t['ink']}]Imported by:[/] [{t['accent']}]{ib}{suffix}[/]")
        else:
            lines.append(f"[dim {t['muted']}]Imported by: none — leaf[/]")
        try:
            size = path.stat().st_size
            lines.append(f"[dim {t['muted']}]Size: {size} bytes · {path.suffix or 'no ext'}[/]")
        except Exception:
            pass
        return Panel(
            "\n".join(lines),
            title=f"[bold {t['ink']}]{_rel(path)}[/]",
            subtitle=f"[{t['muted']}]detail — {_label(theme)}[/]",
            border_style=t["line"],
            padding=(0, 1),
            style=f"on {t['panel']}",
        )
    except Exception as e:
        return Panel(f"[{t['accent2']}]Error: {e}[/]", title="Detail", border_style=t["line"])


if TEXTUAL_AVAILABLE:

    class PeekApp(App):  # type: ignore
        TITLE = "peek — themed — htop for codebases"
        SUB_TITLE = "10 themes"

        # CSS will be set dynamically in __init__ based on theme

        BINDINGS = [
            Binding("q", "quit", "Quit"),
            Binding("o", "open_file", "Open"),
            Binding("/", "filter", "Filter"),
            Binding("?", "help", "Help"),
            Binding("escape", "clear_filter", "Clear", show=False),
            Binding("j", "cursor_down", "Down", show=False),
            Binding("k", "cursor_up", "Up", show=False),
        ]

        def __init__(self, root: Path, scan_result, analyzer_result, elapsed: float, theme: Any | None = None):
            super().__init__()
            self.root = root
            self.scan_result = scan_result
            self.analyzer_result = analyzer_result
            self.elapsed = elapsed
            self._theme = theme
            self._tokens = _tok(theme)
            self._label = _label(theme)
            self._filter = ""
            self._all_ranked = list(analyzer_result.ranked) if analyzer_result else []
            self.title = f"peek — {root.name}"
            self.sub_title = f"{scan_result.stats.get('total_files',0)} files · {elapsed:.2f}s · {self._label}"
            t = self._tokens
            # Dynamic CSS from tokens
            self.CSS = f"""
        Screen {{
            background: {t['bg']};
            color: {t['ink']};
        }}
        Header {{
            background: {t['bg2']};
            color: {t['ink']};
            dock: top;
            height: 3;
            border-bottom: solid {t['line']};
        }}
        HeaderTitle {{
            color: {t['ink']};
        }}
        #main {{
            layout: horizontal;
            height: 1fr;
            background: {t['bg']};
        }}
        #left {{
            width: 1.28fr;
            min-width: 46;
            height: 1fr;
            overflow-y: auto;
            padding-right: 1;
            background: {t['bg']};
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
            border: solid {t['line']};
            background: {t['surface']};
            opacity: 0;
            transition: opacity 220ms ease-out 60ms;
        }}
        #right.in {{
            opacity: 1;
        }}
        #right-title {{
            width: 100%;
            height: 3;
            background: {t['panel']};
            color: {t['muted']};
            text-style: bold;
            padding: 0 1;
            content-align: center middle;
            border-bottom: solid {t['line']};
        }}
        #detail {{
            height: auto;
            max-height: 9;
            dock: bottom;
            border: solid {t['line']};
            background: {t['panel']};
            opacity: 0;
            transition: opacity 180ms ease-out;
        }}
        #detail.in {{
            opacity: 1;
        }}
        ListView {{
            height: 1fr;
            background: {t['surface']};
        }}
        ListView > ListItem {{
            color: {t['ink']};
            background: {t['surface']};
            border-bottom: solid {t['line']};
            opacity: 0;
            transition: opacity 160ms ease-out, background 120ms ease-out;
        }}
        ListView > ListItem.in {{
            opacity: 1;
        }}
        ListView > ListItem.-highlight {{
            background: {t['panel']};
            color: {t['ink']};
            border-left: solid {t['accent']};
        }}
        ListView:focus > ListItem.-highlight {{
            background: {t['accent']};
            color: {t['bg']};
        }}
        #filter-input {{
            display: none;
            dock: top;
            height: 3;
            border: solid {t['accent']};
            background: {t['panel']};
        }}
        #filter-input.visible {{
            display: block;
        }}
        Input {{
            background: {t['bg2']};
            border: solid {t['line']};
        }}
        Input:focus {{
            border: solid {t['accent']};
        }}
        Footer {{
            background: {t['bg2']};
            color: {t['muted']};
            border-top: solid {t['line']};
        }}
        """

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
                    yield Label(f" Start Here  ·  {len(self._all_ranked)} ranked  ·  {self._label}", id="right-title")
                    yield ListView(*self._make_list_items(self._all_ranked), id="ranked-list")
            yield Footer()

        def on_mount(self) -> None:
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
            t = self._tokens
            return Panel(
                f"[{t['ink']}]{s}[/]",
                title=f"[bold {t['ink']}]Summary[/]",
                subtitle=f"[{t['muted']}]{self._label}[/]",
                box=box.ROUNDED,
                border_style=t["line"],
                padding=(0, 1),
                style=f"on {t['panel']}",
            )

        def _tech_renderable(self):
            from rich import box
            from rich.panel import Panel

            ts = self.analyzer_result.tech_stack if self.analyzer_result else {}
            ext = self.analyzer_result.external_imports if self.analyzer_result else set()
            t = self._tokens
            lines: list[str] = []
            if ts.get("primary") and ts["primary"] != "unknown":
                lines.append(f"[bold {t['ink']}]Primary:[/] {ts['primary']}")
            if ts.get("frameworks"):
                lines.append(f"[bold {t['ink']}]Frameworks:[/] {', '.join(ts['frameworks'])}")
            if ext:
                preview = ", ".join(sorted(ext)[:6])
                if len(ext) > 6:
                    preview += f" (+{len(ext)-6})"
                lines.append(f"[dim {t['muted']}]External:[/] {preview}")
            if ts.get("configs"):
                lines.append(f"[dim {t['muted']}]Configs:[/] {', '.join(ts['configs'][:5])}")
            if not lines:
                return Panel(f"[dim {t['muted']}]No stack detected[/]", title="[bold]Tech Stack[/]", box=box.ROUNDED, border_style=t["line"])
            return Panel("\n".join(lines), title=f"[bold {t['ink']}]Tech Stack[/]", box=box.ROUNDED, border_style=t["line"], padding=(0, 1), style=f"on {t['panel']}")

        def _graph_renderable(self):
            from rich import box
            from rich.panel import Panel

            g = self.analyzer_result.graph if self.analyzer_result else {}
            r = self.analyzer_result.ranked if self.analyzer_result else []
            t = self._tokens
            if not g:
                return Panel(f"[dim {t['muted']}]No graph[/]", title=f"[bold {t['ink']}]Import Graph[/]", box=box.ROUNDED, border_style=t["line"])
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
                lines.append(f"[{t['cyan']}]{src_rel}[/] [{t['muted']}]→[/] {', '.join(dep_rels)}{suffix}")
            try:
                from peek._ascii_graph import ascii_graph

                one = ascii_graph(g, r, self.root)
                if one:
                    lines.append(f"[dim {t['muted']}]{one}[/]")
            except Exception:
                pass
            if not lines:
                lines = [f"[dim {t['muted']}]No edges[/]"]
            return Panel("\n".join(lines), title=f"[bold {t['ink']}]Import Graph[/]", box=box.ROUNDED, border_style=t["line"], padding=(0, 1))

        def _languages_renderable(self):
            from rich import box
            from rich.panel import Panel
            from rich.table import Table

            stats = self.scan_result.stats
            by_lang = stats.get("by_lang", {})
            t = self._tokens
            if not by_lang:
                return Static("")
            tbl = Table(box=box.SIMPLE_HEAD, show_header=True, header_style=f"bold {t['muted']}", padding=(0, 1), border_style=t["line"])
            tbl.add_column("Lang", style=t["ink"])
            tbl.add_column("Files", justify="right", style=t["ink"])
            tbl.add_column("Bar", style=t["accent"])
            sorted_langs = sorted(by_lang.items(), key=lambda x: x[1], reverse=True)[:5]
            max_c = sorted_langs[0][1] if sorted_langs else 1
            for lang, cnt in sorted_langs:
                bar_len = int(cnt / max_c * 14) if max_c else 0
                bar = "█" * bar_len + "░" * (14 - bar_len)
                tbl.add_row(lang, str(cnt), bar)
            return Panel(tbl, title=f"[bold {t['ink']}]Languages[/]", box=box.ROUNDED, border_style=t["line"], padding=(0, 1))

        def _initial_detail(self):
            t = self._tokens
            if not self._all_ranked:
                return Panel(f"[dim {t['muted']}]No modules[/]", title=f"[bold {t['ink']}]Detail[/]", border_style=t["line"])
            first = self._all_ranked[0]
            return _detail_for(first.path, self.analyzer_result.graph, self.analyzer_result.reverse_graph, self.root, self._theme)

        def _make_list_items(self, ranked):
            t = self._tokens
            items: list[ListItem] = []
            for i, r in enumerate(ranked, 1):
                why = ", ".join(r.reasons[:2])
                label = Label(f"[dim {t['muted']}]{i:>2}[/] [{t['ink']}]{r.rel.as_posix()}[/]  [dim {t['muted']}]{r.score:.1f} · {why}[/]")
                item = ListItem(label, id=f"item-{i}")
                item._peek_path = r.path  # type: ignore[attr-defined]
                item._peek_ranked = r  # type: ignore[attr-defined]
                items.append(item)
            if not items:
                items.append(ListItem(Label(f"[dim {t['muted']}]No files — try filter[/]")))
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
            self.notify(f"{self._label} — q quit · j/k nav · o open · / filter · enter details · esc clear · theme: {self._label}", timeout=4)

        @on(ListView.Highlighted)
        def on_highlighted(self, event: ListView.Highlighted) -> None:
            item = event.item
            if not item or not hasattr(item, "_peek_path"):
                return
            path: Path = item._peek_path  # type: ignore
            detail = self.query_one("#detail", Static)
            detail.update(_detail_for(path, self.analyzer_result.graph, self.analyzer_result.reverse_graph, self.root, self._theme))

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
                for idx, it in enumerate(items):
                    await asyncio.sleep(0.012)
                    try:
                        it.add_class("in")
                    except Exception:
                        pass
                title = self.query_one("#right-title", Label)
                title.update(f" Start Here  ·  {len(filtered)}/{len(self._all_ranked)} filtered · {self._label}" if q else f" Start Here  ·  {len(filtered)} ranked · {self._label}")
                if filtered:
                    detail = self.query_one("#detail", Static)
                    detail.update(_detail_for(filtered[0].path, self.analyzer_result.graph, self.analyzer_result.reverse_graph, self.root, self._theme))

            self.run_worker(_rebuild(), exclusive=True)


else:

    class PeekApp:  # type: ignore
        def __init__(self, *a, **k):
            raise RuntimeError("Textual not installed — run `pip install textual`")


def run_tui(root: Path | str, scan_result=None, analyzer_result=None, elapsed: float = 0.0, theme: Any | None = None) -> int:
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

    # resolve theme if string passed
    if isinstance(theme, str):
        try:
            from peek.themes import get_theme
            theme = get_theme(theme)
        except Exception:
            theme = None

    if not TEXTUAL_AVAILABLE:
        from rich.console import Console

        console = Console(legacy_windows=False)
        from peek.renderer import render_static

        render_static(scan_result, analyzer_result, elapsed, console, theme=theme)
        console.print("\n[dim]Install TUI: [bold]pip install textual[/] for themed view.[/]")
        return 0

    if not sys.stdout.isatty() and not sys.stderr.isatty():
        from rich.console import Console

        console = Console(legacy_windows=False)
        from peek.renderer import render_static

        render_static(scan_result, analyzer_result, elapsed, console, theme=theme)
        return 0

    app = PeekApp(root, scan_result, analyzer_result, elapsed, theme=theme)
    return app.run() or 0
