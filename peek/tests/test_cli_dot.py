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


def test_version_flag_prints_version_and_exits_zero():
    """`peek --version` prints "peek v<version>" and exits cleanly."""
    from typer.testing import CliRunner
    from peek import __version__
    from peek.cli import app

    r = CliRunner().invoke(app, ["--version"])

    assert r.exit_code == 0
    assert "peek v" in r.output
    assert __version__ in r.output


def test_version_short_flag_matches():
    """-V is documented as the alias, so it must agree with --version."""
    from typer.testing import CliRunner
    from peek.cli import app

    long_form = CliRunner().invoke(app, ["--version"])
    short_form = CliRunner().invoke(app, ["-V"])

    assert short_form.exit_code == 0
    assert short_form.output == long_form.output

