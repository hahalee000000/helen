"""Helen agent launcher."""
import os
import signal
import subprocess
import sys
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"


def check_nodejs() -> bool:
    """Check if Node.js is installed."""
    try:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            shell=IS_WINDOWS,  # node.exe works without shell, but keep consistent
        )
        return result.returncode == 0
    except (FileNotFoundError, OSError):
        return False


def check_agent_dependencies() -> tuple[bool, list[str]]:
    """Check if agent dependencies are installed.

    Returns:
        (success, missing_packages)
    """
    missing = []

    packages = {
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "websockets": "websockets",
        "pydantic": "pydantic",
        "pydantic_settings": "pydantic-settings",
        "dotenv": "python-dotenv",
        "multipart": "python-multipart",
    }

    for module, package in packages.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)

    return len(missing) == 0, missing


def check_node_modules(agent_dir: Path) -> bool:
    """Check if frontend node_modules exists and is usable."""
    frontend_dir = agent_dir / "webui" / "frontend"
    node_modules = frontend_dir / "node_modules"
    if not node_modules.exists():
        return False
    # Verify key binary exists (incomplete installs leave empty node_modules)
    if IS_WINDOWS:
        vite_bin = node_modules / ".bin" / "vite.cmd"
    else:
        vite_bin = node_modules / ".bin" / "vite"
    return vite_bin.exists()


def install_node_modules(agent_dir: Path) -> bool:
    """Install frontend dependencies."""
    frontend_dir = agent_dir / "webui" / "frontend"
    print("📦 Installing frontend dependencies...")
    try:
        # shell=True is required on Windows: npm is a .cmd batch file,
        # and CreateProcess can only resolve direct executables without it.
        result = subprocess.run(
            ["npm", "install"],
            cwd=frontend_dir,
            capture_output=True,
            text=True,
            shell=IS_WINDOWS,
        )
    except (FileNotFoundError, OSError) as e:
        print(f"❌ Failed to run npm: {e}")
        print("   Make sure Node.js is installed: https://nodejs.org/")
        return False
    if result.returncode != 0:
        print(f"❌ Error installing node modules:")
        print(result.stderr)
        return False
    print("✅ Frontend dependencies installed")
    return True


def launch_agent():
    """Launch Helen Web UI (cross-platform)."""
    print("=" * 60)
    print("🚀 Helen Programming Assistant")
    print("=" * 60)
    print()

    # Check Node.js
    if not check_nodejs():
        print("❌ Error: Node.js is not installed.")
        print()
        print("Helen agent requires Node.js 18+ for the frontend.")
        print()
        print("Install Node.js:")
        print("  https://nodejs.org/")
        print()
        print("Or using a version manager:")
        print("  nvm install 18")
        print("  nvm use 18")
        return 1

    # Check Python dependencies
    success, missing = check_agent_dependencies()
    if not success:
        print("❌ Error: Helen agent requires additional Python packages.")
        print()
        print("Missing packages:")
        for pkg in missing:
            print(f"  - {pkg}")
        print()
        print("Install with:")
        print("  pip install helen-lang[agent]")
        print()
        print("Or install individually:")
        print(f"  pip install {' '.join(missing)}")
        return 1

    # Find agent directory
    helen_dir = Path(__file__).parent.parent
    agent_dir = helen_dir / "agent"

    if not agent_dir.exists():
        print("❌ Error: agent directory not found")
        print(f"Expected location: {agent_dir}")
        return 1

    # Check node_modules
    if not check_node_modules(agent_dir):
        print("⚠️  Frontend dependencies not found")
        print()
        if not install_node_modules(agent_dir):
            print()
            print("Please install manually:")
            print(f"  cd {agent_dir / 'webui' / 'frontend'}")
            print("  npm install")
            return 1
        print()

    # Check LLM configuration
    config_path = Path.home() / ".helen" / "config.yaml"
    if not config_path.exists():
        print("⚠️  Warning: LLM configuration not found")
        print()
        print(f"Please configure your LLM API in:")
        print(f"  {config_path}")
        print()
        print("Example:")
        print("  llm:")
        print('    base_url: "https://api.openai.com/v1"')
        print('    api_key: "your-key"')
        print('    model: "gpt-4"')
        print()
        response = input("Continue anyway? [y/N] ")
        if response.lower() != 'y':
            return 1
        print()

    # Launch Web UI using cross-platform Python script
    start_script = agent_dir / "webui" / "start_webui.py"
    if not start_script.exists():
        print("❌ Error: start_webui.py not found")
        return 1

    # Pass user's current directory to the Web UI
    # This ensures the Web UI uses the user's project directory, not the agent directory
    env = os.environ.copy()
    env["HELEN_WEBUI_CWD"] = str(Path.cwd())

    print("✅ Starting Helen programming assistant...")
    print()

    try:
        if IS_WINDOWS:
            # On Windows, use CREATE_NEW_PROCESS_GROUP for proper process management
            proc = subprocess.Popen(
                [sys.executable, str(start_script)],
                cwd=str(agent_dir),
                env=env,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )
        else:
            # On Unix, use process group for signal forwarding
            proc = subprocess.Popen(
                [sys.executable, str(start_script)],
                cwd=str(agent_dir),
                env=env,
                preexec_fn=os.setsid,
            )

            # Signal forwarding: forward SIGTERM/SIGINT to the entire process group
            def forward_signal(signum, frame):
                try:
                    os.killpg(os.getpgid(proc.pid), signum)
                except ProcessLookupError:
                    pass

            signal.signal(signal.SIGTERM, forward_signal)
            signal.signal(signal.SIGINT, forward_signal)

        try:
            proc.wait()
            return proc.returncode
        except KeyboardInterrupt:
            if IS_WINDOWS:
                # On Windows, terminate the process tree
                try:
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                        capture_output=True,
                        timeout=10,
                    )
                except (subprocess.TimeoutExpired, OSError):
                    pass
            else:
                # On Unix, forward SIGINT to process group
                forward_signal(signal.SIGINT, None)
                proc.wait()
            print("\n👋 Helen agent stopped")
            return 0
    except Exception as e:
        print(f"❌ Error launching Helen agent: {e}")
        return 1
