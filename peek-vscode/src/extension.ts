import * as child_process from "child_process";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import * as vscode from "vscode";

interface RankedFile {
  path: string;
  score: number;
  reasons?: string[];
}

function workspaceRoot(): string | undefined {
  return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
}

/** Prefer `peek` on PATH, fall back to `python -m peek` / `py -m peek`. */
function peekBase(): string[] {
  for (const cmd of [["peek"], ["python", "-m", "peek"], ["py", "-m", "peek"]]) {
    try {
      child_process.execFileSync(cmd[0], [...cmd.slice(1), "--version"], { timeout: 8000 });
      return cmd;
    } catch {
      // try next
    }
  }
  return ["peek"];
}

function runPeek(args: string[], cwd: string): string {
  const base = peekBase();
  return child_process.execFileSync(base[0], [...base.slice(1), ...args], {
    cwd,
    timeout: 60000,
    maxBuffer: 64 * 1024 * 1024,
  }).toString();
}

function analyzeJson(root: string): { ranked: RankedFile[]; summary: string } {
  try {
    const data = JSON.parse(runPeek(["analyze", root, "--json"], root));
    return { ranked: data.ranked ?? [], summary: data.summary ?? "" };
  } catch (err) {
    void err;
    return { ranked: [], summary: "" };
  }
}

class StartHereProvider implements vscode.TreeDataProvider<RankedFile> {
  private readonly didChange = new vscode.EventEmitter<void>();
  readonly onDidChangeTreeData = this.didChange.event;
  private items: RankedFile[] = [];

  refresh(): void {
    const root = workspaceRoot();
    this.items = root ? analyzeJson(root).ranked.slice(0, 20) : [];
    this.didChange.fire();
  }

  getTreeItem(file: RankedFile): vscode.TreeItem {
    const root = workspaceRoot() ?? "";
    const item = new vscode.TreeItem(
      `${file.path} (${Number(file.score).toFixed(1)})`,
      vscode.TreeItemCollapsibleState.None
    );
    item.tooltip = (file.reasons ?? []).join(", ");
    item.command = {
      command: "vscode.open",
      title: "Open file",
      arguments: [vscode.Uri.file(path.join(root, file.path))],
    };
    return item;
  }

  getChildren(): vscode.ProviderResult<RankedFile[]> {
    return this.items;
  }
}

async function showMapPanel(context: vscode.ExtensionContext): Promise<void> {
  const root = workspaceRoot();
  if (!root) {
    void vscode.window.showWarningMessage("Peek: open a folder first.");
    return;
  }
  const outFile = path.join(os.tmpdir(), `peek-${Date.now()}.html`);
  try {
    runPeek(["--html", "-o", outFile], root);
  } catch {
    void vscode.window.showErrorMessage("Peek: failed to build the map. Is peek installed? (`pip install peek-code`)");
    return;
  }
  const html = fs.readFileSync(outFile, "utf-8");
  const panel = vscode.window.createWebviewPanel("peekMap", "Peek map", vscode.ViewColumn.One, {
    enableScripts: false,
    retainContextWhenHidden: true,
  });
  panel.webview.html = html;
  context.subscriptions.push(panel);
}

export function activate(context: vscode.ExtensionContext): void {
  const provider = new StartHereProvider();
  context.subscriptions.push(
    vscode.window.registerTreeDataProvider("peekStartHere", provider),
    vscode.commands.registerCommand("peek-vscode.peek", () => showMapPanel(context)),
    vscode.commands.registerCommand("peek-vscode.refresh", () => provider.refresh())
  );
  provider.refresh();
}

export function deactivate(): void {
  // nothing to clean up
}
