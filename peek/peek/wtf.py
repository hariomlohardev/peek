from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class Frame:
    filename: str
    lineno: int
    func: str
    code: str = ""

@dataclass
class TracebackInfo:
    frames: list[Frame]
    exc_type: str
    exc_msg: str
    raw: str

_TB_RE = re.compile(r'File "([^"]+)", line (\d+), in (\S+)')
_EXC_RE = re.compile(r'^(\w+(?:\.\w+)*Error|\w+Exception|\w+Error):\s*(.*)$', re.M)

def parse_traceback(text: str) -> TracebackInfo | None:
    if "Traceback" not in text:
        return None
    frames = []
    for m in _TB_RE.finditer(text):
        fn, ln, func = m.groups()
        # next line after match is code
        after = text[m.end():].splitlines()
        code = after[1].strip() if len(after) > 1 else ""
        frames.append(Frame(fn, int(ln), func, code))
    if not frames:
        return None
    # last line that matches exc
    exc_type = exc_msg = ""
    for line in reversed(text.strip().splitlines()):
        mm = _EXC_RE.match(line.strip())
        if mm:
            exc_type, exc_msg = mm.groups()
            break
    if not exc_type:
        return None
    return TracebackInfo(frames, exc_type, exc_msg, text)

def find_relevant_files(info: TracebackInfo, scan_result) -> list[Path]:
    # map frame filename to scanned files by suffix match, shortest rel path wins
    out = []
    scanned = {f.rel.as_posix(): f.path for f in scan_result.files}
    for fr in info.frames:
        # try exact rel, else suffix
        cand = [p for rel,p in scanned.items() if rel.endswith(fr.filename) or fr.filename.endswith(rel)]
        if cand:
            out.append(cand[0])
    return out

def explain_tb(info: TracebackInfo, scan_result, analyzer_result) -> str:
    lines = [f"## {info.exc_type}: {info.exc_msg}", "", "Traceback (most relevant first):"]
    for fr in reversed(info.frames):
        lines.append(f"- `{fr.filename}:{fr.lineno}` in `{fr.func}`" + (f" — `{fr.code}`" if fr.code else ""))
    # heuristic: if file in Start Here ranked, add hint
    try:
        ranked = {r.rel.as_posix() for r in analyzer_result.ranked[:5]}
        hinted = [f for f in find_relevant_files(info, scan_result) if any(r.endswith(f.name) for r in ranked)]
        if hinted:
            lines.append(f"\n**Start Here:** {hinted[0]} is in ranked top 5 — check its callers in `peek analyze`.")
    except Exception:
        pass
    return "\n".join(lines)
