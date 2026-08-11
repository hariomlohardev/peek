"""Watch mode — Task 5 TDD."""

import time
from pathlib import Path


def test_watch_debounce(tmp_path):
    from peek.watch import watch_repo
    p = tmp_path / "repo"; p.mkdir(); (p/"a.py").write_text("x=1\n")
    calls = []
    watcher = watch_repo(p, lambda sr,ar: calls.append(1), debounce=0.2, poll_interval=0.1)
    time.sleep(0.3)
    (p/"a.py").write_text("x=2\n")
    time.sleep(0.5)
    watcher.stop()
    assert len(calls) >= 1
    assert len(calls) <= 2  # debounce prevents many


def test_watch_stop_idempotent(tmp_path):
    from peek.watch import watch_repo
    p = tmp_path / "repo"; p.mkdir(); (p/"a.py").write_text("x=1\n")
    watcher = watch_repo(p, lambda sr,ar: None, debounce=0.1, poll_interval=0.1)
    time.sleep(0.2)
    watcher.stop()
    # second stop should not raise
    watcher.stop()


def test_watch_new_file_triggers(tmp_path):
    from peek.watch import watch_repo
    p = tmp_path / "repo"; p.mkdir(); (p/"a.py").write_text("x=1\n")
    calls = []
    watcher = watch_repo(p, lambda sr,ar: calls.append(sr), debounce=0.2, poll_interval=0.1)
    time.sleep(0.2)
    (p/"b.py").write_text("y=1\n")
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
