"""Helen agent launcher."""
import os
import subprocess
import sys
from pathlib import Path


def check_nodejs() -> bool:
    """Check if Node.js is installed."""
    try:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except FileNotFoundError:
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
        "sqlalchemy": "sqlalchemy",
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
    """Check if frontend node_modules exists."""
    frontend_dir = agent_dir / "webui" / "frontend"
    node_modules = frontend_dir / "node_modules"
    return node_modules.exists()


def install_node_modules(agent_dir: Path) -> bool:
    """Install frontend dependencies."""
    frontend_dir = agent_dir / "webui" / "frontend"
    print("📦 Installing frontend dependencies...")
    result = subprocess.run(
        ["npm", "install"],
        cwd=frontend_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"❌ Error installing node modules:")
        print(result.stderr)
        return False
    print("✅ Frontend dependencies installed")
    return True


def launch_agent():
    """Launch helenagent Web UI."""
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
        print('    api_key: "your-api-key"')
        print('    model: "gpt-4"')
        print()
        response = input("Continue anyway? [y/N] ")
        if response.lower() != 'y':
            return 1
        print()

    # Launch Web UI
    start_script = agent_dir / "start-web.sh"
    if not start_script.exists():
        print("❌ Error: start-web.sh not found")
        return 1

    print("✅ Starting Helen programming assistant...")
    print()

    try:
        result = subprocess.run(["bash", str(start_script)], cwd=agent_dir)
        return result.returncode
    except KeyboardInterrupt:
        # Ctrl+C pressed - the start-web.sh script handles cleanup
        # Just exit cleanly without showing traceback
        print("\n👋 Helen agent stopped")
        return 0
