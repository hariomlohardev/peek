# peek â€” htop for codebases

> Understand any codebase in 5 seconds. `pip install peek && peek .`

<p align="center">
  <em>Beautiful, zero-config codebase cartographer â€” Python-native, Rich + Textual, works offline.</em>
</p>

**Day 1 status:** Scanner live â€” `peek scan .` works. Days 2-5 in progress.

## Install (Day 5)

```bash
pip install peek
# or
pipx install peek
uv tool install peek
```

## Usage (Day 1)

```bash
peek scan .              # scan repo, show file stats + tech stack + entry points
peek scan /path/to/repo  # scan any repo
peek --help
```

## What it will do (by Day 5)

```bash
peek .                  # interactive TUI
peek . --no-tui         # static output (for screenshots/CI)
peek . --html -o map.html
peek --find "auth" .
peek . --pack           # ranked files for LLM
```

## Portfolio

Built by [Hariom Lohar](https://hariomlohardev.github.io/) — hariomlohar.new@gmail.com

## License

MIT
