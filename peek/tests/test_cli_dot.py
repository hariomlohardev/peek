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


def test_scan_empty_dir_suggests_help(tmp_path):
    """An empty scan should point somewhere, not just state the fact."""
    from typer.testing import CliRunner
    from peek.cli import app

    r = CliRunner().invoke(app, ["scan", str(tmp_path)])

    assert r.exit_code == 0
    assert "No files found" in r.output
    assert "peek --help" in r.output


def test_analyze_empty_dir_suggests_help(tmp_path):
    """analyze shares the helper, so it must say the same thing."""
    from typer.testing import CliRunner
    from peek.cli import app

    r = CliRunner().invoke(app, ["analyze", str(tmp_path)])

    assert r.exit_code == 0
    assert "No files found" in r.output
    assert "peek --help" in r.output


def test_non_empty_scan_does_not_warn(tmp_path):
    """The hint must not appear when there was nothing wrong."""
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    from typer.testing import CliRunner
    from peek.cli import app

    r = CliRunner().invoke(app, ["scan", str(tmp_path)])

    assert r.exit_code == 0
    assert "No files found" not in r.output


def test_peek_dot_help():
    """`peek . --help` shows the same as `peek --help`."""
    r_dot = runner.invoke(app, [".", "--help"])
    r_main = runner.invoke(app, ["--help"])
    assert r_dot.exit_code == 0
    assert r_main.exit_code == 0
    assert r_dot.output == r_main.output

