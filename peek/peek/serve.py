"""serve — live HTML dashboard on localhost (issue #23) with --open (issue #75)."""

from __future__ import annotations

import contextlib
import functools
import re
import threading
import time
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional

DEFAULT_PORT = 4181


def _inject_reload(html: str, seconds: int) -> str:
    """Insert a meta-refresh tag after <head> (prepend fallback when absent)."""
    tag = f'<meta http-equiv="refresh" content="{seconds}">'
    new_html, n = re.subn(
        r"<head[^>]*>", lambda m: m.group(0) + tag, html, count=1, flags=re.IGNORECASE
    )
    if n == 0:
        return tag + html
    return new_html


def build_report_html(root: Path, theme: Any = None) -> str:
    """Scan + analyze *root* and return the HTML report string."""
    from peek.analyzer import analyze
    from peek.renderer import build_html
    from peek.scanner import scan

    t0 = time.perf_counter()
    sr = scan(root)
    ar = analyze(sr)
    return build_html(sr, ar, time.perf_counter() - t0, theme=theme)


class ReportServer:
    """Serve the peek HTML report; rebuild on file change via watch_repo."""

    def __init__(
        self,
        root: Path,
        port: int = DEFAULT_PORT,
        open_browser: bool = False,
        theme: Any = None,
        directory: Optional[Path] = None,
        watch: bool = True,
        reload_sec: int = 0,
    ) -> None:
        self.root = Path(root)
        if self.root.is_file():
            self.root = self.root.parent
        self.port = port
        self.open_browser = open_browser
        self.theme = theme
        self.directory = Path(directory) if directory else Path.cwd() / ".peek-serve"
        self.use_watch = watch
        self.reload_sec = reload_sec
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._watcher = None

    @property
    def url(self) -> str:
        port = self._server.server_address[1] if self._server else self.port
        return f"http://localhost:{port}"

    def rebuild(self) -> None:
        """Regenerate index.html (also used as the watch on_change callback)."""
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            html = build_report_html(self.root, self.theme)
            if self.reload_sec > 0:
                html = _inject_reload(html, self.reload_sec)
            (self.directory / "index.html").write_text(html, encoding="utf-8")
        except Exception:
            pass

    def _on_change(self, _sr: Any, _ar: Any) -> None:
        self.rebuild()

    def start(self) -> "ReportServer":
        self.rebuild()
        handler = functools.partial(SimpleHTTPRequestHandler, directory=str(self.directory))
        self._server = ThreadingHTTPServer(("127.0.0.1", self.port), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        if self.use_watch:
            try:
                from peek.watch import watch_repo

                self._watcher = watch_repo(self.root, self._on_change)
            except Exception:
                self._watcher = None
        if self.open_browser:
            with contextlib.suppress(Exception):
                webbrowser.open(self.url)
        return self

    def stop(self) -> None:
        try:
            if self._watcher is not None:
                self._watcher.stop()
        except Exception:
            pass
        try:
            if self._server is not None:
                self._server.shutdown()
                self._server.server_close()
        except Exception:
            pass
        try:
            if self._thread is not None:
                self._thread.join(timeout=2.0)
        except Exception:
            pass
