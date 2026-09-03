"""Test peek --version output — GFI #5."""

from typer.testing import CliRunner

from peek import __version__
from peek.cli import app


def test_peek_version_output():
    """`peek --version` prints "peek v<version>" and exits 0."""
    r = CliRunner().invoke(app, ["--version"])
    assert r.exit_code == 0
    assert "peek v" in r.output
    assert __version__ in r.output


def test_peek_version_json_is_valid_json():
    """`peek --version --json` emits a machine-readable payload for CI (#74)."""
    import json
    import sys

    r = CliRunner().invoke(app, ["--version", "--json"])

    assert r.exit_code == 0
    payload = json.loads(r.output)
    assert payload == {
        "name": "peek-code",
        "version": __version__,
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
    }


def test_peek_version_json_carries_no_human_prose():
    """The point is that a parser does not have to strip "peek v" first."""
    r = CliRunner().invoke(app, ["--version", "--json"])

    assert r.exit_code == 0
    assert "peek v" not in r.output


def test_peek_version_plain_is_unchanged_by_the_json_flag():
    """Adding --json must not have altered the default output."""
    r = CliRunner().invoke(app, ["--version"])

    assert r.exit_code == 0
    assert r.output.strip() == f"peek v{__version__}"
