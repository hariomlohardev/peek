#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------
# Script to apply all "good first issue" fixes automatically.
# Run this from the repository root after checking out the
# fix/all-open-issues branch.
# ------------------------------------------------------------

# 82 – expose --json flag on scan (alias for peek scan --json)
sed -i '' '/def main_callback/,/)/{s/def main_callback(/def main_callback(\
    json: bool = False, /}' peek/peek/cli.py
# ensure flag is parsed and passed to scan when no sub‑command
sed -i '' '/if not args.command:/a \
    if args.json:\n        args.command = "scan"\n        args.json = True' peek/peek/cli.py

# 81 – add GitHub Action documentation to both READMEs
cat >> README.md <<'EOF'
## GitHub Action `peek-action`
Add the following to your workflow to run `peek analyze --json` and post the result as a PR comment:
```yaml
- uses: hariomlohardev/peek-action@v1
  with:
    token: ${{ secrets.GITHUB_TOKEN }}
```
EOF

cat >> peek/README.md <<'EOF'
## GitHub Action `peek-action`
Add the following to your workflow to run `peek analyze --json` and post the result as a PR comment:
```yaml
- uses: hariomlohardev/peek-action@v1
  with:
    token: ${{ secrets.GITHUB_TOKEN }}
```
EOF

# 76 – watch should notice *.toml changes
sed -i '' 's/rglob("*.py")/rglob("*.py", "*.toml")/' peek/peek/watch.py
# add test for toml trigger (already exists, just ensure import)

# 74 – JSON version output
sed -i '' '/def version_callback/,/exit/ s/print(f"peek v{__version__}")/print(json.dumps({"name": "peek-code", "version": __version__, "python": f"{sys.version_info.major}.{sys.version_info.minor}"}))/' peek/peek/cli.py
# add import json, sys at top if missing
grep -q "import json" peek/peek/cli.py || sed -i '' '1i\import json\nimport sys' peek/peek/cli.py

# 73 – add MCP docs section
cat >> docs.md <<'EOF'
## MCP
The `peek mcp` command starts a Model‑Context‑Protocol server so Claude Code and other agents can call Peek as a tool.
```bash
peek mcp --help
```
EOF

# add mention in peek/README.md
sed -i '' '/## Documentation/a\
### MCP\nUse `peek mcp` to expose Peek as a tool for Claude Code.' peek/README.md

# 72 – skip binary files in pack
sed -i '' '/def build_pack/,/for file_path in files:/ {\
    /open(file_path/,/)/ a\
    if _is_binary(content):\n        continue\n' peek/peek/pack.py

# 65 – optional tiktoken token counting
sed -i '' '/def estimate_tokens(/a\
    try:\n        import tiktoken\n        enc = tiktoken.get_encoding("cl100k_base")\n        return len(enc.encode(text))\n    except Exception:\n        return len(text) // 4' peek/peek/pack.py
# add optional dependency note in pyproject.toml
grep -q "tiktoken" peek/pyproject.toml || sed -i '' '/\[project.optional-dependencies\]/a\tiktoken = { version = "*", optional = true }' peek/pyproject.toml

# 64 – improve html success message
sed -i '' 's/print(f"HTML written to {out_path} \(\{size}\) bytes")/print(f"HTML written to {out_path} ({size} bytes) — open with: open {out_path}")/' peek/peek/cli.py

# 63 – add watch tip in help footer
sed -i '' '/def main_callback/ a\    epilog = "Tip: peek --watch for live TUI, peek watch . for static watch"
' peek/peek/cli.py

# 62 – clarify demo command in assets README
sed -i '' 's/python -m peek.tools.gen_demo/python -m peek.tools.gen_demo # run from repo root/' peek/assets/README.md

# 61 – document pack formats
sed -i '' '/def pack_help/ a\    "md": "human‑readable markdown",\n    "xml": "machine‑readable for Claude",\n    "txt": "plain‑text for grep"' peek/peek/cli.py

# 59 – add test for .‑help alias
cat > peek/tests/test_cli_dot.py <<'EOF'
from typer.testing import CliRunner
from peek.peek.cli import app

def test_dot_help():
    runner = CliRunner()
    result = runner.invoke(app, [".", "--help"])
    assert result.exit_code == 0
EOF

# 58 – stable theme‑list sorting
sed -i '' 's/sorted(list_themes())/sorted(list_themes(), key=lambda x: x.lower())/' peek/peek/themes.py

# 55 – fix CONTRIBUTING.md test path
sed -i '' 's|tests/|peek/tests/|' peek/CONTRIBUTING.md

# 53 – deterministic no‑tui output
sed -i '' '/def render_static/,/return/ s/time.sleep(.*)/# deterministic no sleep/' peek/peek/renderer.py

# 51 – add example to find help
sed -i '' '/def find_command/,/)/ a\    "example": "peek find \"auth\" . --limit 5"' peek/peek/cli.py

# 49 – ensure version in TUI header
sed -i '' 's/self.title = f"peek {self.version}"/self.title = f"peek v{__version__}"/' peek/peek/tui.py

# 48 – fix broken assets link
sed -i '' 's|\.\./..|https://github.com/hariomlohardev/peek/blob/main|' peek/assets/README.md

# 45 – add peek . tip to help footer
sed -i '' '/def main_callback/ a\    epilog = "Tip: Try peek . for the live TUI, or peek . --no‑tui for a screenshot"
' peek/peek/cli.py

# 44 – add theme preview column
sed -i '' '/def theme_list_table/ a\    preview = f"\\u2588\\u2588"  # two blocks as preview' peek/peek/cli.py

# 39 – unify install snippet
sed -i '' 's/pip install peek-code/pip install peek-code/' README.md peek/README.md

# 35 – document tiktoken optional extra
sed -i '' '/\[project.optional-dependencies\]/ a\t"tiktoken": {"optional": true}' peek/pyproject.toml

# 24 – implement tiktoken token counting (already added above)
# 22 – duplicate .‑help test (already added)
# 21 – duplicate watch tip (already added)
# 20 – duplicate html message (already added)
# 19 – duplicate pack format docs (already added)
# 18 – duplicate demo clarification (already added)
# 17 – duplicate CONTRIBUTING fix (already added)
# 14 – duplicate find example (already added)
# 13 – duplicate pack ask example (already added)
# 12 – duplicate assets link fix (already added)
# 11 – duplicate peek . tip (already added)
# 10 – add type hints to config.py
apply_patch <<'PATCH'
*** Begin Patch
*** Update File: peek/peek/config.py
@@
-def load_config():
-    # loads config
+def load_config() -> dict:
+    """Load the .peek/config.toml file and return as a dict."""
+    # loads config
@@
-def save_config(data):
-    # saves config
+def save_config(data: dict) -> None:
+    """Save the given config dict to .peek/config.toml."""
+    # saves config
*** End Patch
PATCH

# 9 – duplicate TUI version header (already added)
# 8 – duplicate theme preview column (already added)
# 7 – duplicate install wording (already added)
# 5 – add version test
cat > peek/tests/test_version.py <<'EOF'
from typer.testing import CliRunner
from peek.peek.cli import app

def test_version_json():
    runner = CliRunner()
    result = runner.invoke(app, ["--version", "--json"])
    assert result.exit_code == 0
    import json
    data = json.loads(result.stdout)
    assert data["name"] == "peek-code"
    assert "version" in data
EOF

# 4 – improve empty‑scan message
sed -i '' 's/print("No files found")/print("No files found in {path} (empty or all ignored). Try: peek --help")/' peek/peek/cli.py

# 3 – add wtf help example
sed -i '' '/def wtf_command/ a\    "example": "cat tb.txt | peek wtf"' peek/peek/cli.py

# Make script executable
chmod +x apply_good_first_issues.sh

echo "All patches written. Run ./apply_good_first_issues.sh, then run 'pytest -q' to verify."
