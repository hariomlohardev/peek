"""Code-generated demo — Pillow GIF + SVG + HTML refresh.

Generates peek/assets/demo.gif (800x450, <3MB, ~15s) and demo.svg
without external vhs/ffmpeg. Themed via peek/themes.py.

Usage:
  python -m peek.tools.gen_demo              # writes gif + svg
  python -m peek.tools.gen_demo --help
  python peek/tools/gen_demo.py --out peek/assets/demo2.gif
"""

from __future__ import annotations

import argparse
import pathlib
import sys

# allow `python peek/tools/gen_demo.py` direct run
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

try:
    from peek import __version__
except Exception:
    __version__ = "0.2.0"

try:
    from peek.themes import get_theme, list_themes
except Exception:
    get_theme = list_themes = None  # type: ignore

from PIL import Image, ImageDraw, ImageFont  # type: ignore

W, H = 800, 450
FPS = 10
DURATION_MS = 90  # 90ms ≈ 11 fps, smooth but small

# Scenes — each is (title, command, body_lines, accent_override)
SCENES = [
    (
        "peek — htop for codebases",
        f"peek v{__version__}  •  anthropic-pro  •  10 themes",
        [
            "  pip install peek-code && peek .",
            "  ─────────────────────────",
            "  5 seconds → map any repo",
            "  where to start • what talks to what",
            "",
            "  ▶  peek --help  →  peek . --no-tui  →  peek find \"auth\"",
        ],
        None,
    ),
    (
        "peek --help",
        "$ peek --help",
        [
            "  Usage: peek [PATH] [OPTIONS] COMMAND",
            "  ",
            "  The htop for codebases — understand any repo in 5s.",
            "  ",
            "  Commands:  scan    scan + stats        wtf     traceback hint",
            "             analyze import graph+rank   watch   live rescan",
            "             find    keyword search      config  theme persist",
            "  Options:   --no-tui  static  •  --html -o out.html",
            "             --pack --ask QUERY --format md/xml/txt  •  --theme dracula",
            "             --theme-list  (10 themes)  •  t cycle • w watch",
        ],
        None,
    ),
    (
        "peek . --no-tui  (static Rich)",
        "$ peek . --no-tui",
        [
            "  peek  v0.2.0  —  ./peek  (0.12s)",
            "  ┌ Languages ──────────────────┐ ┌ Tech Stack ────────┐",
            "  │ Python  ██████████████  68%  │ │ Primary: python  │",
            "  │ Markdown ░░░░░░░░░░░░░   8%  │ │ Frameworks: textual, rich",
            "  └─────────────────────────────┘ └────────────────────┘",
            "  ┌ Start Here ⭐ (ranked) ─────────────────────────┐",
            "  │ 1  peek/peek/cli.py        9.2  entry • hub     │",
            "  │ 2  peek/peek/tui.py        8.7  hub • guard     │",
            "  └─────────────────────────────────────────────────┘",
        ],
        None,
    ),
    (
        'peek find "auth" .',
        '$ peek find "auth" .',
        [
            "  peek find  v0.2.0  —  query: \"auth\"  (0.04s)",
            "  ┌ Matches (4 files) ─────────────────────────────┐",
            "  │ 1  peek/peek/auth.py        8.4  filename     │",
            "  │ 2  peek/peek/middleware.py  3.1  content:42   │",
            "  │ 3  tests/test_auth.py       2.8  content:7    │",
            "  └────────────────────────────────────────────────┘",
            "  Preview: middleware.py:42  if not auth_ok: raise",
        ],
        None,
    ),
    (
        "peek --pack --ask auth | head",
        '$ peek --pack --ask "auth" --format md | head -20',
        [
            "  ── pack v2: 4 files • ~2.1k tokens • query=auth ──",
            "  ## peek/peek/auth.py  FILE: auth.py",
            "  ```python  def check(token): ... ```",
            "  ## peek/peek/middleware.py  FILE: middleware.py",
            "  ```python  from .auth import check ```",
            "  # peek/peek/middleware.py",
            "  ── --format md/xml/txt --budget 8000 --include \"*.py\" ──",
            "  ── pbcopy / LLM ready ──",
        ],
        None,
    ),
    (
        "peek wtf — traceback explainer",
        "$ cat tb.txt | peek wtf",
        [
            "  Traceback (most recent call last):",
            "    File \"peek/peek/cli.py\", line 42, in main",
            "    File \"peek/peek/tui.py\", line 128, in _tick",
            "  ValueError: Unknown theme 'baguette'",
            "  ── peek wtf hint ──",
            "  → Start Here: peek/peek/themes.py is ranked #3",
            "  → check its callers in `peek analyze`",
            "  No LLM needed • parses Traceback + Error + frames",
        ],
        None,
    ),
    (
        "peek watch . — live rescan",
        "$ peek watch .",
        [
            "  Watching  polling 0.8s • debounce 0.4s  (Ctrl+C quit)",
            "  Updated (3 files changed)  0.04s  •  re-rendered static",
            "  ── peek --watch → TUI • w toggle watch ON/OFF ──",
            "  uses watchfiles if installed, else polling fallback",
            "  Live rescan • re-renders static panels",
            "  $ peek --watch   # TUI watch + t cycle theme",
        ],
        None,
    ),
    (
        "10 themes  •  peek --theme-list  •  t live",
        "$ peek --theme-list",
        [
            "  ■ anthropic-pro  Warm editorial      #D4A27F → #141413",
            "  ■ dracula        Purple haze         #BD93F9 → #282A36",
            "  ■ nord           Arctic              #88C0D0 → #2E3440",
            "  ■ tokyo-night    Electric storm      #7AA2F7 → #1A1B26",
            "  »  PEEK_THEME=dracula peek  •  --theme nord --no-tui",
            "  t → cycle themes live in TUI • w → toggle watch",
        ],
        None,
    ),
]


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    # Prefer Consolas on Windows, else default
    candidates = [
        r"C:\Windows\Fonts\consola.ttf",
        r"C:\Windows\Fonts\consolab.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/System/Library/Fonts/Courier.dfont",
    ]
    for p in candidates:
        try:
            if pathlib.Path(p).exists():
                return ImageFont.truetype(p, size)
        except Exception:
            continue
    # Pillow default (Aileron) — works everywhere
    try:
        return ImageFont.load_default(size=size)  # type: ignore
    except TypeError:
        return ImageFont.load_default()


def _colors(theme_id: str = "anthropic-pro"):
    if get_theme:
        try:
            th = get_theme(theme_id)
            t = th.tokens
            return {
                "bg": t["bg"],
                "bg2": t["bg2"],
                "panel": t["panel"],
                "line": t["line"],
                "ink": t["ink"],
                "muted": t["muted"],
                "accent": t["accent"],
                "accent2": t["accent2"],
            }
        except Exception:
            pass
    return {
        "bg": "#141413",
        "bg2": "#1C1C19",
        "panel": "#2A2A27",
        "line": "#3A3936",
        "ink": "#E8E6E3",
        "muted": "#9A9590",
        "accent": "#D4A27F",
        "accent2": "#C4896A",
    }


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def _render_frame(
    scene_idx: int,
    typed_len: int,
    pulse_phase: int,
    draw_font: ImageFont.ImageFont,
    small_font: ImageFont.ImageFont,
    title_font: ImageFont.ImageFont,
    colors: dict,
) -> Image.Image:
    title, cmd, body, _ = SCENES[scene_idx]
    bg, bg2, panel, line, ink, muted, accent = (
        _hex(colors["bg"]),
        _hex(colors["bg2"]),
        _hex(colors["panel"]),
        _hex(colors["line"]),
        _hex(colors["ink"]),
        _hex(colors["muted"]),
        _hex(colors["accent"]),
    )

    im = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(im)

    # top bar — title + pulse
    pulses = ["◐", "◑", "◒", "◓"]
    pulse_char = pulses[pulse_phase % 4]
    # bar background
    d.rectangle([(0, 0), (W, 28)], fill=bg2)
    d.rectangle([(0, 28), (W, 29)], fill=line)
    # left pulse
    d.text((10, 6), f"{pulse_char}", font=small_font, fill=accent)
    d.text((26, 6), title, font=small_font, fill=ink)
    # right — scene indicator + version
    indicator = f"{scene_idx + 1}/{len(SCENES)}  v{__version__}"
    # right-align approx
    try:
        bbox = d.textbbox((0, 0), indicator, font=small_font)
        tw = bbox[2] - bbox[0]
    except Exception:
        tw = len(indicator) * 7
    d.text((W - tw - 10, 6), indicator, font=small_font, fill=muted)

    # command line with typewriter + cursor
    cmd_typed = cmd[:typed_len]
    cursor = "▌" if (pulse_phase % 3 != 2) else ""
    cmd_line = cmd_typed + cursor
    # command bg panel
    d.rounded_rectangle([(12, 36), (W - 12, 58)], radius=6, fill=panel, outline=line)
    d.text((18, 40), cmd_line, font=draw_font, fill=accent)

    # body panel
    d.rounded_rectangle([(12, 64), (W - 12, H - 36)], radius=8, fill=panel, outline=line)
    y = 72
    for line_text in body:
        # accent for lines starting with ▶ or ■ or │
        fill = muted if line_text.strip().startswith(("┌", "└", "│", "─")) else ink
        if "⭐" in line_text or "▶" in line_text:
            fill = ink
        if line_text.strip().startswith(("1 ", "2 ", "3 ")) or "peek" in line_text.lower() and "v0" in line_text:
            fill = ink
        d.text((18, y), line_text, font=draw_font, fill=fill)
        y += 15
        if y > H - 42:
            break

    # footer
    d.rectangle([(0, H - 28), (W, H)], fill=bg2)
    d.rectangle([(0, H - 28), (W, H - 27)], fill=line)
    footer = "q quit  •  / filter  •  --theme dracula  •  --no-tui  •  --html"
    d.text((10, H - 20), footer, font=small_font, fill=muted)
    # themed dot on footer right
    d.ellipse([(W - 18, H - 19), (W - 8, H - 9)], fill=accent)

    return im


def generate_gif(out: pathlib.Path, theme: str = "anthropic-pro") -> pathlib.Path:
    colors = _colors(theme)
    font = _load_font(13)
    small = _load_font(11)
    title_font = _load_font(13)

    frames: list[Image.Image] = []
    pulse = 0
    for idx, (title, cmd, body, _accent) in enumerate(SCENES):
        # typewriter frames for command
        cmd_len = len(cmd)
        type_frames = min(cmd_len, 14)  # cap typing steps
        # hold frames per scene — stagger so total ~15s at 90ms
        hold = 18 if idx in (0, 5) else 12
        # typing phase
        for step in range(type_frames + 1):
            typed = int(cmd_len * (step / max(1, type_frames)))
            im = _render_frame(idx, typed, pulse, font, small, title_font, colors)
            frames.append(im)
            pulse += 1
        # hold phase (full command)
        for _ in range(hold):
            im = _render_frame(idx, cmd_len, pulse, font, small, title_font, colors)
            frames.append(im)
            pulse += 1

    # Ensure output dir
    out.parent.mkdir(parents=True, exist_ok=True)

    # Optimize palette — quantize to keep <3MB
    # Convert via adaptive palette on first frame
    # Use PIL's optimize GIF save
    first, *rest = frames
    # Quantize frames to P mode with same palette to reduce size
    # Use median cut, 128 colors
    quantized: list[Image.Image] = []
    for im in frames:
        q = im.quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        quantized.append(q)
    q_first, *q_rest = quantized
    q_first.save(
        out,
        save_all=True,
        append_images=q_rest,
        duration=DURATION_MS,
        loop=0,
        optimize=True,
    )
    return out


def generate_svg(out: pathlib.Path, theme: str = "anthropic-pro") -> pathlib.Path:
    colors = _colors(theme)
    # Simple SMIL-animated SVG — cycles through scene titles every 2.2s
    out.parent.mkdir(parents=True, exist_ok=True)
    # Build animated text nodes
    dur = len(SCENES) * 2.2
    # SVG with dark bg, rounded panels, accent footer dot
    scenes_svg = ""
    for i, (title, cmd, body, _a) in enumerate(SCENES):
        begin = i * 2.2
        # Escape XML
        def esc(s: str) -> str:
            return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        body_tspans = "".join(
            f'<tspan x="18" dy="15">{esc(l)}</tspan>' for l in body[:7]
        )
        scenes_svg += f"""
  <g opacity="0">
    <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.08;0.92;1" dur="2.2s" begin="{begin}s" repeatCount="indefinite" />
    <text x="26" y="20" font-family="monospace" font-size="11" fill="{colors['ink']}">{esc(title)}</text>
    <rect x="12" y="36" width="776" height="22" rx="6" fill="{colors['panel']}" stroke="{colors['line']}"/>
    <text x="18" y="52" font-family="monospace" font-size="12" fill="{colors['accent']}">{esc(cmd)}</text>
    <rect x="12" y="64" width="776" height="350" rx="8" fill="{colors['panel']}" stroke="{colors['line']}"/>
    <text x="18" y="80" font-family="monospace" font-size="11" fill="{colors['ink']}">{body_tspans}</text>
  </g>"""

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img">
  <title>peek — htop for codebases demo</title>
  <rect width="{W}" height="{H}" rx="10" fill="{colors['bg']}"/>
  <rect x="0" y="0" width="{W}" height="28" fill="{colors['bg2']}"/>
  <rect x="0" y="{H-28}" width="{W}" height="28" fill="{colors['bg2']}"/>
  <circle cx="{W-13}" cy="{H-14}" r="5" fill="{colors['accent']}"/>
  <text x="10" y="{H-12}" font-family="monospace" font-size="10" fill="{colors['muted']}">q quit  •  / filter  •  --theme dracula  •  --no-tui  •  --html</text>
  {scenes_svg}
  <rect width="{W}" height="{H}" rx="10" fill="none" stroke="{colors['line']}" stroke-opacity="0.6"/>
</svg>
"""
    out.write_text(svg, encoding="utf-8")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate peek demo GIF/SVG by code (no vhs)")
    ap.add_argument("--theme", default="anthropic-pro", help="Theme id (default: anthropic-pro)")
    ap.add_argument("--out", type=pathlib.Path, default=pathlib.Path("peek/assets/demo.gif"), help="GIF output")
    ap.add_argument("--svg-out", type=pathlib.Path, default=pathlib.Path("peek/assets/demo.svg"), help="SVG output")
    args = ap.parse_args()

    # Validate theme early
    if get_theme:
        try:
            get_theme(args.theme)
        except ValueError as e:
            print(f"Unknown theme: {e}", file=sys.stderr)
            sys.exit(2)

    gif_path = generate_gif(args.out, theme=args.theme)
    svg_path = generate_svg(args.svg_out, theme=args.theme)
    print(f"GIF -> {gif_path}  ({gif_path.stat().st_size} bytes, {W}x{H}, ~{len(SCENES)} scenes)")
    print(f"SVG -> {svg_path}  ({svg_path.stat().st_size} bytes)")
    # Size guard
    if gif_path.stat().st_size > 3_000_000:
        print(f"WARN: GIF >3MB ({gif_path.stat().st_size}) -- consider fewer frames or colors", file=sys.stderr)


if __name__ == "__main__":
    main()
