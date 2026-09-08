"""Issue #37 — peek-vscode scaffold checks (no node needed)."""

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
EXT = ROOT / "peek-vscode"


def test_package_json_contributes_command():
    pkg = json.loads((EXT / "package.json").read_text(encoding="utf-8"))
    commands = [c["command"] for c in pkg["contributes"]["commands"]]
    assert "peek-vscode.peek" in commands
    views = pkg["contributes"]["views"]["explorer"]
    assert any(v["id"] == "peekStartHere" for v in views)
    for keyword in ("code map", "architecture visualizer", "import graph"):
        assert keyword in pkg["keywords"]


def test_extension_uses_peek_json_and_webview():
    src = (EXT / "src" / "extension.ts").read_text(encoding="utf-8")
    assert "analyze" in src and "--json" in src
    assert "createWebviewPanel" in src
    assert "vscode.open" in src
    assert "registerTreeDataProvider" in src


def test_docs_has_vscode_section():
    docs = (ROOT / "docs.md").read_text(encoding="utf-8")
    assert "VS Code" in docs
    assert "Peek: Map Workspace" in docs


def test_tsconfig_strict():
    tsconfig = (EXT / "tsconfig.json").read_text(encoding="utf-8")
    assert '"strict": true' in tsconfig
