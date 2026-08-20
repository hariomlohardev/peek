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
