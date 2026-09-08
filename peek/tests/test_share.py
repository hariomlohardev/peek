"""Issue #31 — `peek --share` uploads HTML to gist (mocked network)."""

import io
import json
import urllib.error

import pytest
from typer.testing import CliRunner

from peek.cli import app
from peek.share import ShareError, upload_gist

runner = CliRunner()


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


def _mock_urlopen(monkeypatch, payload, seen):
    def fake(req, timeout=15):
        seen["url"] = req.full_url
        seen["auth"] = req.get_header("Authorization")
        seen["body"] = json.loads(req.data.decode("utf-8"))
        return _FakeResp(payload)

    monkeypatch.setattr("peek.share.urllib.request.urlopen", fake)


def test_upload_gist_returns_url(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "tok123")
    seen = {}
    _mock_urlopen(monkeypatch, {"html_url": "https://gist.github.com/u/abc"}, seen)
    url = upload_gist("<html>peek</html>")
    assert url == "https://gist.github.com/u/abc"
    assert seen["url"] == "https://api.github.com/gists"
    assert seen["auth"] == "Bearer tok123"
    assert seen["body"]["files"]["peek-report.html"]["content"] == "<html>peek</html>"
    assert seen["body"]["public"] is False


def test_upload_gist_needs_token(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with pytest.raises(ShareError, match="GITHUB_TOKEN"):
        upload_gist("<html>x</html>")


def test_upload_gist_http_error(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "bad")

    def fake(req, timeout=15):
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, io.BytesIO(b"{}"))

    monkeypatch.setattr("peek.share.urllib.request.urlopen", fake)
    with pytest.raises(ShareError, match="HTTP 401"):
        upload_gist("<html>x</html>")


def test_share_cli_needs_token(monkeypatch, tmp_path):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    r = runner.invoke(app, ["--share"])
    assert r.exit_code == 1, r.output
    assert "GITHUB_TOKEN" in r.output


def test_share_cli_prints_url(monkeypatch, tmp_path):
    monkeypatch.setenv("GITHUB_TOKEN", "tok123")
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    seen = {}
    _mock_urlopen(monkeypatch, {"html_url": "https://gist.github.com/u/abc"}, seen)
    r = runner.invoke(app, ["--share"])
    assert r.exit_code == 0, r.output
    assert "https://gist.github.com/u/abc" in r.output
