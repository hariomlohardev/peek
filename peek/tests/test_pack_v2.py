"""Pack v2 — token-smart, format, budget, include/exclude globs."""

import pathlib
import tempfile

from typer.testing import CliRunner

from peek.cli import app
from peek.analyzer import analyze
from peek.pack import build_pack
from peek.scanner import scan

runner = CliRunner()


def test_pack_format_xml():
    import tempfile, pathlib
    from peek.scanner import scan; from peek.analyzer import analyze; from peek.pack import build_pack
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td); (p/"a.py").write_text("x=1\n"); (p/"b.py").write_text("y=2\n")
        sr = scan(p); ar = analyze(sr)
        out, files, toks = build_pack(sr, ar, format="xml")
        assert "<file" in out or "<code" in out
        assert len(files) == 2


def test_pack_include_glob():
    import tempfile, pathlib
    from peek.scanner import scan; from peek.analyzer import analyze; from peek.pack import build_pack
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td); (p/"a.py").write_text("x\n"); (p/"b.md").write_text("y\n")
        sr = scan(p); ar = analyze(sr)
        out, files, _ = build_pack(sr, ar, include="*.py")
        assert all(f.suffix == ".py" for f in files)
        assert len(files) == 1


def test_pack_format_txt():
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        (p / "a.py").write_text("x=1\n")
        (p / "b.py").write_text("y=2\n")
        sr = scan(p); ar = analyze(sr)
        out, files, toks = build_pack(sr, ar, format="txt")
        assert "# " in out or "a.py" in out
        assert len(files) == 2
        # txt should not contain xml tags
        assert "<file" not in out


def test_pack_format_md():
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        (p / "a.py").write_text("x=1\n")
        sr = scan(p); ar = analyze(sr)
        out, files, _ = build_pack(sr, ar, format="md")
        # md should contain markdown fence and header
        assert "```" in out
        assert "a.py" in out
        assert len(files) == 1


def test_pack_exclude_glob():
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        (p / "a.py").write_text("x\n")
        (p / "b.py").write_text("y\n")
        (p / "c.md").write_text("z\n")
        sr = scan(p); ar = analyze(sr)
        out, files, _ = build_pack(sr, ar, exclude="*.md")
        assert all(f.suffix != ".md" for f in files)
        assert len(files) == 2
        # exclude one py file
        out2, files2, _ = build_pack(sr, ar, exclude="b.py")
        assert len(files2) == 1
        assert all("b.py" not in str(f) for f in files2)


def test_pack_budget_truncates():
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        for i in range(5):
            (p / f"f{i}.py").write_text("x=1\n" * 200)
        sr = scan(p); ar = analyze(sr)
        # small budget should truncate
        out_small, files_small, toks_small = build_pack(sr, ar, budget=100)
        out_big, files_big, toks_big = build_pack(sr, ar, budget=8000)
        assert len(files_small) < len(files_big)
        assert len(files_small) <= 2
        assert toks_small <= 150  # slack for manifest
        # alias token_budget should also work (backwards compat)
        out_alias, files_alias, _ = build_pack(sr, ar, token_budget=100)
        assert len(files_alias) == len(files_small)


def test_pack_cli_format_xml():
    import os
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        (p / "a.py").write_text("x=1\n")
        (p / "b.py").write_text("y=2\n")
        # CLI: peek --pack --format xml (uses cwd)
        old = os.getcwd()
        try:
            os.chdir(td)
            result = runner.invoke(app, ["--pack", "--format", "xml"])
        finally:
            os.chdir(old)
        assert result.exit_code == 0, result.output
        out = result.output
        assert "<file" in out or "<code" in out
        assert "a.py" in out or "b.py" in out


def test_pack_cli_include_and_budget():
    import os
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        (p / "a.py").write_text("hello\n")
        (p / "b.md").write_text("world\n")
        (p / "c.py").write_text("foo\n" * 100)
        old = os.getcwd()
        try:
            os.chdir(td)
            # include only py
            result = runner.invoke(app, ["--pack", "--include", "*.py"])
            assert result.exit_code == 0, result.output
            assert "a.py" in result.output or "c.py" in result.output
            # budget small + txt format (use budget large enough for 1 file but smaller than full)
            result2 = runner.invoke(app, ["--pack", "--budget", "500", "--format", "txt"])
            assert result2.exit_code == 0, result2.output
            assert "# " in result2.output or "a.py" in result2.output
            # exclude
            result3 = runner.invoke(app, ["--pack", "--exclude", "*.md"])
            assert result3.exit_code == 0, result3.output
        finally:
            os.chdir(old)
