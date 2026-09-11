"""Regression: _languages_renderable must never return a Textual widget.

Bug: on latest textual (8.x) `Static(Static(""))` raises
`VisualError: unable to display 'Static' type`.
Empty scan (by_lang == {}) hit `return Static("")` inside
`_languages_renderable`, which compose() then wrapped in
`Static(..., id="langs")` -> crash.
"""

import pathlib
import tempfile

import pytest

pytest.importorskip("textual")

from textual.widgets import Static  # noqa: E402

from peek.analyzer import analyze  # noqa: E402
from peek.scanner import scan  # noqa: E402
from peek.themes import get_theme  # noqa: E402
from peek.tui import PeekApp  # noqa: E402


def test_languages_renderable_empty_is_not_widget():
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        # empty dir -> by_lang == {}
        sr = scan(p)
        assert sr.stats.get("by_lang", {}) == {}
        ar = analyze(sr)
        app = PeekApp(p, sr, ar, 0.01, theme=get_theme("dracula"))
        result = app._languages_renderable()
        # Must be a Rich renderable / str, never a Textual widget.
        assert not isinstance(result, Static), f"returned widget {result!r} nests Static in Static -> VisualError"


def test_langs_static_wrapping_does_not_raise():
    """Simulates compose(): Static(renderable, id='langs') must not raise."""
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        sr = scan(p)
        ar = analyze(sr)
        app = PeekApp(p, sr, ar, 0.01, theme=get_theme("dracula"))
        renderable = app._languages_renderable()
        # This is what compose() does; on textual 8.x a Static inside raises VisualError
        # when the widget tries to render. Constructing + accessing visual proves it.
        w = Static(renderable)
        # Force render path that raised in the bug report (visualize content)
        _ = w.visual if hasattr(w, "visual") else w.render()
