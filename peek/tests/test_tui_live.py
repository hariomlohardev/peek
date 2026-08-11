"""Live theme cycling — Task 4 TDD."""

import pathlib
import tempfile

import pytest

pytest.importorskip("textual")

from peek.tui import PeekApp  # noqa: E402
from peek.themes import get_theme, list_themes  # noqa: E402
from peek.scanner import scan  # noqa: E402
from peek.analyzer import analyze  # noqa: E402


def test_tui_bindings_has_t():
    assert any(b.key == "t" for b in PeekApp.BINDINGS)
    # also check binding action and description
    t_bind = next(b for b in PeekApp.BINDINGS if b.key == "t")
    assert t_bind.action == "cycle_theme"
    assert "theme" in t_bind.description.lower()


def test_cycle_theme_changes_theme():
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        (p / "a.py").write_text("x=1\n")
        sr = scan(p)
        ar = analyze(sr)
        app = PeekApp(p, sr, ar, 0.01, theme=get_theme("dracula"))
        assert app._theme.id == "dracula"
        app.action_cycle_theme()
        assert app._theme.id != "dracula"
        assert app._theme.id in [t.id for t in list_themes()]


def test_cycle_theme_wraps_after_ten():
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        (p / "a.py").write_text("x=1\n")
        sr = scan(p)
        ar = analyze(sr)
        start = get_theme("dracula")
        app = PeekApp(p, sr, ar, 0.01, theme=start)
        themes = list_themes()
        n = len(themes)
        # cycle n times should return to start id if start is in list
        start_id = start.id
        # find start index
        start_idx = next((i for i, t in enumerate(themes) if t.id == start_id), 0)
        for _ in range(n):
            app.action_cycle_theme()
        assert app._theme.id == start_id
        # one more cycle goes to next
        app.action_cycle_theme()
        assert app._theme.id == themes[(start_idx + 1) % n].id


def test_css_for_theme_exists_and_linear():
    from peek.tui import _css_for_theme

    css = _css_for_theme(get_theme("dracula"))
    assert isinstance(css, str)
    assert "linear" in css
    assert "#282A36" in css or "dracula" in css.lower() or "#BD93F9" in css  # dracula tokens
    # different theme yields different CSS
    css2 = _css_for_theme(get_theme("nord"))
    assert css != css2
    assert "linear" in css2


def test_cycle_theme_updates_label_and_tokens():
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        (p / "a.py").write_text("x=1\n")
        sr = scan(p)
        ar = analyze(sr)
        app = PeekApp(p, sr, ar, 0.01, theme=get_theme("dracula"))
        old_label = app._label
        old_tokens = dict(app._tokens)
        app.action_cycle_theme()
        assert app._label != old_label
        assert app._label == app._theme.id
        assert app._tokens != old_tokens
        assert app._tokens == app._theme.tokens
        # CSS should have been updated to new theme's tokens
        assert app.CSS is not None
        assert "linear" in app.CSS
