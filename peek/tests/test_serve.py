"""Issues #23 (serve) + #75 (--open)."""

import urllib.request

from typer.testing import CliRunner

from peek.cli import app
from peek.serve import ReportServer

runner = CliRunner()


def _tiny_repo(tmp_path):
    p = tmp_path / "repo"
    p.mkdir()
    (p / "a.py").write_text("x = 1\n", encoding="utf-8")
    return p


def test_serve_help():
    r = runner.invoke(app, ["serve", "--help"])
    assert r.exit_code == 0, r.output
    assert "--open" in r.output
    assert "4181" in r.output


def test_serve_serves_html(tmp_path):
    repo = _tiny_repo(tmp_path)
    server = ReportServer(repo, port=0, watch=False, directory=tmp_path / "out")
    server.start()
    try:
        with urllib.request.urlopen(server.url, timeout=5) as resp:
            assert resp.status == 200
            body = resp.read().decode("utf-8", "replace")
        assert "<html" in body.lower() or "peek" in body.lower()
        assert "a.py" in body
    finally:
        server.stop()


def test_serve_open_calls_browser(tmp_path, monkeypatch):
    repo = _tiny_repo(tmp_path)
    calls = []
    monkeypatch.setattr("peek.serve.webbrowser.open", lambda url: calls.append(url))
    server = ReportServer(repo, port=0, open_browser=True, watch=False, directory=tmp_path / "out")
    server.start()
    try:
        assert len(calls) == 1
        assert calls[0] == server.url
    finally:
        server.stop()


def test_serve_rebuild_updates_html(tmp_path):
    repo = _tiny_repo(tmp_path)
    server = ReportServer(repo, port=0, watch=False, directory=tmp_path / "out")
    server.start()
    try:
        before = (tmp_path / "out" / "index.html").read_text(encoding="utf-8")
        assert "a.py" in before
        (repo / "b.py").write_text("y = 2\n", encoding="utf-8")
        server.rebuild()
        after = (tmp_path / "out" / "index.html").read_text(encoding="utf-8")
        assert "b.py" in after
    finally:
        server.stop()
