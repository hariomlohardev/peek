"""watch — polling watcher with optional watchfiles backend."""

from __future__ import annotations

import time
import threading
from pathlib import Path
from typing import Callable


def watch_repo(path: Path, on_change: Callable, debounce: float = 0.4, poll_interval: float = 0.8):
    """Watch *path* for *.py changes, call *on_change(scan_result, analyzer_result)* debounced.

    Uses ``watchfiles`` if available, otherwise polling fallback.
    Returns a ``Watcher`` with ``.stop()`` method.
    """
    path = Path(path)
    try:
        from watchfiles import watch as wwatch  # type: ignore
        has_watchfiles = True
    except ImportError:
        has_watchfiles = False

    stop = threading.Event()
    last_mtime: dict[Path, float] = {}

    # snapshot current mtimes so first poll doesn't fire spuriously
    try:
        for f in path.rglob("*.py"):
            try:
                last_mtime[f] = f.stat().st_mtime
            except FileNotFoundError:
                pass
    except Exception:
        pass

    def poll_loop() -> None:
        while not stop.is_set():
            # wait allows quick stop
            if stop.wait(poll_interval):
                break
            changed = False
            # check modified/new files
            try:
                current_files: set[Path] = set()
                for f in path.rglob("*.py"):
                    current_files.add(f)
                    try:
                        mt = f.stat().st_mtime
                        if last_mtime.get(f) != mt:
                            last_mtime[f] = mt
                            changed = True
                    except FileNotFoundError:
                        pass
                # detect deleted files
                deleted = [k for k in list(last_mtime.keys()) if k not in current_files and not k.exists()]
                if deleted:
                    for k in deleted:
                        last_mtime.pop(k, None)
                    changed = True
            except Exception:
                pass
            if changed:
                if stop.wait(debounce):
                    break
                if stop.is_set():
                    break
                try:
                    from peek.scanner import scan
                    from peek.analyzer import analyze

                    sr = scan(path)
                    ar = analyze(sr)
                    on_change(sr, ar)
                except Exception:
                    pass

    if has_watchfiles:
        def watchfiles_loop() -> None:
            try:
                for changes in wwatch(path, debounce=int(debounce * 1000), step=int(poll_interval * 1000)):  # type: ignore
                    if stop.is_set():
                        break
                    try:
                        from peek.scanner import scan
                        from peek.analyzer import analyze

                        sr = scan(path)
                        ar = analyze(sr)
                        on_change(sr, ar)
                    except Exception:
                        pass
                    if stop.is_set():
                        break
            except Exception:
                # fallback to poll if watchfiles fails (e.g., path deleted)
                poll_loop()

        t = threading.Thread(target=watchfiles_loop, daemon=True)
    else:
        t = threading.Thread(target=poll_loop, daemon=True)
    t.start()

    class Watcher:
        def stop(self) -> None:
            stop.set()
            t.join(timeout=1.0)

    return Watcher()
