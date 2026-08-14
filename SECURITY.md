# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.3.x   | :white_check_mark: |
| 0.2.x   | :white_check_mark: |
| < 0.2   | :x: |

## Reporting a Vulnerability

**Do not** open a public issue for security bugs.

Email **hariomlohar.new@gmail.com** with:
- `peek --version` + `peek scan --json` (redact sensitive paths)
- OS, Python version, terminal
- Repro steps or PoC (no exploit needed)

We’ll acknowledge within 48h, fix within 7 days, and credit you in `CHANGELOG.md` (unless you prefer anonymous).

## Scope

`peek` never sends code off-device (offline, no API key). `peek mcp` and `peek --share` are the only network paths — report any exfiltration there.

Thanks for keeping `peek` safe! :lock: :heart:
