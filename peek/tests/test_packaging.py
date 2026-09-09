"""Issues #99 (Homebrew), #100 (smithery), #101 (winget/scoop) — manifest checks."""

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
VERSION = "0.5.0"
TARBALL = f"https://github.com/hariomlohardev/peek/archive/refs/tags/v{VERSION}.tar.gz"
TARBALL_SHA = "6f3854c79ce0819c032918ba3ea7f011d2e9a2e96d65d0a822e809c1a0d433b0"


def test_homebrew_formula():
    text = (ROOT / "Formula" / "peek.rb").read_text(encoding="utf-8")
    assert TARBALL in text
    assert TARBALL_SHA in text
    assert "virtualenv" in text
    assert "peek --version" in text


def test_scoop_manifest():
    manifest = json.loads((ROOT / "scoop" / "peek.json").read_text(encoding="utf-8"))
    assert manifest["version"] == VERSION
    assert manifest["url"] == TARBALL
    assert TARBALL_SHA in manifest["hash"]
    assert "checkver" in manifest and "autoupdate" in manifest


def test_winget_manifests():
    base = ROOT / "winget"
    version = (base / "hariomlohardev.peek.yaml").read_text(encoding="utf-8")
    installer = (base / "hariomlohardev.peek.installer.yaml").read_text(encoding="utf-8")
    locale = (base / "hariomlohardev.peek.locale.en-US.yaml").read_text(encoding="utf-8")
    for text in (version, installer, locale):
        assert "hariomlohardev.peek" in text
        assert VERSION in text
        assert "ManifestVersion: 1.6.0" in text
    assert TARBALL in installer
    assert TARBALL_SHA in installer.lower()


def test_smithery_yaml():
    text = (ROOT / "smithery.yaml").read_text(encoding="utf-8")
    assert "name: peek" in text
    assert "peek.mcp_server" in text
    for tool in ("peek_scan", "peek_rank", "peek_pack", "peek_find", "peek_graph", "peek_explain", "peek_trace"):
        assert tool in text


def test_docs_mentions_distribution():
    docs = (ROOT / "docs.md").read_text(encoding="utf-8").lower()
    assert "brew install" in docs
    assert "scoop" in docs
    assert "winget" in docs
    assert "smithery" in docs
