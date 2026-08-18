"""Builder for Python-only trace graph."""

# ruff: noqa: SIM102, F841

from __future__ import annotations

from pathlib import Path

from peek.scanner import ScanResult

from .models import CallSite, FuncId, FuncNode, TraceGraph
from .python import extract_calls_per_file, parse_python_file


def _build_module_index(files, root: Path) -> dict[str, Path]:
    index: dict[str, Path] = {}
    for f in files:
        if f.language != "python":
            continue
        rel = f.rel
        parts = rel.with_suffix("").parts
        if not parts:
            continue
        if parts[-1] == "__init__":
            parts = parts[:-1]
        if not parts:
            continue
        if parts[0] in ("src", "app", "lib", "source", "project") and len(parts) > 1:
            parts = parts[1:]
        if not parts:
            continue
        mod = ".".join(parts)
        index[mod] = f.path
    return index


def _resolve_module_file(
    import_str: str, current_file: Path, module_index: dict[str, Path], root: Path
) -> Path | None:
    if import_str.startswith("."):
        level = len(import_str) - len(import_str.lstrip("."))
        mod = import_str.lstrip(".")
        try:
            cur_rel = current_file.relative_to(root)
        except Exception:
            cur_rel = Path(current_file.name)
        cur_parts = list(cur_rel.with_suffix("").parts)
        if cur_parts and cur_parts[-1] == "__init__":
            cur_parts = cur_parts[:-1]
        # if current is not __init__, package is parent
        if current_file.name != "__init__.py":
            package_parts = cur_parts[:-1] if len(cur_parts) > 1 else []
        else:
            package_parts = cur_parts
        if level == 1:
            base = package_parts
        else:
            keep = len(package_parts) - (level - 1)
            if keep < 0:
                return None
            base = package_parts[:keep] if keep > 0 else []
        full_parts = list(base) + mod.split(".") if mod else list(base)
        if not full_parts:
            return None
        full = ".".join(full_parts)
        # try exact, then prefix
        if full in module_index:
            return module_index[full]
        # longest prefix match
        best = None
        best_len = -1
        for k, v in module_index.items():
            if full == k or full.startswith(k + "."):
                if len(k) > best_len:
                    best = v
                    best_len = len(k)
        return best
    else:
        if import_str in module_index:
            return module_index[import_str]
        # try prefix
        best = None
        best_len = -1
        for k, v in module_index.items():
            if import_str == k or import_str.startswith(k + "."):
                if len(k) > best_len:
                    best = v
                    best_len = len(k)
        return best


def build_trace_graph(scan_result: ScanResult) -> TraceGraph:
    root = scan_result.root
    graph = TraceGraph(root=root)
    py_files = [f for f in scan_result.files if f.language == "python"]
    if not py_files:
        graph.warnings.append("No Python files found in scan")
        return graph
    file_to_nodes: dict[Path, list[FuncNode]] = {}
    file_to_alias: dict[Path, dict[str, str]] = {}
    file_to_source: dict[Path, str] = {}
    module_index = _build_module_index(scan_result.files, root)
    qual_index: dict[tuple[Path, str], FuncId] = {}
    bare_index: dict[str, list[FuncId]] = {}
    for f in py_files:
        try:
            text = f.path.read_text(encoding="utf-8", errors="ignore")
            if text.startswith("﻿"):
                text = text.lstrip("﻿")
        except Exception:
            file_to_nodes[f.path] = []
            file_to_alias[f.path] = {}
            continue
        file_to_source[f.path] = text
        nodes, alias = parse_python_file(f.path, f.rel, text)
        file_to_nodes[f.path] = nodes
        file_to_alias[f.path] = alias
        for node in nodes:
            fid = node.id
            graph.nodes[fid] = node
            qual_index[(f.path, node.qualname)] = fid
            qual_index[(f.path, node.name)] = fid
            bare_index.setdefault(node.name, []).append(fid)
            bare_index.setdefault(node.qualname, []).append(fid)
            # also index by qualname alone for suffix fallback
            bare_index.setdefault(node.qualname.split(".")[-1], []).append(fid)

    # second pass: build qualifier for resolver
    # Prepare file_groups
    for fid, node in list(graph.nodes.items()):
        graph.file_groups.setdefault(node.file, []).append(fid)

    # resolve calls
    stdlib_externals = {
        "print", "len", "range", "open", "str", "int", "float", "bool", "list", "dict", "set", "tuple",
        "enumerate", "zip", "map", "filter", "sorted", "reversed", "sum", "min", "max", "abs", "all", "any",
        "isinstance", "issubclass", "hasattr", "getattr", "setattr", "type", "super", "input", "repr",
        "json", "os", "sys", "pathlib", "re", "collections", "itertools", "functools", "typing", "dataclasses",
        "ast", "inspect", "logging", "time", "datetime", "math", "random", "hashlib", "http", "unittest", "pytest",
        "tempfile", "shutil", "subprocess", "threading", "asyncio",
    }

    for file_path, nodes in file_to_nodes.items():
        if not nodes:
            continue
        source = file_to_source.get(file_path, "")
        alias_map = file_to_alias.get(file_path, {})
        per_file_calls = extract_calls_per_file(file_path, nodes[0].rel, source, nodes, alias_map)
        for fid, raw_calls in per_file_calls.items():
            node = graph.nodes[fid]
            for rc in raw_calls:
                callee_raw = rc["callee_raw"]
                callee_name = rc["callee_name"]
                lineno = rc["lineno"]
                col = rc["col"]
                call_args = rc["call_args"]
                arg_sources = rc["arg_sources"]
                assign_target = rc["assign_target"]
                is_await = rc["is_await"]
                is_chained = rc["is_chained"]
                callee_resolved: FuncId | None = None
                is_external = False
                external_label: str | None = None

                # 1. alias resolution
                if "." in callee_raw:
                    root_name = callee_raw.split(".")[0]
                    if root_name in alias_map:
                        mapped = alias_map[root_name]
                        # mapped may be relative
                        if mapped.startswith("."):
                            resolved_path = _resolve_module_file(mapped, file_path, module_index, root)
                            if resolved_path:
                                # suffix is remainder after root_name
                                suffix = callee_raw[len(root_name):]  # ".attr..."
                                # extract bare name after last dot
                                bare = callee_name
                                # try qual_index lookup in resolved file
                                for suffix_try in [bare, suffix.lstrip(".").split(".")[-1]]:
                                    cand = qual_index.get((resolved_path, suffix_try))
                                    if cand:
                                        callee_resolved = cand
                                        break
                                    # also try full qualname
                                    cand2 = qual_index.get((resolved_path, callee_raw.replace(root_name, mapped.split(".")[-1], 1)))
                                    if cand2:
                                        callee_resolved = cand2
                                        break
                        else:
                            # absolute import like "pkg.mod"
                            # try to resolve via module_index
                            mod_part = mapped
                            # callee_raw like "alias.func" -> "pkg.mod.func"
                            remainder = callee_raw[len(root_name):]
                            if remainder.startswith("."):
                                # try to resolve file for mod_part
                                resolved_path = module_index.get(mod_part)
                                if not resolved_path:
                                    resolved_path = _resolve_module_file(mod_part, file_path, module_index, root)
                                if resolved_path:
                                    # lookup bare in that file
                                    cand = qual_index.get((resolved_path, callee_name))
                                    if cand:
                                        callee_resolved = cand
                                    else:
                                        # try qualname
                                        cand = qual_index.get((resolved_path, remainder.lstrip(".").split(".")[-1]))
                                        if cand:
                                            callee_resolved = cand
                                # also try bare index fallback
                                if not callee_resolved:
                                    # check bare_index for name
                                    cands = bare_index.get(callee_name, [])
                                    # prefer same package?
                                    # filter by path containing mod_part last component
                                    filtered = [c for c in cands if mod_part.split(".")[-1] in str(c.file)]
                                    if filtered:
                                        callee_resolved = filtered[0]
                            else:
                                # just alias itself is a function?
                                cands = bare_index.get(mapped.split(".")[-1], [])
                                if cands:
                                    callee_resolved = cands[0]
                # 2. try local file qualname
                if not callee_resolved:
                    # direct qualname in same file
                    cand = qual_index.get((file_path, callee_raw))
                    if cand:
                        callee_resolved = cand
                    else:
                        cand = qual_index.get((file_path, callee_name))
                        if cand:
                            callee_resolved = cand
                # 3. try bare index across files
                if not callee_resolved:
                    cands = bare_index.get(callee_name, [])
                    if len(cands) == 1:
                        callee_resolved = cands[0]
                    elif len(cands) > 1:
                        # prefer same file already checked, else check if cross_file will be allowed later
                        # Use heuristic: if multiple, pick one where file shares directory with caller?
                        # For now leave unresolved to be treated as external or filtered by cross_file
                        # But we keep as unresolved and will handle in query filtering
                        # Try to find candidate in same directory
                        caller_dir = file_path.parent
                        same_dir = [c for c in cands if c.file.parent == caller_dir]
                        if same_dir:
                            callee_resolved = same_dir[0]
                        else:
                            # leave unresolved, caller will see as external
                            pass
                # 4. import alias bare name
                if not callee_resolved and callee_raw in alias_map:
                    mapped = alias_map[callee_raw]
                    # mapped is like "pkg.mod.func"
                    bare = mapped.split(".")[-1]
                    cands = bare_index.get(bare, [])
                    if cands:
                        callee_resolved = cands[0]
                # 5. external check
                if not callee_resolved:
                    # check if stdlib/external
                    root_tok = callee_raw.split(".")[0].split("(")[0]
                    if root_tok in stdlib_externals or root_tok in alias_map and alias_map[root_tok] in stdlib_externals or callee_name in stdlib_externals:
                        is_external = True
                        external_label = callee_raw
                    else:
                        # treat as external for now if not found
                        is_external = True
                        external_label = callee_raw
                        # but if we want to hide unresolved non-stdlib, we still mark external but query will hide unless show_externals
                        # keep is_external true
                # if resolved, not external
                if callee_resolved:
                    is_external = False
                    external_label = None

                cs = CallSite(
                    caller=fid,
                    callee_raw=callee_raw,
                    callee_name=callee_name,
                    callee_resolved=callee_resolved,
                    is_external=is_external,
                    external_label=external_label,
                    lineno=lineno,
                    col=col,
                    call_args=call_args,
                    arg_sources=arg_sources,
                    assign_target=assign_target,
                    is_await=is_await,
                    is_chained=is_chained,
                )
                graph.edges.append(cs)
    graph.rebuild_indices()
    # warnings
    if len(graph.nodes) == 0:
        graph.warnings.append("No functions found — empty or no Python defs")
    return graph
