"""One local/pre-commit check entrypoint; no network access required."""

import ast
import importlib.metadata
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRET_FILES = (".env", ".env.local", "private.pem", "private.key")


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def verify_project_rules() -> None:
    expected_python = (ROOT / ".python-version").read_text().strip()
    actual_python = ".".join(map(str, sys.version_info[:3]))
    if actual_python != expected_python:
        raise SystemExit(f"Use Python {expected_python}; found {actual_python}.")
    for line in (ROOT / "requirements-dev.txt").read_text().splitlines():
        name, version = line.split("==")
        if importlib.metadata.version(name) != version:
            raise SystemExit(f"Install pinned development dependencies: {line}")
    files = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    for name in files:
        if not name.endswith(".py"):
            continue
        source = (ROOT / name).read_text()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.ExceptHandler) and all(
                isinstance(statement, ast.Pass) for statement in node.body
            ):
                raise SystemExit(f"{name}: empty exception handler")
            # No environment settings are currently needed. Fail new env reads
            # until they are introduced through an explicit configuration module.
            if isinstance(node, ast.Attribute) and node.attr in {"environ", "getenv"}:
                raise SystemExit(f"{name}: centralize environment settings first")
            if isinstance(node, ast.ImportFrom) and node.module == "os":
                if any(alias.name in {"environ", "getenv"} for alias in node.names):
                    raise SystemExit(f"{name}: centralize environment settings first")
    for name in SECRET_FILES:
        run("git", "check-ignore", "--quiet", name)
    scan = subprocess.check_output(
        [
            sys.executable,
            "-m",
            "detect_secrets",
            "scan",
            "--all-files",
            "--exclude-files",
            r"(^|/)(\.git|\.venv|\.mypy_cache|\.ruff_cache|__pycache__)/",
        ],
        cwd=ROOT,
        text=True,
    )
    if json.loads(scan)["results"]:
        raise SystemExit("Secret scanner found candidates; inspect before committing.")


def main() -> None:
    verify_project_rules()
    run(sys.executable, "-m", "ruff", "format", "--check", ".")
    run(sys.executable, "-m", "ruff", "check", ".")
    run(sys.executable, "-m", "mypy")
    run(sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v")


if __name__ == "__main__":
    main()
