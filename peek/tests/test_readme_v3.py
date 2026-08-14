"""Viral polish v3 — README hero must mention v3 features."""
import pathlib

def test_readme_mentions_v3():
    txt = pathlib.Path("peek/README.md").read_text(encoding="utf-8", errors="ignore")
    assert "polyglot" in txt.lower() or "javascript" in txt.lower()
    assert "peek mcp" in txt.lower() or "mcp" in txt.lower()
    assert "peek graph" in txt.lower()
    assert "semantic" in txt.lower()
    assert "pip install peek-code" in txt
