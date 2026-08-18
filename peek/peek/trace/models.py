"""Models for Python-only trace graph."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, order=True)
class FuncId:
    """Unique identifier for a function: file + qualified name.

    qualname is Python qualified name like "foo", "MyClass.method", "outer.inner".
    file is absolute Path (resolved) — matches scanner FileInfo.path.
    """

    file: Path
    qualname: str

    def __str__(self) -> str:
        try:
            return f"{self.file.name}::{self.qualname}"
        except Exception:
            return self.qualname


@dataclass
class Param:
    name: str
    kind: str  # posonly, arg, vararg, kwonly, kwarg
    annotation: str | None = None
    default: str | None = None

    def format(self) -> str:
        base = self.name
        if self.kind == "vararg":
            base = f"*{base}"
        elif self.kind == "kwarg":
            base = f"**{base}"
        if self.annotation:
            base += f": {self.annotation}"
        if self.default:
            base += f" = {self.default}"
        return base


@dataclass
class FuncNode:
    """Function/method node in the trace graph (Python only)."""

    id: FuncId
    name: str
    qualname: str
    file: Path
    rel: Path
    lineno: int
    end_lineno: int
    col: int
    kind: str  # def, async, method
    params: list[Param] = field(default_factory=list)
    returns: str | None = None
    docstring: str = ""
    decorators: list[str] = field(default_factory=list)
    is_method: bool = False
    class_name: str | None = None

    def signature(self) -> str:
        params_str = ", ".join(p.format() for p in self.params)
        sig = f"{self.name}({params_str})"
        if self.returns:
            sig += f" -> {self.returns}"
        return sig

    def qualified_signature(self) -> str:
        params_str = ", ".join(p.format() for p in self.params)
        sig = f"{self.qualname}({params_str})"
        if self.returns:
            sig += f" -> {self.returns}"
        return sig


@dataclass
class CallSite:
    """Call edge from caller to callee (raw + resolved)."""

    caller: FuncId
    callee_raw: str
    callee_name: str
    callee_resolved: FuncId | None
    is_external: bool
    external_label: str | None
    lineno: int
    col: int
    call_args: list[str]
    arg_sources: list[str]
    assign_target: str | None
    is_await: bool = False
    is_chained: bool = False


@dataclass
class TraceGraph:
    """Container for function-level graph (Python only)."""

    root: Path
    nodes: dict[FuncId, FuncNode] = field(default_factory=dict)
    edges: list[CallSite] = field(default_factory=list)
    edges_by_caller: dict[FuncId, list[CallSite]] = field(default_factory=dict)
    edges_by_callee: dict[FuncId, list[CallSite]] = field(default_factory=dict)
    file_groups: dict[Path, list[FuncId]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def rebuild_indices(self) -> None:
        self.edges_by_caller = {}
        self.edges_by_callee = {}
        self.file_groups = {}
        for e in self.edges:
            self.edges_by_caller.setdefault(e.caller, []).append(e)
            if e.callee_resolved:
                self.edges_by_callee.setdefault(e.callee_resolved, []).append(e)
        for fid, node in self.nodes.items():
            self.file_groups.setdefault(node.file, []).append(fid)
