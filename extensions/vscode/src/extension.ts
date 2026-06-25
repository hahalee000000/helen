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
import {
    LanguageClient,
    LanguageClientOptions,
    ServerOptions,
    TransportKind
} from 'vscode-languageclient/node';

let client: LanguageClient | undefined;

export function activate(context: vscode.ExtensionContext) {
    console.log('Helen Language extension activated');

    // Get configuration
    const config = vscode.workspace.getConfiguration('helen');
    const lspEnabled = config.get<boolean>('lsp.enabled', true);
    
    if (!lspEnabled) {
        console.log('Helen LSP is disabled in settings');
        return;
    }

    // Get LSP server path and args
    const lspPath = config.get<string>('lsp.path', 'helen');
    const lspArgs = config.get<string[]>('lsp.args', ['lsp']);

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
            `Make sure 'helen' is installed and in your PATH, ` +
            `or configure 'helen.lsp.path' in settings.`
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
