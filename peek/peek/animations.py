"""Animations — best possible terminal design for peek.

Provides helpers for animated scanning, typing, bars, and TUI transitions.
Used by CLI (scan spinner), renderer (live bars), and TUI (stagger + pulse).

Design: "Cinematic Terminal" — dark, neon signal, grain, motion.
No external deps beyond Rich/Textual.
"""

from __future__ import annotations

import asyncio
import random
import time
from pathlib import Path

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.text import Text


# ---------------------------------------------------------------------------
# Tokens — Cinematic
# ---------------------------------------------------------------------------

CINE = {
    "bg": "#070A14",
    "bg2": "#0F1426",
    "surface": "#12182E",
    "panel": "#1A2142",
    "line": "#2A3A6B",
    "ink": "#E6E8F0",
    "muted": "#7A86B6",
    "signal": "#FFE600",
    "signal2": "#FF3B30",
    "cyan": "#00E5FF",
    "violet": "#B46EFF",
    "green": "#00E676",
    "grid": "rgba(42,58,107,0.35)",
}

GRADIENTS = [
    ("#FFE600", "#FF3B30"),
    ("#00E5FF", "#B46EFF"),
    ("#00E676", "#FFE600"),
]


def cinematic_header(root: Path, elapsed: float, version: str = "0.1.0") -> Panel:
    """Header with gradient peek + subtle grain."""
    t = Text()
    t.append("▮ ", style=f"bold {CINE['signal']}")
    # gradient peek
    for i, ch in enumerate("peek"):
        # cycle through gradient
        c = GRADIENTS[i % len(GRADIENTS)][0]
        t.append(ch, style=f"bold {c}")
    t.append(f"  v{version}", style=f"dim {CINE['muted']}")
    t.append(f"  —  {root}", style=CINE["cyan"])
    t.append(f"  {elapsed:.2f}s", style=f"dim {CINE['muted']}")
    # subtle tagline
    t.append("  ·  htop for codebases", style=f"italic dim {CINE['muted']}")
    return Panel(
        t,
        box=None,
        style=f"on {CINE['bg2']}",
        padding=(0, 1),
        border_style=CINE["line"],
    )


def animated_scan_progress(console: Console, task: str = "Scanning"):
    """Context manager for animated scan — spinner + bar."""
    progress = Progress(
        SpinnerColumn(style=CINE["signal"]),
        TextColumn(f"[bold {CINE['ink']}]{task}[/]"),
        BarColumn(bar_width=None, style=CINE["line"], complete_style=CINE["signal"]),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn(f"[{CINE['muted']} ]{{task.fields[extra]}}[/]"),
        console=console,
        transient=True,
    )
    return progress


def typewriter(text: str, delay: float = 0.015) -> Text:
    """Return Text that can be typed — for demo, not used in TUI directly."""
    # Rich Text with per-char style — used for static typing effect
    t = Text()
    for ch in text:
        t.append(ch, style=CINE["ink"])
    return t


def glitch_text(text: str, intensity: float = 0.08) -> Text:
    """Slight glitch — random char flicker for signal."""
    t = Text()
    for ch in text:
        if random.random() < intensity and ch not in (" ", "\n"):
            # glitch char
            glitch = random.choice(["█", "▓", "▒", "░", "·"])
            t.append(glitch, style=CINE["signal"])
        else:
            t.append(ch, style=CINE["ink"])
    return t


async def stagger_mount(widgets, delay: float = 0.06):
    """Helper for TUI — mount widgets with stagger (used in app)."""
    for w in widgets:
        yield w
        await asyncio.sleep(delay)


def bar_grow_animator(console: Console, label: str, pct: float, width: int = 16):
    """Build a bar that can be animated from 0 to pct."""
    # For Rich Live, we can update bar over frames
    filled = int(width * pct / 100)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{CINE['signal']}]{bar}[/] [{CINE['muted']}]{pct:.0f}%[/]"
