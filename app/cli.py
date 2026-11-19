import subprocess
import sys

import uvicorn


def dev() -> None:
    """Start the FastAPI dev server with hot-reload."""
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


def start() -> None:
    """Start the FastAPI server without reload."""
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)


def lint() -> int:
    """Run Ruff lint checks."""
    return subprocess.run([sys.executable, "-m", "ruff", "check", "."]).returncode


def format_code() -> int:
    """Format code with Ruff."""
    return subprocess.run([sys.executable, "-m", "ruff", "format", "."]).returncode


def format_check() -> int:
    """Check code formatting with Ruff."""
    return subprocess.run([sys.executable, "-m", "ruff", "format", "--check", "."]).returncode


def test() -> int:
    """Run the test suite with pytest."""
    return subprocess.run([sys.executable, "-m", "pytest", "-v"]).returncode
