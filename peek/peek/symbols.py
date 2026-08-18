"""Symbol index — extracts symbols (def/class/var/import) for all langs.

Polyglot fallback: for Python uses AST, for JS/TS uses regex (no hard deps).
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Symbol:
    name: str
    kind: str  # def, class, import, var
    file: Path
    rel: Path
    lineno: int
    docstring: str = ""


JS_IMPORT_RE = re.compile(r"""import\s+(?:.*?\s+from\s+)?['"]([^'"]+)['"]|require\(['"]([^'"]+)['"]\)""")
JS_EXPORT_RE = re.compile(r"""export\s+(?:default\s+)?(?:function|class|const|let|var)\s+(\w+)""")

# Rust -- leading [ \t]* rather than \s*, because \s matches newlines and the
# match would then start on a blank line above, reporting a lineno one or more
# lines early. Indentation is allowed on purpose: unlike Go, a Rust method lives
# inside an `impl` block and is indented, and anchoring hard to column 0 would
# miss most of the functions in a real crate. A commented-out `// fn foo()`
# still does not match, since `//` is not whitespace.
_RUST_VIS = r"(?:pub(?:\([^)]*\))?\s+)?"
RUST_FN_RE = re.compile(
    r"^[ \t]*" + _RUST_VIS + r"(?:default\s+)?(?:const\s+)?(?:async\s+)?(?:unsafe\s+)?"
    r'(?:extern\s+"[^"]*"\s+)?fn\s+([A-Za-z_]\w*)',
    re.MULTILINE,
)
RUST_TYPE_RE = re.compile(
    r"^[ \t]*" + _RUST_VIS + r"(?:struct|enum|trait|union)\s+([A-Za-z_]\w*)",
    re.MULTILINE,
)
RUST_MOD_RE = re.compile(r"^[ \t]*" + _RUST_VIS + r"mod\s+([A-Za-z_]\w*)", re.MULTILINE)


def index_symbols(scan_result) -> list[Symbol]:
    """Index symbols from ScanResult.

    Returns list[Symbol] with name, kind, file (abs), rel, lineno, docstring.
    Never raises — skips unreadable / unparsable files.
    """
    out: list[Symbol] = []
    for f in scan_result.files:
        try:
            # utf-8-sig to strip BOM if present (PowerShell)
            try:
                text = f.path.read_text(encoding="utf-8-sig", errors="ignore")
            except Exception:
                text = f.path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if not text.strip():
            continue
        if f.language == "python":
            try:
                # strip leading BOM if still present
                if text.startswith("﻿"):
                    text = text.lstrip("﻿")
                tree = ast.parse(text, filename=str(f.path))
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        out.append(
                            Symbol(
                                node.name,
                                "def",
                                f.path,
                                f.rel,
                                node.lineno,
                                ast.get_docstring(node) or "",
                            )
                        )
                    elif isinstance(node, ast.AsyncFunctionDef):
                        out.append(
                            Symbol(
                                node.name,
                                "def",
                                f.path,
                                f.rel,
                                node.lineno,
                                ast.get_docstring(node) or "",
                            )
                        )
                    elif isinstance(node, ast.ClassDef):
                        out.append(
                            Symbol(
                                node.name,
                                "class",
                                f.path,
                                f.rel,
                                node.lineno,
                                ast.get_docstring(node) or "",
                            )
                        )
            except Exception:
                pass
        elif f.language in ("javascript", "typescript"):
            try:
                import tree_sitter  # type: ignore  # noqa: F401

                raise ImportError  # fallback to regex per brief (no hard dep)
            except ImportError:
                for m in JS_EXPORT_RE.finditer(text):
                    lineno = text[: m.start()].count("\n") + 1
                    out.append(Symbol(m.group(1), "def", f.path, f.rel, lineno))
        elif f.language == "rust":
            # `mod` is recorded as "import": it names another unit of the crate,
            # which is the role `import` plays elsewhere here. Kept inside the
            # existing def/class/import/var vocabulary rather than inventing a
            # new kind that nothing downstream would know about.
            for regex, kind in (
                (RUST_FN_RE, "def"),
                (RUST_TYPE_RE, "class"),
                (RUST_MOD_RE, "import"),
            ):
                for m in regex.finditer(text):
                    lineno = text[: m.start()].count("\n") + 1
                    out.append(Symbol(m.group(1), kind, f.path, f.rel, lineno))
    return out
