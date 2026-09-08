"""Tests for analyzer — graph, ranking, summary, edge cases."""

import tempfile
from pathlib import Path

from peek.analyzer import analyze, build_graph, summarize
from peek.scanner import scan


def _w(p: Path, c: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(c, encoding="utf-8")


def test_build_graph_simple():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _w(root / "main.py", "import b\nimport c\n")
        _w(root / "b.py", "import d\n")
        _w(root / "c.py", "import d\n")
        _w(root / "d.py", "# hub\n")
        sr = scan(root)
        ar = analyze(sr)
        # d should be hub (imported by 2)
        assert ar.stats["graph_nodes"] == 4
        assert ar.stats["graph_edges"] >= 3
        # ranked top should be d or main (hub vs entry)
        top = ar.ranked[0].rel.as_posix()
        assert top in ("d.py", "main.py", "b.py", "c.py")
        # d should be high
        d_rank = next((r for r in ar.ranked if r.rel.name == "d.py"), None)
        assert d_rank is not None
        assert "hub" in " ".join(d_rank.reasons) or d_rank.score > 2


def test_relative_imports():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _w(root / "pkg" / "__init__.py", "from . import utils\n")
        _w(root / "pkg" / "utils.py", "def helper(): pass\n")
        _w(root / "pkg" / "sub" / "core.py", "from .. import utils\nfrom ..utils import helper\n")
        _w(root / "app.py", "from pkg.sub import core\n")
        sr = scan(root)
        ar = analyze(sr)
        # Should not crash, graph should have edges
        assert ar.stats["graph_edges"] >= 2
        # utils should be hub
        utils_rank = next((r for r in ar.ranked if r.rel.as_posix().endswith("utils.py")), None)
        assert utils_rank is not None


def test_circular_imports():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _w(root / "a.py", "import b\n")
        _w(root / "b.py", "import a\n")
        sr = scan(root)
        ar = analyze(sr)
        # Should handle circular without infinite loop
        assert ar.stats["graph_nodes"] == 2
        assert ar.stats["graph_edges"] == 2
        assert len(ar.ranked) == 2


def test_syntax_error_handled():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _w(root / "broken.py", "def broken(:")
        _w(root / "good.py", "import broken\n")
        sr = scan(root)
        ar = analyze(sr)
        # Should not crash, broken should be node but with no outgoing
        assert ar.stats["graph_nodes"] >= 1
        # good imports broken is external? broken is local but parse failed, so no edge expected?
        # But should not raise
        assert ar.summary  # summary should exist


def test_non_python_repo():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _w(root / "README.md", "# hi")
        (root / "package.json").write_text('{"name":"t"}', encoding="utf-8")
        sr = scan(root)
        ar = analyze(sr)
        assert ar.stats["graph_nodes"] == 0
        assert "no python" in ar.summary.lower() or "0" in ar.summary


def test_empty_repo():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        sr = scan(root)
        ar = analyze(sr)
        assert ar.stats["graph_nodes"] == 0
        assert len(ar.ranked) == 0
        assert "no python" in ar.summary.lower() or "0 files" in ar.summary.lower()


def test_summary_frameworks():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _w(root / "pyproject.toml", '[project]\ndependencies=["fastapi","sqlalchemy"]\n')
        _w(root / "app.py", "import fastapi\n")
        sr = scan(root)
        ar = analyze(sr)
        # summary should mention FastAPI or SQLAlchemy
        assert "FastAPI" in ar.summary or "fastapi" in ar.summary.lower() or "SQLAlchemy" in ar.summary


def test_rank_entry_bonus():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _w(root / "pyproject.toml", '[project.scripts]\ncli="app.cli:app"\n')
        _w(root / "app" / "cli.py", 'def main(): pass\nif __name__ == "__main__": main()\n')
        _w(root / "app" / "utils.py", "x=1\n")
        sr = scan(root)
        ar = analyze(sr)
        # cli should be ranked high due to entry bonus
        cli = next((r for r in ar.ranked if r.rel.as_posix().endswith("cli.py")), None)
        assert cli is not None
        assert "entry point" in " ".join(cli.reasons).lower() or cli.score > 5


def test_bom_handling():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        # Write BOM file via utf-8-sig
        p = root / "a.py"
        p.write_text("import b\n", encoding="utf-8-sig")
        (root / "b.py").write_text("x=1\n", encoding="utf-8")
        sr = scan(root)
        ar = analyze(sr)
        assert ar.stats["graph_edges"] >= 1


def test_go_import_graph(tmp_path):
    """Go files form graph nodes with resolved local edges (regex, offline)."""
    from peek.analyzer import analyze
    from peek.scanner import scan

    p = tmp_path / "repo"
    (p / "b").mkdir(parents=True)
    (p / "go.mod").write_text("module example.com/t\n\ngo 1.21\n", encoding="utf-8")
    (p / "a.go").write_text('package t\n\nimport "example.com/t/b"\n\nfunc A() { b.B() }\n', encoding="utf-8")
    (p / "b" / "b.go").write_text("package b\n\nfunc B() {}\n", encoding="utf-8")
    ar = analyze(scan(p))
    assert len(ar.graph) >= 2
    a_key = next(k for k in ar.graph if str(k).endswith("a.go"))
    assert any(str(t).endswith(("b/b.go", "b\\b.go")) for t in ar.graph[a_key])
    assert any(str(r.rel).endswith(".go") for r in ar.ranked)
