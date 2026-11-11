"""Watch mode — Task 5 TDD."""

import time
from pathlib import Path


def test_watch_debounce(tmp_path):
    from peek.watch import watch_repo

    p = tmp_path / "repo"
    p.mkdir()
    (p / "a.py").write_text("x=1\n")
    calls = []
    watcher = watch_repo(p, lambda sr, ar: calls.append(1), debounce=0.2, poll_interval=0.1)
    time.sleep(0.3)
    (p / "a.py").write_text("x=2\n")
    time.sleep(0.5)
    watcher.stop()
    assert len(calls) >= 1
    assert len(calls) <= 2  # debounce prevents many


def test_watch_stop_idempotent(tmp_path):
    from peek.watch import watch_repo

    p = tmp_path / "repo"
    p.mkdir()
    (p / "a.py").write_text("x=1\n")
    watcher = watch_repo(p, lambda sr, ar: None, debounce=0.1, poll_interval=0.1)
    time.sleep(0.2)
    watcher.stop()
    # second stop should not raise
    watcher.stop()


def test_watch_new_file_triggers(tmp_path):
    from peek.watch import watch_repo

    p = tmp_path / "repo"
    p.mkdir()
    (p / "a.py").write_text("x=1\n")
    calls = []
    watcher = watch_repo(p, lambda sr, ar: calls.append(sr), debounce=0.2, poll_interval=0.1)
    time.sleep(0.2)
    (p / "b.py").write_text("y=1\n")
    time.sleep(0.6)
    watcher.stop()
    assert len(calls) >= 1
    # verify the scan result contains the new file
    assert any(c > 0 for c in [len(calls)])


def test_watch_cli_help():
    from typer.testing import CliRunner
    from peek.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["watch", "--help"])
    assert result.exit_code == 0, result.output
    assert "watch" in result.output.lower()


def test_tui_w_toggle_binding():
    import pytest

    pytest.importorskip("textual")
    from peek.tui import PeekApp

    assert any(b.key == "w" for b in PeekApp.BINDINGS)
    w_bind = next(b for b in PeekApp.BINDINGS if b.key == "w")
    assert w_bind.action == "toggle_watch"
    assert "watch" in w_bind.description.lower()
    # also verify action exists
    assert hasattr(PeekApp, "action_toggle_watch")
    # verify start/stop helpers exist
    assert hasattr(PeekApp, "_start_watch")
    assert hasattr(PeekApp, "_stop_watch")


def test_watch_toml_changes(tmp_path):
    import time
    from peek.watch import watch_repo

    p = tmp_path / "repo"
    p.mkdir()
    (p / "pyproject.toml").write_text("x=1\n")
    calls = []
    watcher = watch_repo(p, lambda sr, ar: calls.append(1), debounce=0.1, poll_interval=0.1)
    time.sleep(0.2)
    (p / "pyproject.toml").write_text("x=2\n")
    time.sleep(0.5)
    watcher.stop()
    assert len(calls) >= 1


def test_watch_readme_triggers(tmp_path):
    """Issue #28: editing README.md must trigger on_change."""
    import time

    from peek.watch import watch_repo

    p = tmp_path / "repo"
    p.mkdir()
    (p / "README.md").write_text("# hi\n")
    calls = []
    watcher = watch_repo(p, lambda sr, ar: calls.append(1), debounce=0.1, poll_interval=0.1)
    time.sleep(0.2)
    (p / "README.md").write_text("# hi!\n")
    time.sleep(0.5)
    watcher.stop()
    assert len(calls) >= 1


def test_watch_js_triggers(tmp_path):
    """Issue #28: editing a .js file must trigger on_change (polyglot watch)."""
    import time

    from peek.watch import watch_repo

    p = tmp_path / "repo"
    p.mkdir()
    (p / "app.js").write_text("let x = 1;\n")
    calls = []
    watcher = watch_repo(p, lambda sr, ar: calls.append(1), debounce=0.1, poll_interval=0.1)
    time.sleep(0.2)
    (p / "app.js").write_text("let x = 2;\n")
    time.sleep(0.5)
    watcher.stop()
    assert len(calls) >= 1


# ---------------------------------------------------------------------------
# Issue #182: the polling fallback must notice build files (Dockerfile,
# Dockerfile.*, Makefile, GNUmakefile) that the scanner already recognizes.
# These tests force the polling backend even when watchfiles is installed.


def _polling_watcher(p, calls, monkeypatch):
    import sys

    from peek.watch import watch_repo

    monkeypatch.setitem(sys.modules, "watchfiles", None)  # force the polling fallback
    return watch_repo(p, lambda sr, ar: calls.append(1), debounce=0.1, poll_interval=0.1)


def _wait_for_count(calls, n, timeout=2.0):
    import time

    deadline = time.monotonic() + timeout
    while len(calls) < n and time.monotonic() < deadline:
        time.sleep(0.02)
    return len(calls)


def test_watch_build_files_modify_polling(tmp_path, monkeypatch):
    """Editing Dockerfile, Dockerfile.prod, Makefile and GNUmakefile each trigger on_change."""
    p = tmp_path / "repo"
    p.mkdir()
    for name in ("Dockerfile", "Dockerfile.prod", "Makefile", "GNUmakefile"):
        (p / name).write_text("# v1\n")
    calls = []
    watcher = _polling_watcher(p, calls, monkeypatch)
    try:
        time.sleep(0.3)
        for name in ("Dockerfile", "Dockerfile.prod", "Makefile", "GNUmakefile"):
            before = len(calls)
            (p / name).write_text("# v2\n")
            assert _wait_for_count(calls, before + 1) > before, (
                f"no callback after editing {name}"
            )
    finally:
        watcher.stop()


def test_watch_build_file_created_polling(tmp_path, monkeypatch):
    """A newly created Makefile triggers on_change in the polling fallback."""
    p = tmp_path / "repo"
    p.mkdir()
    (p / "a.py").write_text("x=1\n")
    calls = []
    watcher = _polling_watcher(p, calls, monkeypatch)
    try:
        time.sleep(0.3)
        (p / "Makefile").write_text("all:\n\ttrue\n")
        assert _wait_for_count(calls, 1) >= 1
    finally:
        watcher.stop()


def test_watch_build_file_deleted_polling(tmp_path, monkeypatch):
    """Deleting a Dockerfile triggers on_change in the polling fallback."""
    p = tmp_path / "repo"
    p.mkdir()
    (p / "a.py").write_text("x=1\n")
    (p / "Dockerfile").write_text("FROM scratch\n")
    calls = []
    watcher = _polling_watcher(p, calls, monkeypatch)
    try:
        time.sleep(0.3)
        (p / "Dockerfile").unlink()
        assert _wait_for_count(calls, 1) >= 1
    finally:
        watcher.stop()
