# peek-vscode — Peek map inside VS Code

`Cmd+Shift+P → Peek: Map Workspace` renders `peek --html` in a Webview;
the Explorer view `Peek: Start Here` mirrors the ranked list — click opens the file.

Requires `peek` on PATH (`pip install peek-code`); the extension falls back to
`python -m peek` / `py -m peek`.

```bash
cd peek-vscode
npm install
npm run compile        # tsc typecheck + build to out/
npx @vscode/vsce package   # → peek-vscode-0.3.0.vsix
code --install-extension peek-vscode-0.3.0.vsix
```

Marketplace publishing (`vsce publish`) needs a maintainer token — see
[docs.md#vs-code](../docs.md#vs-code).
