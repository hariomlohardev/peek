"""Guards for demo assets — GIF valid, <3MB, not placeholder."""

import pathlib

# peek/tests/<this file> -> peek/
PEEK_DIR = pathlib.Path(__file__).resolve().parent.parent
ASSETS_DIR = PEEK_DIR / "assets"


def test_demo_gif_exists_and_valid():
    p = ASSETS_DIR / "demo.gif"
    assert p.exists(), "demo.gif missing — run python -m peek.tools.gen_demo"
    assert p.stat().st_size < 3_000_000, f"GIF too large: {p.stat().st_size} > 3MB"
    assert p.stat().st_size > 5000, f"GIF looks like placeholder 1x1: {p.stat().st_size} bytes"
    data = p.read_bytes()
    assert data[:6] in (b"GIF89a", b"GIF87a"), f"Bad GIF header: {data[:6]!r}"


def test_demo_html_exists():
    p = ASSETS_DIR / "demo.html"
    assert p.exists(), "demo.html missing — run peek --html -o peek/assets/demo.html"
    assert p.stat().st_size > 500, "demo.html too small"
    txt = p.read_text(encoding="utf-8", errors="ignore")
    assert "<html" in txt.lower() or "<!doctype" in txt.lower(), "demo.html not HTML"
