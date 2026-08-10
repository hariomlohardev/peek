# Assets

This folder holds demo media for `README` and launch.

## Files

- `demo.gif` — 15–20s terminal demo (800px wide, <3MB, no audio, autoplay, loop). Shows: `git clone requests` → `peek .` → TUI nav (`j/k`/`/`) → `peek --no-tui` → `peek find "auth"` → `peek --pack`.
  - Current file is a placeholder. Generate real GIF with one of:
    - **vhs** (charmbracelet/vhs): `vhs demo.tape` — see `demo.tape` below
    - **asciinema + agg**: `asciinema rec demo.cast --command "peek"` then `agg demo.cast demo.gif`
    - **Screen record + convert**: record 800x600, convert with `ffmpeg -i demo.mov -vf scale=800:-1 -r 10 demo.gif`
  - Keep GIF <3MB: `gifsicle -O3 --colors 128 demo.gif -o demo.gif` or `ffmpeg -i demo.mov -vf "fps=10,scale=800:-1:flags=lanczos" demo.gif`
  - Fallback static screenshot: `peek --no-tui > assets/demo.txt` or `peek --html -o assets/demo.html`

- `demo.html` — self-contained HTML export via `peek --html -o assets/demo.html` (Rich `export_html`). Good for sharing without terminal.

- `demo.tape` — `vhs` script (if you use vhs). Example:

```tape
Output demo.gif
Set Width 1200
Set Height 800
Set Theme "Catppuccin Mocha"
Set FontSize 14

Type "git clone https://github.com/psf/requests /tmp/requests" Enter
Sleep 1000ms
Type "peek /tmp/requests --no-tui" Enter
Sleep 2500ms
Type "peek /tmp/requests" Enter
Sleep 1500ms
Type "j" Sleep 300ms Type "j" Sleep 300ms Type "/" Type "auth" Enter Sleep 1000ms
Type "q"

```

Run: `vhs assets/demo.tape`

## Generating Now (Day 5)

If you have `peek` installed:

```bash
peek . --html -o assets/demo.html
peek . --no-tui > assets/static.txt
# then capture GIF via vhs/asciinema
```

Placeholder GIF is 1x1 transparent — replace before launch.
