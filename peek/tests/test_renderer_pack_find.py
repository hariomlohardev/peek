"""Tests for renderer, html, pack, find, llm."""

import io
import re
import tempfile
from pathlib import Path

from rich.console import Console

from peek.analyzer import analyze
from peek.find import find_matches
from peek.pack import build_pack, estimate_tokens
from peek.renderer import build_html, render_static
from peek.scanner import scan


def _w(p: Path, c: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(c, encoding="utf-8")


def test_render_static_no_crash():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _w(root / "a.py", "x=1\n")
        sr = scan(root)
        ar = analyze(sr)
        console = Console(file=io.StringIO(), force_terminal=True, legacy_windows=False, width=80)
        # should not raise
        render_static(sr, ar, 0.01, console)


def test_build_html_contains():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _w(root / "a.py", "x=1\n")
        sr = scan(root)
        ar = analyze(sr)
        html = build_html(sr, ar, 0.01)
        assert "<html" in html.lower()
        assert "peek" in html.lower()
        assert str(root) in html or "a.py" in html


def test_build_html_scan_only():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _w(root / "README.md", "# hi")
        sr = scan(root)
        # fake analyzer
        fake = type("obj", (), {"root": sr.root, "summary": "scan only", "tech_stack": sr.tech_stack, "external_imports": set(), "stats": sr.stats, "ranked": [], "graph": {}})()
        html = build_html(sr, fake, 0.01)
        assert "<html" in html.lower()


def test_estimate_tokens():
    assert estimate_tokens("a" * 100) == 25
    assert estimate_tokens("") == 1


def test_build_pack_basic():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _w(root / "a.py", "import b\n")
        _w(root / "b.py", "x=1\n")
        _w(root / "c.py", "y=1\n")
        sr = scan(root)
        ar = analyze(sr)
        packed, included, tokens = build_pack(sr, ar)
        assert len(included) >= 1
        assert tokens > 0
        assert "FILE:" in packed
        assert "a.py" in packed or "b.py" in packed


def test_build_pack_query_filter():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _w(root / "auth.py", "def login(): pass\n")
        _w(root / "utils.py", "def helper(): pass\n")
        _w(root / "main.py", "import auth\n")
        sr = scan(root)
        ar = analyze(sr)
        packed, included, _ = build_pack(sr, ar, query="auth")
        # Should include auth.py
        assert any("auth" in str(p).lower() for p in included)
        # Should not include unrelated if filtered strictly? but may include main.py because it imports auth and contains "auth"
        assert len(included) >= 1


def test_build_pack_token_budget():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        for i in range(5):
            _w(root / f"f{i}.py", "x=1\n" * 100)
        sr = scan(root)
        ar = analyze(sr)
        packed, included, tokens = build_pack(sr, ar, token_budget=50)  # tiny budget
        # Should include at most 1-2 files due to budget
        assert len(included) <= 2
        assert tokens <= 60  # some slack


def test_find_filename_and_content():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _w(root / "auth.py", "def validate_token(): pass\n")
        _w(root / "main.py", "from auth import validate_token\n")
        _w(root / "other.py", "nothing\n")
        sr = scan(root)
        ar = analyze(sr)
        matches = find_matches("auth", sr, ar)
        assert len(matches) >= 1
        assert any("auth.py" in str(m["rel"]) for m in matches)
        # First match should be auth.py (filename)
        assert matches[0]["rel"].as_posix().endswith("auth.py") or "auth" in str(matches[0]["rel"])

        matches2 = find_matches("validate_token", sr, ar)
        assert len(matches2) >= 1
        assert any("validate_token" in " ".join(m["preview"]) or "validate_token" in str(m["rel"]) for m in matches2)


def test_find_no_match():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _w(root / "a.py", "x=1\n")
        sr = scan(root)
        ar = analyze(sr)
        matches = find_matches("nonexistentkeyword123", sr, ar)
        assert matches == []


def test_find_empty_query():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _w(root / "a.py", "x=1\n")
        sr = scan(root)
        ar = analyze(sr)
        assert find_matches("", sr, ar) == []
        assert find_matches("   ", sr, ar) == []


def test_llm_fallback():
    # Without API keys, should return None
    import os
    # Ensure no keys
    old_openai = os.environ.pop("OPENAI_API_KEY", None)
    old_anth = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        from peek.llm import try_llm_summary
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _w(root / "a.py", "x=1\n")
            sr = scan(root)
            ar = analyze(sr)
            res = try_llm_summary(sr, ar, force=False)
            assert res is None
            # force also should return None without keys/packages
            res2 = try_llm_summary(sr, ar, force=True)
            # May be None if openai not installed
            assert res2 is None or isinstance(res2, str)
    finally:
        if old_openai is not None:
            os.environ["OPENAI_API_KEY"] = old_openai
        if old_anth is not None:
            os.environ["ANTHROPIC_API_KEY"] = old_anth


def test_cli_scan_and_analyze_import():
    # Ensure CLI import doesn't crash
    from peek.cli import app
    assert app is not None


def _sleep_recorder(monkeypatch):
    """Replace renderer's time.sleep and return the list it records into."""
    calls: list[float] = []
    monkeypatch.setattr("peek.renderer.time.sleep", calls.append)
    return calls


def test_render_static_no_animate(monkeypatch):
    """A non-TTY console must not pay the staggered-reveal sleeps.

    render_static resolves `animate` from `console.is_terminal` when the caller
    leaves it None, so a redirected stdout -- pytest, a pipe, CI -- should take
    the plain path. The stagger totals ~0.25s per call and is what makes the
    reveal flake when it does run under a test runner.
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _w(root / "a.py", "x=1\n")
        sr = scan(root)
        ar = analyze(sr)
        calls = _sleep_recorder(monkeypatch)
        console = Console(file=io.StringIO(), width=80)  # is_terminal False

        render_static(sr, ar, 0.01, console)

        assert console.is_terminal is False
        assert calls == []


def test_render_static_animate_false_never_sleeps(monkeypatch):
    """An explicit animate=False overrides a real TTY."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _w(root / "a.py", "x=1\n")
        sr = scan(root)
        ar = analyze(sr)
        calls = _sleep_recorder(monkeypatch)
        console = Console(file=io.StringIO(), force_terminal=True, legacy_windows=False, width=80)

        render_static(sr, ar, 0.01, console, animate=False)

        assert calls == []


def test_render_static_animates_on_a_terminal(monkeypatch):
    """The control: without this the two tests above would pass on a no-op.

    Pins that the sleeps are reachable at all, so a future change that drops
    the stagger entirely is visible here rather than silently green.
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _w(root / "a.py", "x=1\n")
        sr = scan(root)
        ar = analyze(sr)
        calls = _sleep_recorder(monkeypatch)
        console = Console(file=io.StringIO(), force_terminal=True, legacy_windows=False, width=80)

        render_static(sr, ar, 0.01, console, animate=True)

        assert calls, "a TTY render should stagger"
        assert all(d <= 0.05 for d in calls), f"unexpectedly long stagger: {calls}"


def test_no_color(monkeypatch):
    """NO_COLOR disables ANSI colour escapes in static output."""
    monkeypatch.setenv("NO_COLOR", "1")

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _w(root / "a.py", "x = 1\n")
        sr = scan(root)
        ar = analyze(sr)

        output = io.StringIO()
        console = Console(
            file=output,
            force_terminal=True,
            legacy_windows=False,
            width=80,
            no_color=False,
        )

        render_static(sr, ar, 0.01, console, animate=False)

    ansi_colour = re.compile(
        r"\x1b\[[0-9;]*(?:3[0-7]|4[0-7]|9[0-7]|10[0-7]|38|48)[0-9;]*m"
    )
    assert not ansi_colour.search(output.getvalue())
