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


def test_config_init_creates_the_file_with_the_default_theme(tmp_path, monkeypatch):
    """The acceptance criterion: a config exists with theme = "anthropic-pro"."""
    from peek.config import init_config, load_config

    monkeypatch.setenv("PEEK_CONFIG", str(tmp_path / "nested" / "config.toml"))
    p = init_config()

    assert p.exists()
    assert load_config()["theme"] == "anthropic-pro"


def test_config_init_creates_missing_parent_directories(tmp_path, monkeypatch):
    monkeypatch.setenv("PEEK_CONFIG", str(tmp_path / "a" / "b" / "config.toml"))

    from peek.config import init_config

    assert init_config().exists()


def test_config_init_refuses_to_overwrite(tmp_path, monkeypatch):
    """A config is hand-tuned; `init` must not be a way to lose it by accident."""
    from peek.config import ConfigExistsError, init_config

    monkeypatch.setenv("PEEK_CONFIG", str(tmp_path / "config.toml"))
    init_config()
    (tmp_path / "config.toml").write_text('theme = "dracula"\n', encoding="utf-8")

    with pytest.raises(ConfigExistsError):
        init_config()

    # And the user's edit survived the refusal.
    assert (tmp_path / "config.toml").read_text(encoding="utf-8") == 'theme = "dracula"\n'


def test_config_init_force_overwrites(tmp_path, monkeypatch):
    from peek.config import init_config, load_config

    monkeypatch.setenv("PEEK_CONFIG", str(tmp_path / "config.toml"))
    (tmp_path / "config.toml").write_text('theme = "dracula"\n', encoding="utf-8")

    init_config(force=True)

    assert load_config()["theme"] == "anthropic-pro"


def test_config_init_output_is_valid_toml_and_round_trips(tmp_path, monkeypatch):
    """A scaffold that cannot be parsed is worse than no scaffold."""
    from peek.config import init_config, load_config

    monkeypatch.setenv("PEEK_CONFIG", str(tmp_path / "config.toml"))
    init_config()

    # Only `theme` is live; everything else is commented out on purpose, so a
    # future better default is not silently pinned by a file nobody edited.
    assert load_config() == {"theme": "anthropic-pro"}


def test_config_init_names_a_theme_that_actually_exists(tmp_path, monkeypatch):
    """The scaffold must not ship a theme name the loader would reject."""
    from peek.config import init_config, load_config
    from peek.themes import get_theme

    monkeypatch.setenv("PEEK_CONFIG", str(tmp_path / "config.toml"))
    init_config()

    get_theme(load_config()["theme"])  # raises ValueError if unknown


def test_cli_config_init_exits_2_when_the_file_exists(tmp_path, monkeypatch):
    monkeypatch.setenv("PEEK_CONFIG", str(tmp_path / "config.toml"))

    first = runner.invoke(app, ["config", "init"])
    assert first.exit_code == 0

    second = runner.invoke(app, ["config", "init"])
    assert second.exit_code == 2

    forced = runner.invoke(app, ["config", "init", "--force"])
    assert forced.exit_code == 0
