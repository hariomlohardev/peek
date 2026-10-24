def test_build_dot():
    from peek.graph import build_dot
    from peek.scanner import scan; from peek.analyzer import analyze
    import tempfile, pathlib
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td); (p/"a.py").write_text("import b\n"); (p/"b.py").write_text("x=1\n")
        sr = scan(p); ar = analyze(sr)
        dot = build_dot(ar)
        assert "digraph" in dot
        assert "a.py" in dot or "a" in dot

def test_cli_graph_help():
    from typer.testing import CliRunner; from peek.cli import app
    r = CliRunner().invoke(app, ["graph", "--help"])
    assert r.exit_code == 0
    assert "graph" in r.output.lower()

def test_export_mermaid():
    from peek.graph import export_graph
    from peek.scanner import scan; from peek.analyzer import analyze
    import tempfile, pathlib
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td); (p/"a.py").write_text("import b\n"); (p/"b.py").write_text("x=1\n")
        sr = scan(p); ar = analyze(sr)
        mmd = export_graph(ar, format="mermaid")
        assert "graph TD" in mmd
        # nodes as id["label"] and edges as a --> b
        assert "-->" in mmd or "--" in mmd
        # label should contain file names
        assert "a.py" in mmd or "a_py" in mmd
        assert "b.py" in mmd or "b_py" in mmd

def test_cli_graph_mermaid():
    from typer.testing import CliRunner; from peek.cli import app
    import tempfile, pathlib
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td); (p/"a.py").write_text("import b\n"); (p/"b.py").write_text("x=1\n")
        r = CliRunner().invoke(app, ["graph", str(p), "--format", "mermaid"])
        assert r.exit_code == 0
        assert "graph TD" in r.output

def test_cli_graph_mermaid_output_file():
    from typer.testing import CliRunner; from peek.cli import app
    import tempfile, pathlib
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td); (p/"a.py").write_text("import b\n"); (p/"b.py").write_text("x=1\n")
        out = pathlib.Path(td) / "graph.mmd"
        r = CliRunner().invoke(app, ["graph", str(p), "--format", "mermaid", "-o", str(out)])
        assert r.exit_code == 0
        assert out.exists()
        text = out.read_text(encoding="utf-8")
        assert "graph TD" in text


# --- issue #178: isolated source nodes must appear in the DOT export ----------

class _FakeAnalyzer:
    def __init__(self, graph, root):
        self.graph = graph
        self.root = root


def test_build_dot_declares_isolated_sources(tmp_path):
    from peek.graph import build_dot
    import pathlib

    alone = tmp_path / "alone.py"
    alone.write_text("x=1\n", encoding="utf-8")
    ar = _FakeAnalyzer({pathlib.Path(alone): set()}, tmp_path)
    dot = build_dot(ar)
    assert "digraph" in dot
    assert '"alone.py";' in dot  # explicit declaration, even with no outgoing edge
    assert "->" not in dot  # nothing to connect
    assert dot.count("alone.py") == 1  # declared exactly once


def test_build_dot_keeps_edges_and_declares_mixed_nodes(tmp_path):
    from peek.graph import build_dot
    import pathlib

    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    c = tmp_path / "c.py"
    a.write_text("import b\n", encoding="utf-8")
    b.write_text("x=1\n", encoding="utf-8")
    c.write_text("y=1\n", encoding="utf-8")
    ar = _FakeAnalyzer(
        {pathlib.Path(a): {pathlib.Path(b)}, pathlib.Path(c): set()},
        tmp_path,
    )
    dot = build_dot(ar)
    assert '"a.py";' in dot and '"c.py";' in dot  # every selected source declared
    assert '"a.py" -> "b.py";' in dot  # connected edges preserved
    assert '"b.py" ->' not in dot  # destinations are not re-declared as sources


def test_build_dot_empty_graph_is_valid_dot(tmp_path):
    from peek.graph import build_dot

    ar = _FakeAnalyzer({}, tmp_path)
    dot = build_dot(ar)
    assert dot.startswith("digraph")
    assert dot.rstrip().endswith("}")
