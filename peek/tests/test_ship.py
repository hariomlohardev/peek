"""Issue #38 — `peek ship` AI commit + PR body (git fully mocked)."""

from typer.testing import CliRunner

from peek import ship as ship_mod
from peek.cli import app
from peek.ship import build_message, conventional_type, heuristic_subject, run_ship

runner = CliRunner()


def _fake_git_factory(calls, staged="peek/peek/serve.py", status="A  peek/peek/serve.py"):
    def fake(args, cwd, timeout=10):
        calls.append(args)
        if args[:3] == ["diff", "--staged", "--name-only"]:
            return staged
        if args[:2] == ["status", "--porcelain"]:
            return status
        if args[0] == "commit":
            return "created"
        if args[0] == "push":
            return "pushed"
        return ""

    return fake


def test_dry_run_prints_without_committing(monkeypatch):
    calls = []
    monkeypatch.setattr(ship_mod, "_git", _fake_git_factory(calls))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    import pathlib
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        res = run_ship(pathlib.Path(td), dry_run=True, use_llm=False)
    assert res["subject"].startswith("feat")
    assert "Start Here" in res["body"]
    assert "peek/peek/serve.py" in res["body"]
    assert res["committed"] is False
    assert not any(c[0] == "commit" for c in calls)


def test_yolo_commits_and_pushes(monkeypatch):
    calls = []
    monkeypatch.setattr(ship_mod, "_git", _fake_git_factory(calls))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    import pathlib
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        res = run_ship(pathlib.Path(td), dry_run=False, yolo=True, use_llm=False)
    assert res["committed"] is True
    assert res["pushed"] is True
    assert any(c[0] == "commit" for c in calls)
    assert any(c[0] == "push" for c in calls)


def test_no_push_without_yolo(monkeypatch):
    calls = []
    monkeypatch.setattr(ship_mod, "_git", _fake_git_factory(calls))
    import pathlib
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        res = run_ship(pathlib.Path(td), dry_run=False, yolo=False, use_llm=False)
    assert res["committed"] is True
    assert res["pushed"] is False
    assert not any(c[0] == "push" for c in calls)


def test_nothing_staged_graceful(monkeypatch):
    monkeypatch.setattr(ship_mod, "_git", _fake_git_factory([], staged="", status=""))
    import pathlib
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        res = run_ship(pathlib.Path(td), dry_run=True, use_llm=False)
    assert res["files"] == []
    assert "git add" in res["note"]


def test_type_classification():
    assert conventional_type(["docs.md", "docs/x.md"], set()) == "docs"
    assert conventional_type(["peek/tests/test_x.py"], set()) == "test"
    assert conventional_type([".github/workflows/ci.yml"], set()) == "ci"
    assert conventional_type(["peek/peek/a.py"], {"peek/peek/a.py"}) == "feat"
    assert conventional_type(["peek/peek/a.py"], set()) == "fix"
    subj = heuristic_subject(["peek/peek/serve.py"], {"peek/peek/serve.py"})
    assert subj.startswith("feat(serve): add")


def test_ship_help_and_alias():
    for cmd in ("ship", "commit"):
        r = runner.invoke(app, [cmd, "--help"])
        assert r.exit_code == 0, r.output
        assert "--yolo" in r.output and "--dry-run" in r.output


def test_ship_dry_run_cli_no_repo(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    r = runner.invoke(app, ["ship", "--dry-run"])
    assert r.exit_code == 0, r.output
    assert "git add" in r.output or "Nothing staged" in r.output


def test_build_message_offline_without_key(monkeypatch):
    calls = []
    monkeypatch.setattr(ship_mod, "_git", _fake_git_factory(calls))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    import pathlib
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        subject, body, files = build_message(pathlib.Path(td), use_llm=True)
    assert subject.startswith("feat")  # heuristic fallback, no API key
    assert files == ["peek/peek/serve.py"]
