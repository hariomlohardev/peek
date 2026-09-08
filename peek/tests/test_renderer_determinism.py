"""`peek --no-tui` must not sleep when nobody is watching.

`render_static` reveals its panels with a stagger built from ~250ms of
`time.sleep`. That is the right thing in a terminal and the wrong thing under
`pytest`, in CI, or through a pipe: it costs wall clock and it makes output
timing-dependent.
"""

import io
import tempfile
from pathlib import Path

import pytest
from rich.console import Console

from peek.analyzer import analyze
from peek.renderer import render_static
from peek.scanner import scan


@pytest.fixture()
def results():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "a.py").write_text("x = 1\n", encoding="utf-8")
        (root / "b.py").write_text("import a\ny = a.x\n", encoding="utf-8")
        scan_result = scan(root)
        yield scan_result, analyze(scan_result)


@pytest.fixture()
def no_sleep(monkeypatch):
    """Record every sleep instead of taking it, so a test never waits."""
    calls = []
    monkeypatch.setattr("peek.renderer.time.sleep", lambda seconds: calls.append(seconds))
    return calls


def _console(is_terminal: bool) -> Console:
    return Console(file=io.StringIO(), force_terminal=is_terminal, legacy_windows=False, width=80)


def test_render_static_no_animate(results, no_sleep, monkeypatch):
    """The case the issue names: no sleep at all when stdout is not a terminal."""
    monkeypatch.delenv("PEEK_NO_ANIMATE", raising=False)
    monkeypatch.delenv("NO_COLOR", raising=False)
    scan_result, analyzer_result = results

    console = _console(is_terminal=False)
    assert console.is_terminal is False
    render_static(scan_result, analyzer_result, 0.01, console)

    assert no_sleep == [], f"render_static slept {sum(no_sleep):.2f}s with no terminal attached"


def test_render_static_still_animates_on_a_terminal(results, no_sleep, monkeypatch):
    """The stagger is not removed, only made skippable -- otherwise the test above
    would pass for the wrong reason."""
    monkeypatch.delenv("PEEK_NO_ANIMATE", raising=False)
    monkeypatch.delenv("NO_COLOR", raising=False)
    scan_result, analyzer_result = results

    render_static(scan_result, analyzer_result, 0.01, _console(is_terminal=True))

    assert no_sleep, "the staggered reveal no longer happens on a terminal"


def test_explicit_animate_false_never_sleeps(results, no_sleep):
    scan_result, analyzer_result = results
    render_static(scan_result, analyzer_result, 0.01, _console(is_terminal=True), animate=False)
    assert no_sleep == []


@pytest.mark.parametrize("value", ["1", "true", "yes", "TRUE", "anything"])
def test_peek_no_animate_env_wins_over_a_terminal(results, no_sleep, monkeypatch, value):
    """The escape hatch for a caller that has a terminal and still wants determinism."""
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("PEEK_NO_ANIMATE", value)
    scan_result, analyzer_result = results

    render_static(scan_result, analyzer_result, 0.01, _console(is_terminal=True))

    assert no_sleep == []


@pytest.mark.parametrize("value", ["", "0", "false", "no"])
def test_peek_no_animate_falsey_values_do_not_disable(results, no_sleep, monkeypatch, value):
    """`PEEK_NO_ANIMATE=0` must mean off, not "the variable is set"."""
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("PEEK_NO_ANIMATE", value)
    scan_result, analyzer_result = results

    render_static(scan_result, analyzer_result, 0.01, _console(is_terminal=True))

    assert no_sleep


def test_no_color_also_disables_the_stagger(results, no_sleep, monkeypatch):
    """NO_COLOR already strips styling here; a caller asking for plain output is
    not asking for a quarter-second reveal either."""
    monkeypatch.delenv("PEEK_NO_ANIMATE", raising=False)
    monkeypatch.setenv("NO_COLOR", "1")
    scan_result, analyzer_result = results

    render_static(scan_result, analyzer_result, 0.01, _console(is_terminal=True))

    assert no_sleep == []


def test_output_is_identical_with_and_without_the_stagger(results, monkeypatch):
    """Skipping the sleeps must change the timing and nothing else."""
    monkeypatch.delenv("NO_COLOR", raising=False)
    scan_result, analyzer_result = results

    monkeypatch.setattr("peek.renderer.time.sleep", lambda seconds: None)
    monkeypatch.delenv("PEEK_NO_ANIMATE", raising=False)
    animated = _console(is_terminal=True)
    render_static(scan_result, analyzer_result, 0.01, animated)

    monkeypatch.setenv("PEEK_NO_ANIMATE", "1")
    plain = _console(is_terminal=True)
    render_static(scan_result, analyzer_result, 0.01, plain)

    assert animated.file.getvalue() == plain.file.getvalue()
