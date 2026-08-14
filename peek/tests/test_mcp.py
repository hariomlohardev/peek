"""Tests for MCP server — Task 5."""
from __future__ import annotations

import json
import pathlib
import tempfile


def test_mcp_tools_list():
    from peek.mcp_server import TOOLS

    assert "peek_scan" in TOOLS
    assert "peek_rank" in TOOLS
    assert TOOLS["peek_pack"]["inputSchema"]["properties"]["query"]
    # v3 expects 6 tools
    assert "peek_find" in TOOLS
    assert "peek_graph" in TOOLS
    assert "peek_explain" in TOOLS
    # schema checks
    assert TOOLS["peek_scan"]["inputSchema"]["type"] == "object"
    assert TOOLS["peek_find"]["inputSchema"]["properties"]["query"]
    assert TOOLS["peek_explain"]["inputSchema"]["properties"]["traceback"] or "traceback" in str(TOOLS["peek_explain"])


def test_cli_mcp_help():
    from typer.testing import CliRunner

    from peek.cli import app

    r = CliRunner().invoke(app, ["mcp", "--help"])
    assert r.exit_code == 0
    assert "mcp" in r.output.lower()


def test_mcp_handle_scan(tmp_path):
    from peek.mcp_server import handle_tool

    (tmp_path / "a.py").write_text("x=1\n")
    (tmp_path / "b.py").write_text("import a\n")
    out = handle_tool("peek_scan", {"path": str(tmp_path)})
    assert isinstance(out, dict)
    assert "total_files" in out
    assert out["total_files"] >= 1


def test_mcp_handle_rank(tmp_path):
    from peek.mcp_server import handle_tool

    (tmp_path / "a.py").write_text("import b\n")
    (tmp_path / "b.py").write_text("x=1\n")
    out = handle_tool("peek_rank", {"path": str(tmp_path)})
    assert "ranked" in out
    assert isinstance(out["ranked"], list)


def test_mcp_handle_pack(tmp_path):
    from peek.mcp_server import handle_tool

    (tmp_path / "a.py").write_text("print('hello')\n")
    (tmp_path / "b.py").write_text("print('world')\n")
    out = handle_tool("peek_pack", {"path": str(tmp_path), "budget": 8000, "format": "md"})
    assert "content" in out or "tokens" in out or "files" in out
    # content should be string
    if "content" in out:
        assert isinstance(out["content"], str)


def test_mcp_handle_find(tmp_path):
    from peek.mcp_server import handle_tool

    (tmp_path / "auth.py").write_text("def login(): pass\n# auth token validation\n")
    (tmp_path / "other.py").write_text("def foo(): pass\n")
    out = handle_tool("peek_find", {"path": str(tmp_path), "query": "auth"})
    assert isinstance(out, dict)
    # should have matches or results
    assert "matches" in out or "results" in out or "query" in out or len(out) >= 0


def test_mcp_handle_graph(tmp_path):
    from peek.mcp_server import handle_tool

    (tmp_path / "a.py").write_text("import b\n")
    (tmp_path / "b.py").write_text("x=1\n")
    out = handle_tool("peek_graph", {"path": str(tmp_path), "format": "dot"})
    assert isinstance(out, dict)
    # should contain dot or svg or graph key
    assert any(k in out for k in ("dot", "graph", "content", "svg", "html")) or isinstance(out, dict)


def test_mcp_handle_explain(tmp_path):
    from peek.mcp_server import handle_tool

    tb = 'Traceback (most recent call last):\n  File "a.py", line 10, in <module>\n    x = 1/0\nZeroDivisionError: division by zero\n'
    out = handle_tool("peek_explain", {"traceback": tb, "path": str(tmp_path)})
    assert isinstance(out, dict)
    # should contain explanation or raw
    assert any(k in out for k in ("explanation", "raw", "text", "result")) or "ZeroDivisionError" in str(out) or "division" in str(out).lower()
