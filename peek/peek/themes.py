"""Themes — central registry for peek 10-theme system.

One file owns all colors. Every theme has exactly 15 tokens.
Usage: from peek.themes import get_theme, list_themes, resolve_theme
"""

from __future__ import annotations

import os
from dataclasses import dataclass

_KEYS = [
    "bg",
    "bg2",
    "surface",
    "panel",
    "line",
    "line2",
    "ink",
    "ink2",
    "muted",
    "muted2",
    "accent",
    "accent2",
    "cyan",
    "violet",
    "green",
]


@dataclass(frozen=True)
class Theme:
    id: str
    label: str
    description: str
    tokens: dict[str, str]
    preview: str = "■"


THEMES: dict[str, Theme] = {
    "anthropic-pro": Theme(
        id="anthropic-pro",
        label="Anthropic Pro",
        description="Warm editorial, clay on charcoal",
        preview="■",
        tokens={
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
            "cyan": "#8AB4B8",
            "violet": "#9A8FBF",
            "green": "#8BA888",
        },
    ),
    "catppuccin-mocha": Theme(
        id="catppuccin-mocha",
        label="Catppuccin Mocha",
        description="Pastel mauve, cozy",
        preview="■",
        tokens={
            "bg": "#1E1E2E",
            "bg2": "#181825",
            "surface": "#313244",
            "panel": "#45475A",
            "line": "#585B70",
            "line2": "#45475A",
            "ink": "#CDD6F4",
            "ink2": "#BAC2DE",
            "muted": "#6C7086",
            "muted2": "#585B70",
            "accent": "#CBA6F7",
            "accent2": "#F5C2E7",
            "cyan": "#89B4FA",
            "violet": "#CBA6F7",
            "green": "#A6E3A1",
        },
    ),
    "cinematic": Theme(
        id="cinematic",
        label="Cinematic",
        description="Neon viral, signal yellow on midnight",
        preview="■",
        tokens={
            "bg": "#070A14",
            "bg2": "#0F1320",
            "surface": "#141A2E",
            "panel": "#1A2140",
            "line": "#2A3358",
            "line2": "#3A4568",
            "ink": "#E8E6E3",
            "ink2": "#D4D0C8",
            "muted": "#8B8FA3",
            "muted2": "#6B7280",
            "accent": "#FFE600",
            "accent2": "#FFD000",
            "cyan": "#00D4FF",
            "violet": "#9A8FBF",
            "green": "#00FF88",
        },
    ),
    "dracula": Theme(
        id="dracula",
        label="Dracula",
        description="Purple haze, soft pink",
        preview="■",
        tokens={
            "bg": "#282A36",
            "bg2": "#1E1F2E",
            "surface": "#343746",
            "panel": "#44475A",
            "line": "#6272A4",
            "line2": "#44475A",
            "ink": "#F8F8F2",
            "ink2": "#E6E6E6",
            "muted": "#6272A4",
            "muted2": "#44475A",
            "accent": "#BD93F9",
            "accent2": "#FF79C6",
            "cyan": "#8BE9FD",
            "violet": "#BD93F9",
            "green": "#50FA7B",
        },
    ),
    "github-dark": Theme(
        id="github-dark",
        label="GitHub Dark",
        description="GitHub dark, familiar",
        preview="■",
        tokens={
            "bg": "#0D1117",
            "bg2": "#010409",
            "surface": "#161B22",
            "panel": "#21262D",
            "line": "#30363D",
            "line2": "#21262D",
            "ink": "#E6EDF3",
            "ink2": "#C9D1D9",
            "muted": "#8B949E",
            "muted2": "#6E7681",
            "accent": "#58A6FF",
            "accent2": "#A371F7",
            "cyan": "#58A6FF",
            "violet": "#A371F7",
            "green": "#3FB950",
        },
    ),
    "minimal-mono": Theme(
        id="minimal-mono",
        label="Minimal Mono",
        description="Black & white, a11y",
        preview="■",
        tokens={
            "bg": "#111111",
            "bg2": "#0A0A0A",
            "surface": "#1A1A1A",
            "panel": "#262626",
            "line": "#333333",
            "line2": "#262626",
            "ink": "#E5E5E5",
            "ink2": "#CCCCCC",
            "muted": "#8A8A8A",
            "muted2": "#6A6A6A",
            "accent": "#E5E5E5",
            "accent2": "#FFFFFF",
            "cyan": "#CCCCCC",
            "violet": "#AAAAAA",
            "green": "#E5E5E5",
        },
    ),
    "monokai": Theme(
        id="monokai",
        label="Monokai",
        description="Hot pink/green, contrast",
        preview="■",
        tokens={
            "bg": "#272822",
            "bg2": "#1E1F1C",
            "surface": "#3E3D32",
            "panel": "#49483E",
            "line": "#75715E",
            "line2": "#49483E",
            "ink": "#F8F8F2",
            "ink2": "#E8E8E2",
            "muted": "#75715E",
            "muted2": "#49483E",
            "accent": "#F92672",
            "accent2": "#A6E22E",
            "cyan": "#66D9EF",
            "violet": "#AE81FF",
            "green": "#A6E22E",
        },
    ),
    "nord": Theme(
        id="nord",
        label="Nord",
        description="Frosty arctic, muted blues",
        preview="■",
        tokens={
            "bg": "#2E3440",
            "bg2": "#3B4252",
            "surface": "#434C5E",
            "panel": "#4C566A",
            "line": "#4C566A",
            "line2": "#3B4252",
            "ink": "#ECEFF4",
            "ink2": "#E5E9F0",
            "muted": "#4C566A",
            "muted2": "#3B4252",
            "accent": "#88C0D0",
            "accent2": "#81A1C1",
            "cyan": "#88C0D0",
            "violet": "#B48EAD",
            "green": "#A3BE8C",
        },
    ),
    "solarized-dark": Theme(
        id="solarized-dark",
        label="Solarized Dark",
        description="Teal, classic",
        preview="■",
        tokens={
            "bg": "#002B36",
            "bg2": "#073642",
            "surface": "#0A3B4A",
            "panel": "#184956",
            "line": "#586E75",
            "line2": "#0A3B4A",
            "ink": "#EEE8D5",
            "ink2": "#FDF6E3",
            "muted": "#586E75",
            "muted2": "#657B83",
            "accent": "#268BD2",
            "accent2": "#2AA198",
            "cyan": "#2AA198",
            "violet": "#6C71C4",
            "green": "#859900",
        },
    ),
    "tokyo-night": Theme(
        id="tokyo-night",
        label="Tokyo Night",
        description="Electric blue, storm",
        preview="■",
        tokens={
            "bg": "#1A1B26",
            "bg2": "#16161E",
            "surface": "#24283B",
            "panel": "#414868",
            "line": "#414868",
            "line2": "#24283B",
            "ink": "#C0CAF5",
            "ink2": "#A9B1D6",
            "muted": "#565F89",
            "muted2": "#414868",
            "accent": "#7AA2F7",
            "accent2": "#BB9AF7",
            "cyan": "#7DCFFF",
            "violet": "#BB9AF7",
            "green": "#9ECE6A",
        },
    ),
}


def get_theme(name: str | None) -> Theme:
    """Case-insensitive lookup. Falls back to anthropic-pro if None/empty. Raises ValueError if unknown."""
    if not name or not name.strip():
        return THEMES["anthropic-pro"]
    key = name.strip().lower()
    # normalize underscores to dashes
    key = key.replace("_", "-")
    if key in THEMES:
        return THEMES[key]
    raise ValueError(f"Unknown theme '{name}'. Available: {', '.join(sorted(THEMES))}")


def list_themes() -> list[Theme]:
    """Every registered theme, ordered by id, case-insensitively.

    Plain ``sorted()`` orders by codepoint, which puts every capitalised id
    ahead of every lowercase one -- a theme registered as ``"Solarized-Light"``
    would jump to the top of ``peek --theme-list`` rather than sit next to
    ``solarized-dark``. Every id in ``THEMES`` is lowercase today, so this
    changes nothing now and keeps the order sensible when one is not.

    The raw id breaks ties, so ids differing only in case have a stable order
    rather than one decided by dict insertion.
    """
    return [THEMES[k] for k in sorted(THEMES, key=lambda k: (k.lower(), k))]


def resolve_theme(cli_opt: str | None) -> Theme:
    """Precedence: cli > PEEK_THEME env > config file > anthropic-pro.

    Fix #80: do not cache — PEEK_THEME env and --theme must be re-evaluated
    on every call. A previous lru_cache on this function cached the first
    result (often anthropic-pro #141413) and returned it for later dracula
    requests, causing Windows `peek --theme dracula --html` to embed the wrong bg.
    """
    if cli_opt:
        return get_theme(cli_opt)
    env = os.environ.get("PEEK_THEME")
    if env and env.strip():
        try:
            return get_theme(env)
        except ValueError:
            # env invalid → fall through to config then default, but also let caller know via error?
            # For now, treat as error to be visible — caller will handle ValueError
            raise
    try:
        from peek.config import load_config

        cfg = load_config()
        if isinstance(cfg, dict) and cfg.get("theme"):
            return get_theme(str(cfg["theme"]))
    except Exception:
        pass
    return THEMES["anthropic-pro"]


# Validation at import — fail fast if theme shape broken
for _th in THEMES.values():
    if set(_th.tokens) != set(_KEYS):
        raise ValueError(f"Theme {_th.id} missing keys: expected {_KEYS}, got {sorted(_th.tokens)}")
    for _k, _v in _th.tokens.items():
        if not isinstance(_v, str) or not _v.startswith("#") or len(_v) != 7:
            raise ValueError(f"Theme {_th.id} bad color {_k}={_v}")
