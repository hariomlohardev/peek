"""Tests for 10-theme system."""

import os
import tempfile
from dataclasses import replace
from pathlib import Path

import pytest

from peek.themes import THEMES, get_theme, list_themes, resolve_theme
from peek.config import load_config, config_path


def test_registry_has_10():
    assert len(THEMES) == 10
    expected = {"anthropic-pro", "cinematic", "dracula", "nord", "catppuccin-mocha", "tokyo-night", "solarized-dark", "github-dark", "monokai", "minimal-mono"}
    assert set(THEMES) == expected


def test_tokens_shape():
    keys = {"bg", "bg2", "surface", "panel", "line", "line2", "ink", "ink2", "muted", "muted2", "accent", "accent2", "cyan", "violet", "green"}
    for th in list_themes():
        assert set(th.tokens) == keys, f"{th.id} bad keys"
        for k, v in th.tokens.items():
            assert isinstance(v, str) and v.startswith("#") and len(v) == 7, f"{th.id} {k}={v}"


def test_get_theme_case_insensitive():
    assert get_theme("Dracula").id == "dracula"
    assert get_theme("DRACULA").id == "dracula"
    assert get_theme("catppuccin_mocha").id == "catppuccin-mocha"
    assert get_theme("  nord  ").id == "nord"


def test_theme_list_sorted():
    """`peek --theme-list` order is by id, case-insensitive and stable."""
    ids = [th.id for th in list_themes()]

    assert ids == sorted(ids, key=str.lower)
    assert len(ids) == len(set(ids))
    # Stable across calls: no dependence on dict iteration or set ordering.
    assert ids == [th.id for th in list_themes()]


def test_theme_list_sorted_ignores_case(monkeypatch):
    """A capitalised id sorts into place rather than jumping to the front.

    Every id in THEMES is lowercase today, so this registers one that is not
    -- otherwise the case-insensitive key is untested and a later plain
    sorted() would pass.
    """
    odd = "Solarized-Light"
    monkeypatch.setitem(THEMES, odd, replace(THEMES["solarized-dark"], id=odd))

    ids = [th.id for th in list_themes()]

    assert ids.index("solarized-dark") + 1 == ids.index(odd)
    assert ids[0] == "anthropic-pro"  # not the capitalised one


def test_get_theme_unknown_raises():
    with pytest.raises(ValueError, match="Unknown theme"):
        get_theme("bogus-theme-xyz")


def test_get_theme_none_fallback():
    assert get_theme(None).id == "anthropic-pro"
    assert get_theme("").id == "anthropic-pro"
    assert get_theme("   ").id == "anthropic-pro"


def test_resolve_precedence_cli_over_env_over_config(monkeypatch, tmp_path):
    # env vs config
    # create tmp config with theme = dracula, env = nord, cli = tokyo-night -> cli wins
    cfg = tmp_path / "config.toml"
    cfg.write_text('theme = "dracula"\n', encoding="utf-8")
    monkeypatch.setenv("PEEK_CONFIG", str(cfg))
    monkeypatch.setenv("PEEK_THEME", "nord")
    # cli overrides env and config
    assert resolve_theme("tokyo-night").id == "tokyo-night"
    # no cli -> env wins over config
    assert resolve_theme(None).id == "nord"
    # no env -> config wins
    monkeypatch.delenv("PEEK_THEME")
    assert resolve_theme(None).id == "dracula"
    # no config -> default
    cfg.unlink()
    assert resolve_theme(None).id == "anthropic-pro"


def test_resolve_config_missing(monkeypatch, tmp_path):
    fake = tmp_path / "nope.toml"
    monkeypatch.setenv("PEEK_CONFIG", str(fake))
    monkeypatch.delenv("PEEK_THEME", raising=False)
    assert resolve_theme(None).id == "anthropic-pro"


def test_config_toml_parse(monkeypatch, tmp_path):
    cfg = tmp_path / "peek.toml"
    cfg.write_text('theme = "dracula"\n', encoding="utf-8")
    monkeypatch.setenv("PEEK_CONFIG", str(cfg))
    assert load_config().get("theme") == "dracula"
    # malformed -> returns {}
    cfg.write_text("not toml {{{", encoding="utf-8")
    assert load_config() == {}


def test_render_static_all_themes_no_crash():
    from peek.scanner import scan
    from peek.analyzer import analyze
    from peek.renderer import render_static
    from rich.console import Console
    import io

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "a.py").write_text("x=1\n", encoding="utf-8")
        sr = scan(root)
        ar = analyze(sr)
        for th in list_themes():
            c = Console(file=io.StringIO(), force_terminal=True, width=80, legacy_windows=False)
            # should not raise
            render_static(sr, ar, 0.01, c, animate=False, theme=th)


def test_build_html_all_themes_contains():
    from peek.scanner import scan
    from peek.analyzer import analyze
    from peek.renderer import build_html

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "a.py").write_text("x=1\n", encoding="utf-8")
        sr = scan(root)
        ar = analyze(sr)
        for th in list_themes():
            html = build_html(sr, ar, 0.01, theme=th)
            assert "<html" in html.lower()
            assert th.tokens["bg"] in html
            assert th.id in html


def test_tui_css_per_theme():
    from peek.scanner import scan
    from peek.analyzer import analyze
    from peek.tui import PeekApp

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "a.py").write_text("x=1\n", encoding="utf-8")
        sr = scan(root)
        ar = analyze(sr)
        for th in list_themes():
            app = PeekApp(root, sr, ar, 0.01, theme=th)
            assert th.tokens["bg"] in app.CSS
            assert th.tokens["accent"] in app.CSS


def test_cli_theme_list():
    from typer.testing import CliRunner
    from peek.cli import app

    r = CliRunner().invoke(app, ["--theme-list"])
    assert r.exit_code == 0
    for tid in ["anthropic-pro", "dracula", "nord", "tokyo-night"]:
        assert tid in r.output


def test_cli_unknown_theme_exit2():
    from typer.testing import CliRunner
    from peek.cli import app

    r = CliRunner().invoke(app, ["--theme", "bogus-theme-xyz", "--no-tui"])
    assert r.exit_code == 2
    assert "Unknown theme" in r.output


def test_render_static_backwards_compat_no_theme_arg():
    from peek.scanner import scan
    from peek.analyzer import analyze
    from peek.renderer import render_static
    from rich.console import Console
    import io

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "a.py").write_text("x=1\n", encoding="utf-8")
        sr = scan(root)
        ar = analyze(sr)
        c = Console(file=io.StringIO(), force_terminal=True, width=80, legacy_windows=False)
        # call without theme param — must not raise
        render_static(sr, ar, 0.01, c, animate=False)
