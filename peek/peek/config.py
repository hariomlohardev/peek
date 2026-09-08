"""Config — load ~/.peek/config.toml or XDG."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def config_path() -> Path:
    if p := os.environ.get("PEEK_CONFIG"):
        return Path(p)
    if xdg := os.environ.get("XDG_CONFIG_HOME"):
        return Path(xdg) / "peek" / "config.toml"
    p2 = Path.home() / ".config" / "peek" / "config.toml"
    if p2.exists():
        return p2
    return Path.home() / ".peek" / "config.toml"


def load_config() -> dict[str, Any]:
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


def save_config(data: dict[str, Any]) -> Path:
    p = config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for k, v in data.items():
        if isinstance(v, str):
            lines.append(f'{k} = "{v}"')
        else:
            lines.append(f'{k} = {v}')
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


#: The scaffold written by ``peek config init``.
#:
#: Every key is commented out except ``theme``, so the file documents what can
#: be set without changing any behaviour by existing. A scaffold that silently
#: pins a value is worse than none: the next release's better default would be
#: overridden by a file the user never edited.
DEFAULT_CONFIG_TEMPLATE = """\
# peek configuration.
#
# Written by `peek config init`. Every setting here is optional -- delete this
# file and peek behaves exactly as it does without it.
#
# Precedence, highest first:
#   1. the command-line flag  (--theme dracula)
#   2. the PEEK_THEME environment variable
#   3. this file
#   4. peek's built-in default

# Colour theme. See `peek --theme-list` for the full set.
theme = "anthropic-pro"

# Stop scanning after this many files. Raise it for a large monorepo.
# max_files = 5000

# Token budget for `peek --pack`.
# budget = 8000

# Pack output format: md, xml or txt.
# format = "md"
"""


class ConfigExistsError(Exception):
    """Raised when ``init_config`` would overwrite an existing file."""

    def __init__(self, path: Path) -> None:
        super().__init__(
            f"{path} already exists. Re-run with --force to overwrite it, "
            f"or edit it directly."
        )
        self.path = path


def init_config(force: bool = False) -> Path:
    """Write a commented config scaffold, and return where it went.

    Refuses to overwrite by default. The file is the only record of settings a
    user has hand-tuned, and `init` is the kind of command people re-run to
    remind themselves it exists -- so silently replacing it would be a way to
    lose work by typing something that sounds read-only.
    """
    p = config_path()
    if p.exists() and not force:
        raise ConfigExistsError(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(DEFAULT_CONFIG_TEMPLATE, encoding="utf-8")
    return p


def set_config_value(key: str, value: str) -> Path:
    if key == "theme":
        from peek.themes import get_theme
        get_theme(value)  # validates, raises ValueError if unknown
    data = load_config()
    data[key] = value
    return save_config(data)
