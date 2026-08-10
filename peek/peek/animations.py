"""Animations — themed for peek

Wraps Rich spinner with theme accent.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text

# Keep ANTHRO for backward compat
ANTHRO = {
    "bg": "#141413",
    "bg2": "#1C1C19",
    "surface": "#232320",
    "panel": "#2A2A27",
    "line": "#3A3936",
    "line2": "#4A4946",
    "ink": "#E8E6E3",
    "ink2": "#D4D0C8",
    "muted": "#9A9590",
    "muted2": "#6B6661",
    "accent": "#D4A27F",
    "accent2": "#C4896A",
    "signal": "#D4A27F",
    "cyan": "#8AB4B8",
    "violet": "#9A8FBF",
    "green": "#8BA888",
}


def _tok(theme: Any | None) -> dict[str, str]:
    if theme is None:
        return ANTHRO
    if hasattr(theme, "tokens"):
        return theme.tokens  # type: ignore[return-value]
    if isinstance(theme, dict):
        return theme
    return ANTHRO


def anthropic_header(root: Path, elapsed: float, version: str = "0.1.0", theme: Any | None = None) -> Panel:
    t = _tok(theme)
    txt = Text()
    txt.append("peek", style=f"bold {t['ink']}")
    txt.append(f"  v{version}", style=f"dim {t['muted']}")
    txt.append(f"  —  {root}", style=t["accent"])
    txt.append(f"  {elapsed:.2f}s", style=f"dim {t['muted']}")
    return Panel(
        txt,
        box=None,
        style=f"on {t['bg2']}",
        padding=(0, 1),
        border_style=t["line"],
    )


def scan_progress(console: Console, label: str = "Scanning", theme: Any | None = None):
    t = _tok(theme)
    return Progress(
        SpinnerColumn(style=t["accent"], spinner="dots"),
        TextColumn(f"[bold {t['ink']}]{label}[/]"),
        TextColumn(f"[dim {t['muted']}]{{task.fields[detail]}}[/]"),
        console=console,
        transient=True,
    )
