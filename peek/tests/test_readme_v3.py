"""Viral polish v3 — README hero must mention v3 features."""

import pathlib

# peek/tests/<this file> -> peek/
PEEK_DIR = pathlib.Path(__file__).resolve().parent.parent


def test_readme_mentions_v3():
    txt = (PEEK_DIR / "README.md").read_text(encoding="utf-8", errors="ignore")
    assert "polyglot" in txt.lower() or "javascript" in txt.lower()
    assert "peek mcp" in txt.lower() or "mcp" in txt.lower()
    assert "peek graph" in txt.lower()
    assert "semantic" in txt.lower()
    assert "pip install peek-code" in txt
