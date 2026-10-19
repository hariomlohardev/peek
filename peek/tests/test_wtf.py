import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from peek.cli import app

runner = CliRunner()


def test_parse_simple_tb():
    from peek.wtf import parse_traceback
    tb = 'Traceback (most recent call last):\n  File "a.py", line 10, in foo\n    x = 1/0\nZeroDivisionError: division by zero\n'
    info = parse_traceback(tb)
    assert info is not None
    assert info.exc_type == "ZeroDivisionError"
    assert info.frames[0].filename == "a.py"
    assert info.frames[0].lineno == 10


def test_parse_none_on_no_tb():
    from peek.wtf import parse_traceback
    assert parse_traceback("hello") is None


def test_explain_needs_scan():
    from peek.wtf import parse_traceback, explain_tb
    from peek.scanner import scan; from peek.analyzer import analyze
    tb = 'Traceback (most recent call last):\n  File "peek/peek/cli.py", line 50, in foo\n    y\nNameError: name \'y\' is not defined\n'
    info = parse_traceback(tb)
    with tempfile.TemporaryDirectory() as td:
        p = Path(td); (p/"peek/peek/cli.py").parent.mkdir(parents=True, exist_ok=True); (p/"peek/peek/cli.py").write_text("y=1\n")
        sr = scan(p / "peek"); ar = analyze(sr)
        out = explain_tb(info, sr, ar)
        assert "NameError" in out
        assert "peek/peek/cli.py:50" in out or "cli.py" in out


def test_parse_multi_frame():
    from peek.wtf import parse_traceback
    tb = (
        'Traceback (most recent call last):\n'
        '  File "a.py", line 1, in <module>\n    foo()\n'
        '  File "b.py", line 5, in foo\n    bar()\n'
        '  File "c.py", line 9, in bar\n    x = 1/0\n'
        'ZeroDivisionError: division by zero\n'
    )
    info = parse_traceback(tb)
    assert info is not None
    assert len(info.frames) == 3
    assert info.frames[0].filename == "a.py"
    assert info.frames[2].filename == "c.py"
    assert info.frames[2].lineno == 9
    assert info.exc_type == "ZeroDivisionError"


def test_parse_empty_returns_none():
    from peek.wtf import parse_traceback
    assert parse_traceback("") is None
    assert parse_traceback("Traceback (most recent call last):\n") is None
    assert parse_traceback("Traceback (most recent call last):\n  File \"a.py\", line 1, in foo\n    pass\n") is None  # no exc line


def test_find_relevant_files():
    from peek.wtf import parse_traceback, find_relevant_files
    from peek.scanner import scan
    tb = 'Traceback (most recent call last):\n  File "peek/peek/cli.py", line 10, in foo\n    x\nNameError: name \'x\' is not defined\n'
    info = parse_traceback(tb)
    assert info is not None
    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        (p / "peek" / "peek").mkdir(parents=True, exist_ok=True)
        (p / "peek" / "peek" / "cli.py").write_text("x=1\n")
        (p / "peek" / "other.py").write_text("y=1\n")
        sr = scan(p / "peek")
        out = find_relevant_files(info, sr)
        assert len(out) >= 1
        assert any("cli.py" in str(x) for x in out)
        # non-matching frame yields no extra
        tb2 = 'Traceback (most recent call last):\n  File "nonexistent.py", line 1, in foo\n    x\nNameError: name \'x\' is not defined\n'
        info2 = parse_traceback(tb2)
        out2 = find_relevant_files(info2, sr)
        assert out2 == []


def _frame_matches(frame_path: str, files: list[str]) -> list[str]:
    from peek.wtf import parse_traceback, find_relevant_files
    from peek.scanner import scan
    # a traceback writes the path as is, with the single backslashes of a Windows path
    tb = f'Traceback (most recent call last):\n  File "{frame_path}", line 1, in foo\n    x\nNameError: name \'x\' is not defined\n'
    info = parse_traceback(tb)
    assert info is not None
    with tempfile.TemporaryDirectory() as td:
        root = Path(td).resolve()
        for f in files:
            (root / f).parent.mkdir(parents=True, exist_ok=True)
            (root / f).write_text("x=1\n")
        return [p.relative_to(root).as_posix() for p in find_relevant_files(info, scan(root))]


def test_find_relevant_files_windows_frame_paths():
    # Windows-style strings on every OS; no real C: drive is needed
    assert _frame_matches(r"C:\project\src\app.py", ["src/app.py", "src/other.py"]) == ["src/app.py"]
    assert _frame_matches(r"src\app.py", ["src/app.py"]) == ["src/app.py"]


def test_find_relevant_files_posix_paths_still_match():
    assert _frame_matches("/home/me/project/src/app.py", ["src/app.py"]) == ["src/app.py"]
    assert _frame_matches("src/app.py", ["src/app.py"]) == ["src/app.py"]


def test_find_relevant_files_matches_on_path_component_boundaries():
    assert _frame_matches(r"C:\project\src\myapp.py", ["src/app.py"]) == []
    assert _frame_matches("myapp.py", ["app.py"]) == []
    assert _frame_matches(r"C:\project\src\app.py", ["src/myapp.py"]) == []


def test_cli_file_read():
    tb = 'Traceback (most recent call last):\n  File "a.py", line 10, in foo\n    x = 1/0\nZeroDivisionError: division by zero\n'
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "tb.txt"
        p.write_text(tb, encoding="utf-8")
        result = runner.invoke(app, ["wtf", str(p), "--no-explain"])
        assert result.exit_code == 0
        assert "ZeroDivisionError" in result.output
        assert "a.py" in result.output


def test_cli_stdin():
    tb = 'Traceback (most recent call last):\n  File "b.py", line 5, in bar\n    y\nNameError: name \'y\' is not defined\n'
    result = runner.invoke(app, ["wtf", "--no-explain"], input=tb)
    assert result.exit_code == 0
    assert "NameError" in result.output


def test_cli_no_explain_flag():
    tb = 'Traceback (most recent call last):\n  File "a.py", line 10, in foo\n    x = 1/0\nZeroDivisionError: division by zero\n'
    # --no-explain prints raw traceback
    r1 = runner.invoke(app, ["wtf", "--no-explain"], input=tb)
    assert r1.exit_code == 0
    assert "Traceback (most recent call last)" in r1.output
    # default --explain prints markdown header
    r2 = runner.invoke(app, ["wtf"], input=tb)
    assert r2.exit_code == 0
    assert "ZeroDivisionError" in r2.output
    # both should contain the error, but explain mode uses markdown heading
    assert "## ZeroDivisionError" in r2.output or "ZeroDivisionError" in r2.output


def test_cli_no_traceback_exits_one():
    # no traceback in input -> exit 1
    result = runner.invoke(app, ["wtf", "--no-explain"], input="hello world")
    assert result.exit_code == 1
    assert "No traceback" in result.output
    # help should be available
    help_result = runner.invoke(app, ["wtf", "--help"])
    assert help_result.exit_code == 0
    assert "wtf" in help_result.output.lower() or "traceback" in help_result.output.lower()


@pytest.mark.parametrize(
    ("terminal", "exc_type", "exc_msg"),
    [
        ("Exception: bad", "Exception", "bad"),
        ("StopIteration", "StopIteration", ""),
        ("KeyboardInterrupt", "KeyboardInterrupt", ""),
        ("pkg.CustomFailure: bad", "pkg.CustomFailure", "bad"),
        ("ValueError: bad", "ValueError", "bad"),
        ("pkg.CustomError: bad", "pkg.CustomError", "bad"),
        ("RuntimeError:", "RuntimeError", ""),
        ("pkg.CustomFailure", "pkg.CustomFailure", ""),
        ("ValueError: bad\nextra", "ValueError", "bad"),
        ("Exception: bad\nNote: extra context", "Exception", "bad"),
    ],
)
def test_parse_exception_names_and_optional_messages(terminal, exc_type, exc_msg):
    from peek.wtf import parse_traceback

    tb = (
        'Traceback (most recent call last):\n'
        '  File "a.py", line 10, in foo\n'
        '    raise Exception("bad")\n'
        f"{terminal}\n"
    )
    info = parse_traceback(tb)
    assert info is not None
    assert (info.exc_type, info.exc_msg) == (exc_type, exc_msg)
    assert info.frames[0].code == 'raise Exception("bad")'


@pytest.mark.parametrize(
    "tail",
    [
        "",
        "    ValueError: str\n",
        "    StopIteration\n",
        "    pkg.CustomFailure: bad\n",
        "    raise Exception('bad')\n",
        "    value = 1\n",
        "This is just prose, not an exception.\n",
    ],
)
def test_parse_requires_unindented_exception_after_frame(tail):
    from peek.wtf import parse_traceback

    tb = 'Traceback (most recent call last):\n  File "a.py", line 1, in foo\n' + tail
    assert parse_traceback(tb) is None


@pytest.mark.parametrize(
    "separator",
    [
        "During handling of the above exception, another exception occurred:",
        "The above exception was the direct cause of the following exception:",
    ],
)
def test_parse_chained_traceback_uses_final_exception(separator):
    from peek.wtf import parse_traceback

    tb = (
        'Traceback (most recent call last):\n'
        '  File "a.py", line 1, in foo\n'
        '    int("bad")\n'
        'ValueError: bad\n\n'
        f"{separator}\n\n"
        'Traceback (most recent call last):\n'
        '  File "b.py", line 2, in bar\n'
        '    next(iter([]))\n'
    )
    assert parse_traceback(tb) is None
    info = parse_traceback(tb + "StopIteration\n")
    assert info is not None
    assert (info.exc_type, info.exc_msg) == ("StopIteration", "")
    assert [frame.filename for frame in info.frames] == ["a.py", "b.py"]


def test_cli_explains_message_free_exception(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.py").write_text("next(iter([]))\n", encoding="utf-8")
    tb = (
        'Traceback (most recent call last):\n'
        '  File "a.py", line 1, in <module>\n'
        '    next(iter([]))\n'
        'StopIteration\n'
    )
    result = runner.invoke(app, ["wtf"], input=tb)
    assert result.exit_code == 0
    assert "StopIteration" in result.output
    assert "No traceback" not in result.output
    assert "a.py:1" in result.output
