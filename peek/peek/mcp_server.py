"""MCP stdio server — exposes peek tools to Claude/Cursor via JSON-RPC.

Implements minimal MCP (2024-11-05) over stdio:
  - initialize
  - tools/list
  - tools/call  -> peek_scan, peek_rank, peek_pack, peek_find, peek_graph, peek_explain
No hard dep on `mcp` package — stdio JSON lines fallback always works.
If `mcp` is installed, its server transport could be used later, but not required.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from peek import __version__

TOOLS = {
    "peek_scan": {
        "name": "peek_scan",
        "description": "Scan repo — file stats, languages, tech stack, entry candidates (via peek.scanner.scan).",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Path to repo (default '.')"}},
            "required": [],
        },
    },
    "peek_rank": {
        "name": "peek_rank",
        "description": "Ranked Start Here — import graph PageRank + in-degree + entry bonus (via peek.analyzer.analyze).",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Path to repo"}},
            "required": [],
        },
    },
    "peek_pack": {
        "name": "peek_pack",
        "description": "Pack ranked files for LLM context within token budget (via peek.pack.build_pack).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to repo"},
                "query": {"type": "string", "description": "Keyword or URL to filter"},
                "budget": {"type": "integer", "description": "Token budget (default 8000)"},
                "format": {"type": "string", "description": "Format md|xml|txt", "enum": ["md", "xml", "txt"]},
            },
            "required": [],
        },
    },
    "peek_find": {
        "name": "peek_find",
        "description": "Find files by keyword — filename + content + semantic BM25 (via peek.find.find_matches).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "query": {"type": "string", "description": "Keyword / intent query"},
                "limit": {"type": "integer", "description": "Max results"},
            },
            "required": ["query"],
        },
    },
    "peek_graph": {
        "name": "peek_graph",
        "description": "Export import graph as DOT/SVG/HTML (via peek.graph.export_graph).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "format": {"type": "string", "enum": ["dot", "svg", "html"], "description": "Output format"},
            },
            "required": [],
        },
    },
    "peek_explain": {
        "name": "peek_explain",
        "description": "Explain a Python traceback with scan-aware hints (via peek.wtf.explain_tb).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Repo path for context"},
                "traceback": {"type": "string", "description": "Traceback text"},
                "file": {"type": "string", "description": "File containing traceback"},
            },
            "required": [],
        },
    },
}


def _resolve_path_arg(args: dict) -> Path:
    try:
        p = Path(args.get("path", ".") or ".")
    except Exception:
        p = Path(".")
    # if not exists, try cwd join
    try:
        if not p.exists():
            cand = Path.cwd() / p
            if cand.exists():
                return cand
        if p.is_file():
            return p.parent
        return p
    except Exception:
        return Path.cwd()


def handle_tool(name: str, args: dict | None) -> dict:
    """Dispatch tool call. Never raises — returns dict with error key on failure."""
    if args is None:
        args = {}
    if not isinstance(args, dict):
        try:
            args = dict(args)  # type: ignore
        except Exception:
            args = {}
    name = str(name)
    # normalize path
    path = _resolve_path_arg(args)

    try:
        if name == "peek_scan":
            from peek.scanner import scan

            sr = scan(path)
            return {
                "root": str(sr.root),
                "total_files": sr.stats.get("total_files", 0),
                "total_loc": sr.stats.get("total_loc", 0),
                "total_bytes": sr.stats.get("total_bytes", 0),
                "by_lang": sr.stats.get("by_lang", {}),
                "tech_stack": sr.tech_stack,
                "entry_candidates": [str(p) for p in sr.entry_candidates[:5]],
            }
        elif name == "peek_rank":
            from peek.analyzer import analyze
            from peek.scanner import scan

            sr = scan(path)
            ar = analyze(sr)
            return {
                "root": str(ar.root),
                "summary": ar.summary,
                "tech_stack": ar.tech_stack,
                "ranked": [
                    {"path": str(r.rel), "score": round(float(r.score), 2), "reasons": r.reasons}
                    for r in ar.ranked[:10]
                ],
                "graph_nodes": len(ar.graph),
                "graph_edges": sum(len(v) for v in ar.graph.values()),
            }
        elif name == "peek_pack":
            from peek.analyzer import analyze
            from peek.pack import build_pack
            from peek.scanner import scan

            sr = scan(path)
            ar = analyze(sr)
            query = args.get("query")
            # budget may be int or string
            budget = args.get("budget", 8000)
            try:
                budget = int(budget)
            except Exception:
                budget = 8000
            fmt = args.get("format", "md")
            if fmt not in ("md", "xml", "txt"):
                fmt = "md"
            out, files, toks = build_pack(sr, ar, query=query, budget=budget, format=fmt)
            return {"content": out[:8000], "files": [str(f) for f in files], "tokens": toks, "query": query, "format": fmt}
        elif name == "peek_find":
            from peek.analyzer import analyze
            from peek.find import find_matches
            from peek.scanner import scan

            sr = scan(path)
            ar = analyze(sr)
            query = str(args.get("query", "") or "")
            limit = args.get("limit", 20)
            try:
                limit = int(limit)
            except Exception:
                limit = 20
            matches = find_matches(query, sr, ar, limit=limit)
            return {
                "query": query,
                "matches": [
                    {"path": str(m["rel"]), "score": m["score"], "reason": m["reason"], "preview": m["preview"]}
                    for m in matches
                ],
            }
        elif name == "peek_graph":
            from peek.analyzer import analyze
            from peek.graph import export_graph
            from peek.scanner import scan

            sr = scan(path)
            ar = analyze(sr)
            fmt = str(args.get("format", "dot") or "dot")
            if fmt not in ("dot", "svg", "html"):
                fmt = "dot"
            content = export_graph(ar, format=fmt)
            return {"format": fmt, "content": content[:12000], "graph_nodes": len(ar.graph)}
        elif name == "peek_explain":
            from peek.wtf import explain_tb, parse_traceback

            tb = args.get("traceback") or args.get("text") or ""
            if not tb and args.get("file"):
                try:
                    p = Path(args["file"])
                    if p.exists() and p.is_file():
                        tb = p.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    tb = ""
            # also try reading path arg's common traceback file?
            if not tb:
                tb = ""
            info = parse_traceback(str(tb))
            if not info:
                return {"explanation": str(tb)[:4000], "raw": str(tb)[:4000], "hint": "No traceback found"}
            try:
                from peek.analyzer import analyze
                from peek.scanner import scan

                sr = scan(path)
                ar = analyze(sr)
                explanation = explain_tb(info, sr, ar)
                return {"explanation": str(explanation)[:6000], "raw": info.raw[:3000]}
            except Exception:
                return {"explanation": info.raw[:6000], "raw": info.raw[:3000]}
        else:
            return {"error": f"Unknown tool '{name}'", "available": list(TOOLS.keys())}
    except Exception as e:
        return {"error": str(e), "tool": name}


def _tools_list_with_names() -> list[dict]:
    """Return TOOLS values ensuring each has 'name' key (for MCP clients)."""
    out: list[dict] = []
    for key, spec in TOOLS.items():
        if "name" not in spec:
            out.append({"name": key, **spec})
        else:
            # ensure name matches key
            entry = dict(spec)
            entry["name"] = key
            out.append(entry)
    return out


def main() -> None:
    """Stdio JSON-RPC loop. Reads one JSON per line, writes one JSON per line.

    Supports both MCP JSON-RPC 2.0 (with id/jsonrpc) and simple method-only (brief fallback).
    Handles: initialize, tools/list, tools/call, ping, notifications/* (ignored).
    """
    import sys as _sys

    stdin = _sys.stdin
    stdout = _sys.stdout
    # Use line-buffered
    for raw_line in stdin:
        try:
            line = raw_line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                # try to handle multiple jsons in one line? skip
                continue

            # Batch?
            if isinstance(msg, list):
                # Respond to each? For MVP, handle first
                msg = msg[0] if msg else {}
            if not isinstance(msg, dict):
                continue

            method = msg.get("method")
            params = msg.get("params", {}) or {}
            msg_id = msg.get("id")

            # Notifications: ignore but acknowledge? No response needed for notifications (no id)
            if method in ("notifications/initialized", "notifications/cancelled"):
                continue

            # Handle initialize
            if method == "initialize":
                result = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}, "logging": {}},
                    "serverInfo": {"name": "peek", "version": __version__},
                }
                resp: dict = {"jsonrpc": "2.0", "id": msg_id, "result": result}
                stdout.write(json.dumps(resp) + "\n")
                stdout.flush()
                continue

            # Handle tools/list (MCP)
            if method in ("tools/list", "tools/list_tools", "list_tools"):
                tools = _tools_list_with_names()
                if msg_id is not None:
                    resp = {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": tools}}
                else:
                    # brief fallback without jsonrpc
                    resp = {"result": {"tools": tools}}
                stdout.write(json.dumps(resp) + "\n")
                stdout.flush()
                continue

            # Handle tools/call
            if method in ("tools/call", "tools/call_tool"):
                # params: {name, arguments}
                name = params.get("name") if isinstance(params, dict) else None
                args = params.get("arguments", {}) if isinstance(params, dict) else {}
                if name is None and isinstance(msg.get("params"), dict):
                    # fallback: msg["params"]["name"]
                    name = msg["params"].get("name")
                    args = msg["params"].get("arguments", {})
                # Also brief used msg["params"]["name"] directly
                if name is None:
                    # try msg["params"] as tool name? no
                    name = ""
                try:
                    result = handle_tool(str(name), args if isinstance(args, dict) else {})
                    # MCP expects result.content = [{type:text, text: json}]
                    content = [{"type": "text", "text": json.dumps(result)}]
                    payload = {"content": content, "isError": False}
                    if msg_id is not None:
                        resp = {"jsonrpc": "2.0", "id": msg_id, "result": payload}
                    else:
                        resp = {"result": payload}
                except Exception as e:
                    if msg_id is not None:
                        resp = {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32603, "message": str(e)}}
                    else:
                        resp = {"error": str(e)}
                stdout.write(json.dumps(resp) + "\n")
                stdout.flush()
                continue

            # ping
            if method == "ping":
                if msg_id is not None:
                    resp = {"jsonrpc": "2.0", "id": msg_id, "result": {}}
                else:
                    resp = {"result": {}}
                stdout.write(json.dumps(resp) + "\n")
                stdout.flush()
                continue

            # Unknown method with id -> error
            if msg_id is not None:
                resp = {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}
                stdout.write(json.dumps(resp) + "\n")
                stdout.flush()
            else:
                # no id, but method unknown and no id -> per brief, write error to stderr?
                print(json.dumps({"error": f"Method not found: {method}"}), file=_sys.stderr)
                _sys.stderr.flush()
        except Exception as e:
            try:
                # try to respond with error if we have id
                msg_id = locals().get("msg_id", None)
                if msg_id is not None:
                    resp = {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32603, "message": str(e)}}
                    stdout.write(json.dumps(resp) + "\n")
                    stdout.flush()
                else:
                    print(json.dumps({"error": str(e)}), file=_sys.stderr)
                    _sys.stderr.flush()
            except Exception:
                try:
                    print(json.dumps({"error": str(e)}), file=_sys.stderr)
                except Exception:
                    pass
