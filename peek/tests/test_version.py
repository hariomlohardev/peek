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
