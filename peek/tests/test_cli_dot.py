"""Test peek . dot handling — ensures `peek .` and `peek` work as TUI entry points."""

from typer.testing import CliRunner
from peek.cli import app

runner = CliRunner()


def test_peek_dot_no_tui():
    r = runner.invoke(app, [".", "--no-tui"])
    assert r.exit_code == 0, r.output
    assert "peek" in r.output.lower()
    assert "files" in r.output.lower() or "loc" in r.output.lower()


def test_peek_no_args_no_tui():
    r = runner.invoke(app, ["--no-tui"])
    assert r.exit_code == 0, r.output
    assert "peek" in r.output.lower()


def test_peek_dot_with_theme():
    r = runner.invoke(app, [".", "--theme", "dracula", "--no-tui"])
    assert r.exit_code == 0, r.output


def test_peek_scan_still_works():
    r = runner.invoke(app, ["scan", "--help"])
    assert r.exit_code == 0
    assert "scan" in r.output.lower()


def test_peek_unknown_command_still_fails():
    r = runner.invoke(app, ["nonexistentcmd123"])
    assert r.exit_code != 0
    assert "No such command" in r.output
