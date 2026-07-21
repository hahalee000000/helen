/**
 * Helen Language VS Code Extension
 *
 * Provides IDE support for the Helen Agent Programming Language:
 * - Syntax highlighting
 * - Language Server Protocol (LSP) integration
 * - Real-time diagnostics
 * - Code completion
 * - Go-to-definition
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';
import {
    LanguageClient,
    LanguageClientOptions,
    ServerOptions,
    TransportKind
} from 'vscode-languageclient/node';

let client: LanguageClient | undefined;

/**
 * Locate the `helen` LSP server binary.
 *
 * Resolution order (when user hasn't configured `helen.lsp.path`):
 *   1. `helen` on PATH (resolves via OS shell — works for most installs)
 *   2. `~/.local/bin/helen` (pip --user install on Linux/macOS)
 *   3. `<workspace>/.venv/bin/helen` (venv activated or project-local)
 *   4. `~/helen/.venv/bin/helen` (common dev layout)
 *
 * Returns the first existing executable, or the literal 'helen' as a
 * last-resort fallback (so the error message stays actionable).
 */
function findHelenBinary(): string {
    // 1. Try PATH via Node's `which`-style lookup
    const pathDirs = (process.env.PATH || '').split(path.delimiter);
    const exeName = process.platform === 'win32' ? 'helen.cmd' : 'helen';
    for (const dir of pathDirs) {
        const candidate = path.join(dir, exeName);
        try {
            if (fs.existsSync(candidate) && fs.statSync(candidate).isFile()) {
                return candidate;
            }
        } catch {
            // ignore permission/IO errors
        }
    }

    // 2. pip --user install location
    const home = os.homedir();
    const userBin = path.join(home, '.local', 'bin', 'helen');
    if (fs.existsSync(userBin)) {
        return userBin;
    }

    // 3. Workspace venv
    const folders = vscode.workspace.workspaceFolders;
    if (folders && folders.length > 0) {
        for (const folder of folders) {
            const venvBin = path.join(folder.uri.fsPath, '.venv', 'bin', 'helen');
            if (fs.existsSync(venvBin)) {
                return venvBin;
            }
        }
    }

    // 4. Common dev layout: ~/helen/.venv/bin/helen
    const devVenv = path.join(home, 'helen', '.venv', 'bin', 'helen');
    if (fs.existsSync(devVenv)) {
        return devVenv;
    }

    // Fallback: let the OS report "command not found" with a clear message
    return 'helen';
}

export function activate(context: vscode.ExtensionContext) {
    console.log('Helen Language extension activated');

    // Get configuration
    const config = vscode.workspace.getConfiguration('helen');
    const lspEnabled = config.get<boolean>('lsp.enabled', true);

    if (!lspEnabled) {
        console.log('Helen LSP is disabled in settings');
        return;
    }

    // Get LSP server path and args. If user left the default 'helen', run
    // auto-detection so the LSP works regardless of whether ~/.local/bin is
    // in VS Code's PATH (which differs between desktop launch and terminal
    // launch on many Linux setups).
    const configuredPath = config.get<string>('lsp.path', 'helen');
    const isDefault = configuredPath === 'helen';
    const lspPath = isDefault ? findHelenBinary() : configuredPath;
    const lspArgs = config.get<string[]>('lsp.args', ['lsp']);

    console.log(`Helen LSP binary: ${lspPath}${isDefault ? ' (auto-detected)' : ' (from settings)'}`);

    // Server options
    const serverOptions: ServerOptions = {
        command: lspPath,
        args: lspArgs,
        transport: TransportKind.stdio
    };

    // Client options
    const clientOptions: LanguageClientOptions = {
        documentSelector: [
            { scheme: 'file', language: 'helen' },
            { scheme: 'untitled', language: 'helen' }
        ],
        synchronize: {
            fileEvents: vscode.workspace.createFileSystemWatcher('**/*.helen')
        },
        diagnosticCollectionName: 'helen',
        outputChannelName: 'Helen Language Server',
        revealOutputChannelOn: 3, // Never
    };

    // Create and start the language client
    client = new LanguageClient(
        'helenLanguageServer',
        'Helen Language Server',
        serverOptions,
        clientOptions
    );

    // Start the client
    client.start().then(() => {
        console.log('Helen Language Server started');
    }).catch((error) => {
        console.error('Failed to start Helen Language Server:', error);
        vscode.window.showErrorMessage(
            `Failed to start Helen Language Server: ${error.message}. ` +
            `Install helen-lang (pip install helen-lang) and ensure 'helen' is ` +
            `on your PATH, or set 'helen.lsp.path' in settings.`
        );
    });

    // Register commands
    const restartCommand = vscode.commands.registerCommand('helen.restartLanguageServer', async () => {
        if (client) {
            await client.stop();
            await client.start();
            vscode.window.showInformationMessage('Helen Language Server restarted');
        }
    });

    context.subscriptions.push(restartCommand);

    // Status bar item
    const statusBarItem = vscode.window.createStatusBarItem(
        vscode.StatusBarAlignment.Right,
        100
    );
    statusBarItem.text = '$(code) Helen';
    statusBarItem.tooltip = 'Helen Language Server';
    statusBarItem.command = 'helen.restartLanguageServer';
    statusBarItem.show();

    context.subscriptions.push(statusBarItem);
}

export function deactivate(): Thenable<void> | undefined {
    if (!client) {
        return undefined;
    }
    return client.stop();
}
