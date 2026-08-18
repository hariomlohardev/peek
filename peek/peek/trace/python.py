"""Python AST parsing for trace — declarations + calls (Python only)."""

# ruff: noqa: SIM105, BLE001, F841

from __future__ import annotations

import ast
from pathlib import Path

from .models import FuncId, FuncNode, Param


def _unparse(node: ast.AST | None) -> str | None:
    if node is None:
        return None
    try:
        return ast.unparse(node)  # type: ignore[attr-defined]
    except Exception:
        return None


def _format_default(node: ast.AST | None) -> str | None:
    if node is None:
        return None
    try:
        val = _unparse(node)
        if val is None:
            return None
        if len(val) > 40:
            val = val[:37] + "..."
        return val
    except Exception:
        return None


class DeclVisitor(ast.NodeVisitor):
    def __init__(self, file: Path, rel: Path):
        self.file = file
        self.rel = rel
        self.stack: list[str] = []
        self.class_stack: list[str] = []
        self.nodes: list[FuncNode] = []
        self.import_alias: dict[str, str] = {}

    def _handle_func(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
        is_async = isinstance(node, ast.AsyncFunctionDef)
        q = ".".join(self.stack + [node.name]) if self.stack else node.name
        fid = FuncId(file=self.file, qualname=q)
        params: list[Param] = []
        args = node.args
        for arg in getattr(args, "posonlyargs", []):
            ann = _unparse(arg.annotation)
            params.append(Param(arg.arg, "posonly", ann, None))
        defaults = list(args.defaults or [])
        num_args = len(args.args)
        num_defaults = len(defaults)
        offset = num_args - num_defaults
        for i, arg in enumerate(args.args):
            ann = _unparse(arg.annotation)
            def_node = defaults[i - offset] if i >= offset else None
            default = _format_default(def_node) if def_node is not None else None
            params.append(Param(arg.arg, "arg", ann, default))
        if args.vararg:
            ann = _unparse(args.vararg.annotation)
            params.append(Param(args.vararg.arg, "vararg", ann, None))
        for arg, def_node in zip(getattr(args, "kwonlyargs", []), getattr(args, "kw_defaults", []), strict=False):
            ann = _unparse(arg.annotation)
            default = _format_default(def_node) if def_node is not None else None
            params.append(Param(arg.arg, "kwonly", ann, default))
        if args.kwarg:
            ann = _unparse(args.kwarg.annotation)
            params.append(Param(args.kwarg.arg, "kwarg", ann, None))
        returns = _unparse(node.returns)
        lineno = getattr(node, "lineno", 1)
        end_lineno = getattr(node, "end_lineno", lineno)
        col = getattr(node, "col_offset", 0)
        kind = "async" if is_async else "def"
        is_method = len(self.class_stack) > 0
        class_name = self.class_stack[-1] if is_method else None
        if is_method:
            kind = "method"
        try:
            doc = ast.get_docstring(node) or ""
        except Exception:
            doc = ""
        decos: list[str] = []
        for d in getattr(node, "decorator_list", []):
            try:
                decos.append(_unparse(d) or "")
            except Exception:
                decos.append("")
        fn = FuncNode(
            id=fid,
            name=node.name,
            qualname=q,
            file=self.file,
            rel=self.rel,
            lineno=lineno,
            end_lineno=end_lineno or lineno,
            col=col,
            kind=kind,
            params=params,
            returns=returns,
            docstring=doc,
            decorators=[d for d in decos if d],
            is_method=is_method,
            class_name=class_name,
        )
        self.nodes.append(fn)

    def visit_ClassDef(self, node: ast.ClassDef):
        self.stack.append(node.name)
        self.class_stack.append(node.name)
        self.generic_visit(node)
        self.class_stack.pop()
        self.stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._handle_func(node)
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._handle_func(node)
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            asname = alias.asname or alias.name.split(".")[0]
            self.import_alias[asname] = alias.name

    def visit_ImportFrom(self, node: ast.ImportFrom):
        mod = node.module or ""
        level = node.level or 0
        for alias in node.names:
            if alias.name == "*":
                continue
            asname = alias.asname or alias.name
            full = f"{mod}.{alias.name}" if mod else alias.name
            if level > 0:
                full = "." * level + full
            self.import_alias[asname] = full


class CallVisitor(ast.NodeVisitor):
    def __init__(self, func_node: FuncNode, source: str, import_alias: dict[str, str]):
        self.func_node = func_node
        self.source = source
        self.import_alias = import_alias
        self.calls: list[dict] = []
        self.param_names: set[str] = {p.name for p in func_node.params}
        self.local_results: set[str] = set()
        self._await_stack: list[bool] = []

    def visit_Assign(self, node: ast.Assign):
        has_call = any(isinstance(v, (ast.Call, ast.Await)) for v in [node.value])
        if has_call:
            for t in node.targets:
                if isinstance(t, ast.Name):
                    self.local_results.add(t.id)
                elif isinstance(t, (ast.Tuple, ast.List)):
                    for elt in t.elts:
                        if isinstance(elt, ast.Name):
                            self.local_results.add(elt.id)
        self.generic_visit(node)
        return

    def visit_AnnAssign(self, node: ast.AnnAssign):
        if isinstance(node.value, (ast.Call, ast.Await)) and isinstance(node.target, ast.Name):
            self.local_results.add(node.target.id)
        self.generic_visit(node)

    def visit_Await(self, node: ast.Await):
        self._await_stack.append(True)
        self.generic_visit(node)
        self._await_stack.pop()

    def visit_Call(self, node: ast.Call):
        callee_raw, callee_name = _extract_callee(node)
        if not callee_name:
            self.generic_visit(node)
            return
        call_args: list[str] = []
        arg_sources: list[str] = []
        for arg in node.args:
            try:
                txt = _unparse(arg)
                if txt is None:
                    txt = ""
                if len(txt) > 60:
                    txt = txt[:57] + "..."
            except Exception:
                txt = ""
            call_args.append(txt or "")
            arg_sources.append(_classify_arg(arg, self.param_names, self.local_results))
        for kw in node.keywords:
            try:
                txt = _unparse(kw.value) if kw.value else ""
                if txt is None:
                    txt = ""
                if len(txt) > 60:
                    txt = txt[:57] + "..."
            except Exception:
                txt = ""
            label = f"{kw.arg}={txt}" if kw.arg else txt
            call_args.append(label)
            src = _classify_arg(kw.value, self.param_names, self.local_results) if kw.value else "UNKNOWN"
            arg_sources.append(src)
        assign_target = None
        is_await = bool(self._await_stack)
        is_chained = False
        try:
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Call):
                is_chained = True
        except Exception:
            pass
        lineno = getattr(node, "lineno", self.func_node.lineno)
        col = getattr(node, "col_offset", 0)
        self.calls.append(
            {
                "callee_raw": callee_raw,
                "callee_name": callee_name,
                "lineno": lineno,
                "col": col,
                "call_args": call_args,
                "arg_sources": arg_sources,
                "assign_target": assign_target,
                "is_await": is_await,
                "is_chained": is_chained,
            }
        )
        self.generic_visit(node)


def _extract_callee(node: ast.Call) -> tuple[str, str]:
    try:
        raw = _unparse(node.func) or ""
        if isinstance(node.func, ast.Name):
            return raw, node.func.id
        if isinstance(node.func, ast.Attribute):
            return raw, node.func.attr
        if raw:
            name = raw.split(".")[-1].split("(")[0].strip()
            return raw, name
        return raw, ""
    except Exception:
        return "", ""


def _classify_arg(node: ast.AST | None, param_names: set[str], local_results: set[str]) -> str:
    if node is None:
        return "UNKNOWN"
    if isinstance(node, ast.Constant):
        return "LITERAL"
    if isinstance(node, (ast.List, ast.Dict, ast.Set, ast.Tuple)):
        return "LITERAL"
    if isinstance(node, ast.Name):
        if node.id in param_names:
            return "PARAM_THROUGH"
        if node.id in local_results:
            return "LOCAL_RESULT"
        return "UNKNOWN"
    if isinstance(node, ast.Attribute):
        try:
            if isinstance(node.value, ast.Name) and node.value.id in param_names:
                return "PARAM_THROUGH"
        except Exception:
            pass
        return "UNKNOWN"
    return "UNKNOWN"


def parse_python_file(file: Path, rel: Path, source: str) -> tuple[list[FuncNode], dict[str, str]]:
    try:
        tree = ast.parse(source, filename=str(file))
    except Exception:
        return [], {}
    visitor = DeclVisitor(file, rel)
    try:
        visitor.visit(tree)
    except Exception:
        pass
    return visitor.nodes, visitor.import_alias


def extract_calls_for_func(func_node: FuncNode, source: str, import_alias: dict[str, str]) -> list[dict]:
    try:
        tree = ast.parse(source, filename=str(func_node.file))
    except Exception:
        return []

    class Finder(ast.NodeVisitor):
        def __init__(self):
            self.stack: list[str] = []
            self.found = None

        def visit_ClassDef(self, node: ast.ClassDef):
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef):
            q = ".".join(self.stack + [node.name]) if self.stack else node.name
            if q == func_node.qualname and getattr(node, "lineno", -1) == func_node.lineno:
                self.found = node
                return
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
            q = ".".join(self.stack + [node.name]) if self.stack else node.name
            if q == func_node.qualname and getattr(node, "lineno", -1) == func_node.lineno:
                self.found = node
                return
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

    finder = Finder()
    try:
        finder.visit(tree)
    except Exception:
        pass
    if finder.found is None:
        return []
    visitor = CallVisitor(func_node, source, import_alias)
    try:
        visitor.visit(finder.found)
    except Exception:
        return visitor.calls
    lines = source.splitlines()
    for c in visitor.calls:
        if c["assign_target"] is None:
            try:
                lineno = c["lineno"]
                if 1 <= lineno <= len(lines):
                    line = lines[lineno - 1]
                    raw = c["callee_raw"]
                    idx = line.find(raw)
                    if idx > 0:
                        before = line[:idx]
                        if "=" in before:
                            left = before.split("=")[0].strip().split(",")[0].strip().split()[-1]
                            if left.isidentifier():
                                c["assign_target"] = left
            except Exception:
                pass
    return visitor.calls


def extract_calls_per_file(
    file: Path, rel: Path, source: str, func_nodes: list[FuncNode], import_alias: dict[str, str]
) -> dict[FuncId, list[dict]]:
    """Optimized per-file extraction: parse once, visit each func subtree once."""
    if not func_nodes:
        return {}
    try:
        tree = ast.parse(source, filename=str(file))
    except Exception:
        return {fn.id: [] for fn in func_nodes}

    func_map: dict[tuple[str, int], ast.AST] = {}

    class Collector(ast.NodeVisitor):
        def __init__(self):
            self.stack: list[str] = []

        def visit_ClassDef(self, node: ast.ClassDef):
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef):
            q = ".".join(self.stack + [node.name]) if self.stack else node.name
            key = (q, getattr(node, "lineno", -1))
            func_map[key] = node
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
            q = ".".join(self.stack + [node.name]) if self.stack else node.name
            key = (q, getattr(node, "lineno", -1))
            func_map[key] = node
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

    collector = Collector()
    try:
        collector.visit(tree)
    except Exception:
        pass

    result: dict[FuncId, list[dict]] = {}
    lines = source.splitlines()
    for fn in func_nodes:
        key = (fn.qualname, fn.lineno)
        ast_node = func_map.get(key)
        if ast_node is None:
            found = None
            for (q, ln), n in func_map.items():
                if ln == fn.lineno and q.endswith(fn.name):
                    found = n
                    break
            ast_node = found
        if ast_node is None:
            result[fn.id] = []
            continue
        visitor = CallVisitor(fn, source, import_alias)
        try:
            visitor.visit(ast_node)
        except Exception:
            result[fn.id] = []
            continue
        for c in visitor.calls:
            if c["assign_target"] is None:
                try:
                    lineno = c["lineno"]
                    if 1 <= lineno <= len(lines):
                        line = lines[lineno - 1]
                        raw = c["callee_raw"]
                        idx = line.find(raw)
                        if idx > 0:
                            before = line[:idx]
                            if "=" in before:
                                left = before.split("=")[0].strip().split(",")[0].strip().split()[-1]
                                if left.isidentifier():
                                    c["assign_target"] = left
                except Exception:
                    pass
        result[fn.id] = visitor.calls
    return result
