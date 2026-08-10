"""TUI — Cinematic Terminal for peek · Best Design with Animations

`peek` launches this. Every frame is designed to be screenshot-viral.
Animations: splash typewriter, header pulse, panels slide, bars grow, list stagger, graph draw.

Falls back to static if not a TTY or Textual missing.
"""

from __future__ import annotations

import asyncio
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
    from textual.timer import Timer
    from textual.widgets import Footer, Header, Input, Label, ListItem, ListView, Static

    TEXTUAL_AVAILABLE = True
except Exception:  # pragma: no cover
    TEXTUAL_AVAILABLE = False
    App = object  # type: ignore
    ComposeResult = None  # type: ignore


# Cinematic tokens — sync with animations.py CINE
CINE = {
    "bg": "#070A14",
    "bg2": "#0F1426",
    "surface": "#12182E",
    "panel": "#1A2142",
    "line": "#2A3A6B",
    "ink": "#E6E8F0",
    "muted": "#7A86B6",
    "signal": "#FFE600",
    "signal_soft": "#2A2500",
    "cyan": "#00E5FF",
    "violet": "#B46EFF",
    "green": "#00E676",
    "red": "#FF3B30",
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
            lines.append(f"[bold {CINE['ink']}]Imports:[/] [{CINE['cyan']}]{deps}{suffix}[/]")
        else:
            lines.append(f"[dim {CINE['muted']}]Imports: none[/]")
        if imported_by:
            ib = ", ".join(_rel(p) for p in sorted(imported_by, key=lambda x: x.name)[:5])
            suffix = f" (+{len(imported_by)-5} more)" if len(imported_by) > 5 else ""
            lines.append(f"[bold {CINE['ink']}]Imported by:[/] [{CINE['signal']}]{ib}{suffix}[/]")
        else:
            lines.append(f"[dim {CINE['muted']}]Imported by: none (leaf / entry)[/]")
        try:
            size = path.stat().st_size
            lines.append(f"[dim {CINE['muted']}]Size: {size} bytes · {path.suffix or 'no ext'} · {path.stat().st_mtime:.0f}[/]")
        except Exception:
            pass
        return Panel(
            "\n".join(lines),
            title=f"[bold {CINE['ink']} on {CINE['signal']}] {_rel(path)} [/]",
            subtitle=f"[{CINE['muted']}]◈ cinematic · tape · signal[/]",
            border_style=CINE["signal"],
            padding=(0, 1),
            style=f"on {CINE['panel']}",
        )
    except Exception as e:
        return Panel(f"[{CINE['red']}]Error: {e}[/]", title="Detail", border_style=CINE["red"])


if TEXTUAL_AVAILABLE:

    class PeekApp(App):  # type: ignore
        """Cinematic peek — htop for codebases, best design."""

        TITLE = "peek — cinematic terminal — htop for codebases"
        SUB_TITLE = "Scan · Graph · Rank · Pack — every frame viral"

        CSS = f"""
        Screen {{
            background: {CINE['bg']};
            color: {CINE['ink']};
            layers: base overlay;
        }}
        /* Grain overlay via subtle tint */
        #grain {{
            dock: top;
            height: 1;
            background: {CINE['bg2']};
            color: {CINE['muted']};
            text-align: center;
            display: none;
        }}
        #splash {{
            align: center middle;
            width: 100%;
            height: 100%;
            layer: overlay;
            background: {CINE['bg']} 95%;
            display: none;
        }}
        #splash.visible {{
            display: block;
        }}
        #splash-box {{
            width: 60;
            height: auto;
            border: tall {CINE['signal']};
            background: {CINE['panel']};
            padding: 1 2;
            content-align: center middle;
        }}
        #splash-logo {{
            width: 100%;
            height: 3;
            content-align: center middle;
            color: {CINE['signal']};
            text-style: bold;
        }}
        #splash-sub {{
            width: 100%;
            height: 2;
            content-align: center middle;
            color: {CINE['muted']};
        }}
        Header {{
            background: {CINE['bg2']};
            color: {CINE['ink']};
            border-bottom: tall {CINE['line']};
            dock: top;
            height: 3;
            /* pulse via animate */
        }}
        HeaderTitle {{
            color: {CINE['signal']};
        }}
        #main {{
            layout: horizontal;
            height: 1fr;
            background: {CINE['bg']};
            overflow: hidden;
        }}
        #left {{
            width: 1.25fr;
            min-width: 44;
            height: 1fr;
            overflow-y: auto;
            padding-right: 1;
            background: {CINE['bg']};
            /* slide in */
            offset-x: -100%;
            transition: offset 400ms in_out_cubic;
        }}
        #left.in {{
            offset-x: 0%;
        }}
        #right {{
            width: 1fr;
            min-width: 34;
            height: 1fr;
            border: tall {CINE['line']};
            background: {CINE['surface']};
            offset-x: 100%;
            transition: offset 450ms in_out_cubic 80ms;
        }}
        #right.in {{
            offset-x: 0%;
        }}
        #right-title {{
            width: 100%;
            height: 3;
            background: {CINE['signal']};
            color: {CINE['bg']};
            text-style: bold;
            padding: 1 1;
            content-align: center middle;
        }}
        #detail {{
            height: auto;
            max-height: 9;
            dock: bottom;
            border: tall {CINE['signal']} 50%;
            background: {CINE['panel']};
            opacity: 0;
            transition: opacity 300ms linear;
        }}
        #detail.in {{
            opacity: 1;
        }}
        ListView {{
            height: 1fr;
            background: {CINE['surface']};
        }}
        ListView > ListItem {{
            color: {CINE['ink']};
            background: {CINE['surface']};
            border-bottom: solid {CINE['line']};
            height: auto;
            padding: 0 1;
            opacity: 0;
            transition: opacity 250ms linear, background 200ms linear;
        }}
        ListView > ListItem.in {{
            opacity: 1;
        }}
        ListView > ListItem.-highlight {{
            color: {CINE['bg']};
            background: {CINE['signal']};
            border-bottom: solid {CINE['signal']};
            text-style: bold;
        }}
        ListView:focus > ListItem.-highlight {{
            background: {CINE['signal']};
            color: {CINE['bg']};
        }}
        #filter-input {{
            display: none;
            dock: top;
            height: 3;
            border: tall {CINE['cyan']};
            background: {CINE['panel']};
        }}
        #filter-input.visible {{
            display: block;
        }}
        Input {{
            border: tall {CINE['line']};
            background: {CINE['bg2']};
        }}
        Input:focus {{
            border: tall {CINE['cyan']};
        }}
        Footer {{
            background: {CINE['bg2']};
            color: {CINE['muted']};
            border-top: tall {CINE['line']};
        }}
        #langs-bar {{
            height: 1;
            background: {CINE['bg2']};
            color: {CINE['signal']};
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
            Binding("r", "refresh", "Refresh", show=False),
        ]

        def __init__(self, root: Path, scan_result, analyzer_result, elapsed: float):
            super().__init__()
            self.root = root
            self.scan_result = scan_result
            self.analyzer_result = analyzer_result
            self.elapsed = elapsed
            self._filter = ""
            self._all_ranked = list(analyzer_result.ranked) if analyzer_result else []
            self.title = f"◈ PEEK — CINEMATIC — {root.name} — {elapsed:.2f}s"
            self.sub_title = f"{scan_result.stats.get('total_files',0)} files · {analyzer_result.stats.get('graph_nodes',0) if analyzer_result else 0} modules · {CINE['signal']} pulse"
            self._splash_timer: Timer | None = None

        def compose(self) -> ComposeResult:
            # Grain line
            yield Static("─" * 80, id="grain")
            # Splash overlay
            with Vertical(id="splash"):
                with Vertical(id="splash-box"):
                    yield Static("▮ PEEK", id="splash-logo")
                    yield Static("htop for codebases — typing…", id="splash-sub")
            yield Header(show_clock=False)
            yield Input(placeholder="Filter files (e.g. auth) — Enter to apply, Esc to clear · cinematic", id="filter-input")
            with Horizontal(id="main"):
                with VerticalScroll(id="left"):
                    yield Static(self._summary_renderable(), id="summary")
                    yield Static(self._tech_renderable(), id="tech")
                    yield Static(self._graph_renderable(), id="graph")
                    yield Static(self._languages_renderable(), id="langs")
                    yield Static(self._initial_detail(), id="detail")
                with Vertical(id="right"):
                    yield Label(f" Start Here ⭐  Cinematic — {len(self._all_ranked)} ranked · signal", id="right-title")
                    yield ListView(*self._make_list_items(self._all_ranked), id="ranked-list")
            yield Footer()

        def on_mount(self) -> None:
            # Splash typewriter
            self.query_one("#splash").add_class("visible")
            self._typewriter_splash()
            # Staggered entrance
            self.set_timer(0.6, self._reveal_main)
            # Header pulse loop
            self.set_interval(2.0, self._pulse_header)

        def _typewriter_splash(self) -> None:
            logo = self.query_one("#splash-logo", Static)
            sub = self.query_one("#splash-sub", Static)
            full = "▮ PEEK — CINEMATIC TERMINAL"
            # typewriter effect
            async def _type():
                txt = ""
                for ch in full:
                    txt += ch
                    logo.update(f"[bold {CINE['signal']}]{txt}[/]")
                    await asyncio.sleep(0.03)
                sub.update(f"[{CINE['muted']}]htop for codebases — {self.root} — {len(self._all_ranked)} modules[/]")
                await asyncio.sleep(0.4)
                # hide splash
                self.query_one("#splash").remove_class("visible")
            self.run_worker(_type(), exclusive=True)

        def _reveal_main(self) -> None:
            # slide panels in
            try:
                self.query_one("#left").add_class("in")
                self.query_one("#right").add_class("in")
                self.query_one("#detail").add_class("in")
            except Exception:
                pass
            # stagger list items
            self._stagger_list()

        def _stagger_list(self) -> None:
            lv = self.query_one("#ranked-list", ListView)
            items = list(lv.query("ListItem"))

            async def _stagger():
                for idx, it in enumerate(items):
                    await asyncio.sleep(0.04 + (idx * 0.012))
                    try:
                        it.add_class("in")
                    except Exception:
                        pass

            self.run_worker(_stagger(), exclusive=True)

        def _pulse_header(self) -> None:
            # subtle header pulse — toggle style
            try:
                h = self.query_one(Header)
                # animate background via style transition (fake pulse by toggling class)
                h.add_class("pulse")
                self.set_timer(0.25, lambda: h.remove_class("pulse"))
            except Exception:
                pass

        # -- render helpers --

        def _summary_renderable(self):
            from rich import box
            from rich.panel import Panel

            s = self.analyzer_result.summary if self.analyzer_result else "No analysis"
            return Panel(
                f"[{CINE['ink']}]{s}[/]",
                title=f"[bold {CINE['ink']} on {CINE['signal']}] SUMMARY [/]",
                subtitle=f"[{CINE['muted']}]signal · {self.elapsed:.2f}s[/]",
                box=box.ROUNDED,
                border_style=CINE["signal"],
                padding=(0, 1),
                style=f"on {CINE['panel']}",
            )

        def _tech_renderable(self):
            from rich import box
            from rich.panel import Panel

            ts = self.analyzer_result.tech_stack if self.analyzer_result else {}
            ext = self.analyzer_result.external_imports if self.analyzer_result else set()
            lines: list[str] = []
            if ts.get("primary") and ts["primary"] != "unknown":
                lines.append(f"[bold {CINE['cyan']}]Primary:[/] [{CINE['ink']}]{ts['primary']}[/]")
            if ts.get("frameworks"):
                lines.append(f"[bold {CINE['cyan']}]Frameworks:[/] [{CINE['violet']}]{', '.join(ts['frameworks'])}[/]")
            if ext:
                preview = ", ".join(sorted(ext)[:6])
                if len(ext) > 6:
                    preview += f" (+{len(ext)-6})"
                lines.append(f"[bold {CINE['muted']}]External:[/] [{CINE['muted']}]{preview}[/]")
            if ts.get("configs"):
                lines.append(f"[{CINE['muted']}]Configs:[/] {', '.join(ts['configs'][:4])}")
            if not lines:
                return Panel(f"[dim {CINE['muted']}]No stack detected[/]", title="[bold]Tech Stack[/]", box=box.ROUNDED, border_style=CINE["line"])
            return Panel("\n".join(lines), title=f"[bold {CINE['ink']}]Tech Stack[/]", subtitle=f"[{CINE['muted']}]surface · panel[/]", box=box.ROUNDED, border_style=CINE["line"], padding=(0, 1))

        def _graph_renderable(self):
            from rich import box
            from rich.panel import Panel

            g = self.analyzer_result.graph if self.analyzer_result else {}
            r = self.analyzer_result.ranked if self.analyzer_result else []
            if not g:
                return Panel(f"[dim {CINE['muted']}]No graph[/]", title=f"[bold {CINE['ink']}]Import Graph[/]", box=box.ROUNDED, border_style=CINE["line"])
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
                lines.append(f"[{CINE['cyan']}]{src_rel}[/] [{CINE['muted']}]→[/] [{CINE['ink']}]{', '.join(dep_rels)}[/][{CINE['muted']}]{suffix}[/]")
            try:
                from peek._ascii_graph import ascii_graph

                one = ascii_graph(g, r, self.root)
                if one:
                    lines.append(f"[dim {CINE['muted']}]{one}[/]")
            except Exception:
                pass
            if not lines:
                lines = [f"[dim {CINE['muted']}]No edges[/]"]
            return Panel("\n".join(lines), title=f"[bold {CINE['ink']}]Import Graph[/]", box=box.ROUNDED, border_style=CINE["cyan"], padding=(0, 1))

        def _languages_renderable(self):
            from rich import box
            from rich.panel import Panel
            from rich.table import Table

            stats = self.scan_result.stats
            by_lang = stats.get("by_lang", {})
            if not by_lang:
                return Static("")
            t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style=f"bold {CINE['cyan']}", padding=(0, 1), border_style=CINE["line"])
            t.add_column("Lang", style=CINE["ink"])
            t.add_column("Files", justify="right", style=CINE["green"])
            t.add_column("Bar", style=CINE["signal"])
            sorted_langs = sorted(by_lang.items(), key=lambda x: x[1], reverse=True)[:5]
            max_c = sorted_langs[0][1] if sorted_langs else 1
            for lang, cnt in sorted_langs:
                bar_len = int(cnt / max_c * 14) if max_c else 0
                bar = "█" * bar_len + "░" * (14 - bar_len)
                # bar will be animated via Live in renderer, here static
                t.add_row(lang, str(cnt), f"[{CINE['signal']}]{bar}[/]")
            return Panel(t, title=f"[bold {CINE['ink']}]Languages[/]", box=box.ROUNDED, border_style=CINE["violet"], padding=(0, 1))

        def _initial_detail(self):
            if not self._all_ranked:
                return Panel(f"[dim {CINE['muted']}]No modules[/]", title=f"[bold {CINE['ink']}]Detail[/]", border_style=CINE["line"])
            first = self._all_ranked[0]
            return _detail_for(first.path, self.analyzer_result.graph, self.analyzer_result.reverse_graph, self.root)

        def _make_list_items(self, ranked):
            items: list[ListItem] = []
            for i, r in enumerate(ranked, 1):
                why = ", ".join(r.reasons[:2])
                if i == 1:
                    label = Label(f"[bold {CINE['bg']} on {CINE['signal']}] {i:>2} [/] [{CINE['ink']}]{r.rel.as_posix()}[/]  [{CINE['green']}]{r.score:.1f}[/] [dim {CINE['muted']}]{why}[/]")
                else:
                    label = Label(f"[bold {CINE['muted']}]{i:>2}[/] [{CINE['ink']}]{r.rel.as_posix()}[/]  [{CINE['green']}]{r.score:.1f}[/] [dim {CINE['muted']}]{why}[/]")
                item = ListItem(label, id=f"item-{i}")
                item._peek_path = r.path  # type: ignore[attr-defined]
                item._peek_ranked = r  # type: ignore[attr-defined]
                items.append(item)
            if not items:
                items.append(ListItem(Label(f"[dim {CINE['muted']}]No files — try filter[/]")))
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
            self.notify("Cinematic — q quit · j/k nav · o open · / filter · enter details · r refresh · esc clear", timeout=5)

        def action_refresh(self) -> None:
            # re-animate
            self._reveal_main()
            self.notify("Refreshed — cinematic pulse", timeout=1.5)

        @on(ListView.Highlighted)
        def on_highlighted(self, event: ListView.Highlighted) -> None:
            item = event.item
            if not item or not hasattr(item, "_peek_path"):
                return
            path: Path = item._peek_path  # type: ignore
            detail = self.query_one("#detail", Static)
            # fade detail
            detail.remove_class("in")
            detail.update(_detail_for(path, self.analyzer_result.graph, self.analyzer_result.reverse_graph, self.root))
            self.set_timer(0.05, lambda: detail.add_class("in"))

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
                # stagger again
                for idx, it in enumerate(items):
                    await asyncio.sleep(0.02)
                    try:
                        it.add_class("in")
                    except Exception:
                        pass
                title = self.query_one("#right-title", Label)
                title.update(f" Start Here ⭐  Cinematic — {len(filtered)}/{len(self._all_ranked)} filtered" if q else f" Start Here ⭐  Cinematic — {len(filtered)} ranked · signal")
                if filtered:
                    detail = self.query_one("#detail", Static)
                    detail.update(_detail_for(filtered[0].path, self.analyzer_result.graph, self.analyzer_result.reverse_graph, self.root))
                    detail.add_class("in")

            self.run_worker(_rebuild(), exclusive=True)


else:  # fallback

    class PeekApp:  # type: ignore
        def __init__(self, *a, **k):
            raise RuntimeError("Textual not installed — run `pip install textual`")


def run_tui(root: Path | str, scan_result=None, analyzer_result=None, elapsed: float = 0.0) -> int:
    """Entry point for `peek [PATH]` cinematic TUI."""
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
        console.print("\n[dim]Install TUI: [bold]pip install textual[/] for cinematic mode.[/]")
        return 0

    if not sys.stdout.isatty() and not sys.stderr.isatty():
        from rich.console import Console

        console = Console(legacy_windows=False)
        from peek.renderer import render_static

        render_static(scan_result, analyzer_result, elapsed, console)
        return 0

    app = PeekApp(root, scan_result, analyzer_result, elapsed)
    return app.run() or 0
