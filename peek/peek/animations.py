"""Animations — Anthropic Pro for peek

Professional, warm, subtle. Not flashy — feels like Claude Code.
Tokens match Anthropic's design: warm ink on charcoal, clay accent, muted.
Animations are 120–220ms, ease-out, staggered — professional, not viral-neon.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.text import Text

# Anthropic Pro tokens — warm, editorial, terminal-native
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
    "accent": "#D4A27F",  # clay
    "accent2": "#E07A5F",  # terracotta
    "signal": "#D4A27F",
    "cyan": "#8AB4B8",
    "violet": "#9A8FBF",
    "green": "#8BA888",
}

def anthropic_header(root: Path, elapsed: float, version: str = "0.1.0") -> Panel:
    t = Text()
    t.append("peek", style=f"bold {ANTHRO['ink']}")
    t.append(f"  v{version}", style=f"dim {ANTHRO['muted']}")
    t.append(f"  —  {root}", style=ANTHRO["accent"])
    t.append(f"  {elapsed:.2f}s", style=f"dim {ANTHRO['muted']}")
    return Panel(
        t,
        box=None,
        style=f"on {ANTHRO['bg2']}",
        padding=(0, 1),
        border_style=ANTHRO["line"],
    )

def scan_progress(console: Console, label: str = "Scanning"):
    return Progress(
        SpinnerColumn(style=ANTHRO["accent"], spinner="dots"),
        TextColumn(f"[bold {ANTHRO['ink']}]{label}[/]"),
        TextColumn(f"[dim {ANTHRO['muted']}]{{task.fields[detail]}}[/]"),
        console=console,
        transient=True,
    )
