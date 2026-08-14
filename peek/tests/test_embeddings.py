import pathlib
import tempfile


def test_bm25_fallback():
    from peek.embeddings import build_index, search
    from peek.scanner import scan

    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        (p / "auth.py").write_text("def validate_token(): pass\n# validates auth token\n")
        (p / "other.py").write_text("def foo(): pass  # unrelated helper module\n")
        sr = scan(p)
        idx = build_index(sr)
        hits = search(idx, "where is auth token validated", k=2)
        assert len(hits) >= 2
        assert hits[0].file.name == "auth.py"
        assert hits[0].score > hits[1].score


def test_pack_uses_semantic(tmp_path):
    from peek.scanner import scan
    from peek.analyzer import analyze
    from peek.pack import build_pack

    (tmp_path / "a.py").write_text("def validate(): # auth token\n")
    (tmp_path / "b.py").write_text("def unrelated(): pass\n")
    sr = scan(tmp_path)
    ar = analyze(sr)
    out, files, toks = build_pack(sr, ar, query="auth token", budget=8000)
    assert files[0].name == "a.py"


def test_build_index_chunks():
    from peek.embeddings import build_index
    from peek.scanner import scan

    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        (p / "a.py").write_text("x=1\n" * 10 + "\nhello world content for chunking\n")
        sr = scan(p)
        idx = build_index(sr)
        assert "chunks" in idx
        assert "docs_tokens" in idx
        assert len(idx["chunks"]) >= 1


def test_search_empty_returns_empty():
    from peek.embeddings import build_index, search
    from peek.scanner import scan

    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        (p / "a.py").write_text("hello world\n" * 5 + "some extra content to ensure chunk length exceeds threshold\n")
        sr = scan(p)
        idx = build_index(sr)
        hits = search(idx, "nonexistentkeyword123", k=5)
        assert hits == []


def test_search_k_limit():
    from peek.embeddings import build_index, search
    from peek.scanner import scan

    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        for i in range(5):
            (p / f"f{i}.py").write_text(f"def func{i}(): pass  # common token\n")
        sr = scan(p)
        idx = build_index(sr)
        hits = search(idx, "common token", k=2)
        assert len(hits) <= 2


def test_search_scoredchunk_fields():
    from peek.embeddings import build_index, search
    from peek.scanner import scan

    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        (p / "a.py").write_text("def foo():\n    # hello world\n    pass\n")
        sr = scan(p)
        idx = build_index(sr)
        hits = search(idx, "hello world", k=1)
        assert len(hits) >= 1
        h = hits[0]
        assert hasattr(h, "file")
        assert hasattr(h, "rel")
        assert hasattr(h, "chunk")
        assert hasattr(h, "lineno")
        assert hasattr(h, "score")
        assert h.score > 0


def test_cli_index_command(tmp_path):
    from typer.testing import CliRunner
    from peek.cli import app

    (tmp_path / "a.py").write_text("x=1\n" * 10 + "hello world content for indexing\n")
    runner = CliRunner()
    result = runner.invoke(app, ["index", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "Indexed" in result.output
    # check .peek/index.json created
    idx_file = tmp_path / ".peek" / "index.json"
    assert idx_file.exists()
    import json

    data = json.loads(idx_file.read_text())
    assert "chunks" in data
