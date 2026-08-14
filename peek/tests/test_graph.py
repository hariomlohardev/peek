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
