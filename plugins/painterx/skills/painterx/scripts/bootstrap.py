#!/usr/bin/env python3
"""Create and verify PainterX's private Python environment."""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path

SUPPORTED = (3, 11), (3, 15)


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def venv_python(root: Path) -> Path:
    if sys.platform == "win32":
        return root / ".venv" / "Scripts" / "python.exe"
    return root / ".venv" / "bin" / "python"


def expected_versions(requirements: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in requirements.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "==" not in line:
            raise RuntimeError(f"Unpinned requirement: {line}")
        name, version = line.split("==", 1)
        result[name.strip().lower()] = version.strip()
    return result


def installed_versions(python: Path, packages: list[str]) -> dict[str, str] | None:
    if not python.is_file():
        return None
    code = (
        "import json; from importlib.metadata import version; "
        f"names={packages!r}; "
        "print(json.dumps({name: version(name) for name in names}))"
    )
    result = subprocess.run([str(python), "-c", code], capture_output=True, text=True)
    if result.returncode:
        return None
    return json.loads(result.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify only; never create or install")
    parser.add_argument("--dry-run", action="store_true", help="show the planned setup without changing files")
    args = parser.parse_args()

    if not (SUPPORTED[0] <= sys.version_info[:2] < SUPPORTED[1]):
        raise RuntimeError(f"PainterX requires Python 3.11-3.14; found {platform.python_version()}.")
    root = skill_root()
    requirements = root / "requirements.lock"
    expected = expected_versions(requirements)
    python = venv_python(root)
    found = installed_versions(python, list(expected))
    if found == expected:
        print(f"BOOTSTRAP_OK|python={python}|dependencies=ready|network=false")
        return 0
    if args.check:
        print(f"BOOTSTRAP_REQUIRED|python={python}|dependencies=missing-or-mismatched")
        return 1
    plan = {
        "skill_root": str(root),
        "venv": str(root / ".venv"),
        "requirements": expected,
        "network_required_this_run": True,
        "api_key_required": False,
    }
    if args.dry_run:
        print(json.dumps(plan, ensure_ascii=False))
        return 0

    subprocess.run([sys.executable, "-m", "venv", str(root / ".venv")], check=True)
    python = venv_python(root)
    subprocess.run([
        str(python), "-m", "pip", "install", "--disable-pip-version-check",
        "-r", str(requirements),
    ], check=True)
    found = installed_versions(python, list(expected))
    if found != expected:
        raise RuntimeError(f"Dependency verification failed: expected {expected}, found {found}")
    print(f"BOOTSTRAP_OK|python={python}|dependencies=installed|network=true|api_key=false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"BOOTSTRAP_ERROR|{exc}", file=sys.stderr)
        raise SystemExit(1)
