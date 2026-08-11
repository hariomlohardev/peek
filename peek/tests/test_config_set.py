"""Config set/get/list with theme validation — Task 3 TDD."""

import pathlib
import tempfile

import pytest
from typer.testing import CliRunner

from peek.cli import app

runner = CliRunner()


def test_config_set_theme(tmp_path, monkeypatch):
    from peek.config import save_config, load_config, config_path
    monkeypatch.setenv("PEEK_CONFIG", str(tmp_path / "cfg.toml"))
    from peek.config import set_config_value
    p = set_config_value("theme", "dracula")
    assert p.exists()
    assert load_config()["theme"] == "dracula"


def test_config_set_validates_theme(tmp_path, monkeypatch):
    from peek.config import set_config_value
    monkeypatch.setenv("PEEK_CONFIG", str(tmp_path / "cfg.toml"))
    with pytest.raises(ValueError, match="Unknown theme"):
        set_config_value("theme", "bogus")


def test_config_set_generic(tmp_path, monkeypatch):
    from peek.config import set_config_value, load_config
    monkeypatch.setenv("PEEK_CONFIG", str(tmp_path / "cfg.toml"))
    p = set_config_value("foo", "bar")
    assert p.exists()
    assert load_config()["foo"] == "bar"
    # theme still validates after generic set
    p2 = set_config_value("theme", "nord")
    assert load_config()["theme"] == "nord"
    assert load_config()["foo"] == "bar"


def test_config_cli_set(tmp_path, monkeypatch):
    monkeypatch.setenv("PEEK_CONFIG", str(tmp_path / "cfg.toml"))
    result = runner.invoke(app, ["config", "set", "theme", "dracula"])
    assert result.exit_code == 0, result.output
    assert "dracula" in result.output
    # verify persisted via get
    result2 = runner.invoke(app, ["config", "get", "theme"])
    assert result2.exit_code == 0
    assert "dracula" in result2.output


def test_config_cli_get_and_list(tmp_path, monkeypatch):
    monkeypatch.setenv("PEEK_CONFIG", str(tmp_path / "cfg.toml"))
    runner.invoke(app, ["config", "set", "theme", "nord"])
    result = runner.invoke(app, ["config", "get", "theme"])
    assert result.exit_code == 0
    assert "nord" in result.output
    # get missing key returns empty
    result_empty = runner.invoke(app, ["config", "get", "nonexistent"])
    assert result_empty.exit_code == 0
    # list should show json with theme
    result_list = runner.invoke(app, ["config", "list"])
    assert result_list.exit_code == 0
    assert "nord" in result_list.output
    assert "theme" in result_list.output.lower() or "nord" in result_list.output


def test_config_cli_set_invalid_theme(tmp_path, monkeypatch):
    monkeypatch.setenv("PEEK_CONFIG", str(tmp_path / "cfg.toml"))
    result = runner.invoke(app, ["config", "set", "theme", "bogus"])
    assert result.exit_code == 2, result.output
    assert "Unknown theme" in result.output or "unknown" in result.output.lower()
