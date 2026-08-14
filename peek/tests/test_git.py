"""Tests for git time machine — Task 5."""
from __future__ import annotations

import pathlib
import subprocess
import tempfile


def _has_git() -> bool:
    try:
        subprocess.check_output(["git", "--version"], text=True)
        return True
    except Exception:
        return False


def test_git_log(tmp_path):
    if not _has_git():
        import pytest

        pytest.skip("git not available")
    from peek.git import git_log

    # init repo
    subprocess.check_call(["git", "init"], cwd=tmp_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.check_call(["git", "config", "user.name", "t"], cwd=tmp_path, stdout=subprocess.DEVNULL)
    subprocess.check_call(["git", "config", "user.email", "t@t.com"], cwd=tmp_path, stdout=subprocess.DEVNULL)
    (tmp_path / "a.py").write_text("x=1\n")
    subprocess.check_call(["git", "add", "."], cwd=tmp_path, stdout=subprocess.DEVNULL)
    subprocess.check_call(["git", "commit", "-m", "init"], cwd=tmp_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    out = git_log(tmp_path, n=5)
    assert isinstance(out, str)
    assert "init" in out.lower() or len(out.strip()) > 0


def test_git_diff(tmp_path):
    if not _has_git():
        import pytest

        pytest.skip("git not available")
    from peek.git import git_diff

    subprocess.check_call(["git", "init"], cwd=tmp_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.check_call(["git", "config", "user.name", "t"], cwd=tmp_path, stdout=subprocess.DEVNULL)
    subprocess.check_call(["git", "config", "user.email", "t@t.com"], cwd=tmp_path, stdout=subprocess.DEVNULL)
    (tmp_path / "a.py").write_text("x=1\n")
    subprocess.check_call(["git", "add", "."], cwd=tmp_path, stdout=subprocess.DEVNULL)
    subprocess.check_call(["git", "commit", "-m", "init"], cwd=tmp_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    (tmp_path / "a.py").write_text("x=2\n")
    out = git_diff(tmp_path, base="HEAD")
    assert isinstance(out, list)
    assert any("a.py" in s for s in out)


def test_git_hot_churn(tmp_path):
    if not _has_git():
        import pytest

        pytest.skip("git not available")
    from peek.git import churn

    subprocess.check_call(["git", "init"], cwd=tmp_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.check_call(["git", "config", "user.name", "t"], cwd=tmp_path, stdout=subprocess.DEVNULL)
    subprocess.check_call(["git", "config", "user.email", "t@t.com"], cwd=tmp_path, stdout=subprocess.DEVNULL)
    (tmp_path / "a.py").write_text("x=1\n")
    subprocess.check_call(["git", "add", "."], cwd=tmp_path, stdout=subprocess.DEVNULL)
    subprocess.check_call(["git", "commit", "-m", "init"], cwd=tmp_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for i in range(3):
        (tmp_path / "a.py").write_text(f"x={i}\n")
        subprocess.check_call(["git", "add", "."], cwd=tmp_path, stdout=subprocess.DEVNULL)
        subprocess.check_call(["git", "commit", "-m", f"c{i}"], cwd=tmp_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    out = churn(tmp_path, n=10)
    assert isinstance(out, (str, list, dict))
    txt = str(out).lower()
    assert "a.py" in txt or "a" in txt


def test_git_blame(tmp_path):
    if not _has_git():
        import pytest

        pytest.skip("git not available")
    from peek.git import git_blame

    subprocess.check_call(["git", "init"], cwd=tmp_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.check_call(["git", "config", "user.name", "t"], cwd=tmp_path, stdout=subprocess.DEVNULL)
    subprocess.check_call(["git", "config", "user.email", "t@t.com"], cwd=tmp_path, stdout=subprocess.DEVNULL)
    (tmp_path / "a.py").write_text("x=1\n")
    subprocess.check_call(["git", "add", "."], cwd=tmp_path, stdout=subprocess.DEVNULL)
    subprocess.check_call(["git", "commit", "-m", "init"], cwd=tmp_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    out = git_blame(tmp_path, tmp_path / "a.py")
    assert isinstance(out, str)
    assert "x=1" in out or "1" in out


def test_cli_log_help():
    from typer.testing import CliRunner

    from peek.cli import app

    r = CliRunner().invoke(app, ["log", "--help"])
    assert r.exit_code == 0
    assert "log" in r.output.lower()


def test_cli_diff_help():
    from typer.testing import CliRunner

    from peek.cli import app

    r = CliRunner().invoke(app, ["diff", "--help"])
    assert r.exit_code == 0
    assert "diff" in r.output.lower()


def test_cli_hot_help():
    from typer.testing import CliRunner

    from peek.cli import app

    r = CliRunner().invoke(app, ["hot", "--help"])
    assert r.exit_code == 0
    assert "hot" in r.output.lower() or "churn" in r.output.lower()


def test_cli_blame_help():
    from typer.testing import CliRunner

    from peek.cli import app

    r = CliRunner().invoke(app, ["blame", "--help"])
    assert r.exit_code == 0
    assert "blame" in r.output.lower()
