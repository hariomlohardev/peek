"""Config — load ~/.peek/config.toml or XDG."""

from __future__ import annotations

import os
from pathlib import Path


def config_path() -> Path:
    if p := os.environ.get("PEEK_CONFIG"):
        return Path(p)
    if xdg := os.environ.get("XDG_CONFIG_HOME"):
        return Path(xdg) / "peek" / "config.toml"
    p2 = Path.home() / ".config" / "peek" / "config.toml"
    if p2.exists():
        return p2
    return Path.home() / ".peek" / "config.toml"


def load_config() -> dict:
    p = config_path()
    if not p.exists():
        return {}
    try:
        try:
            import tomllib  # Python 3.11+
        except ImportError:
            import tomli as tomllib  # type: ignore[import-not-found]
        with p.open("rb") as f:
            data = tomllib.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}
