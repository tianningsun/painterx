#!/usr/bin/env python3
"""Read-only diagnostics for PainterX."""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from importlib.metadata import version
from pathlib import Path

VERSION = "0.4.0-desktop.3"


def default_skill_root() -> Path:
    codex_root = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    return codex_root / "skills/painterx"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill-root", type=Path, default=default_skill_root())
    parser.add_argument("--require-illustrator-open", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    skill_root = args.skill_root.resolve()
    sys.path.insert(0, str(skill_root / "scripts"))
    checks: list[dict] = []

    def add(name: str, status: str, message: str, required: bool = True) -> None:
        checks.append({"name": name, "status": status, "required": required, "message": message})

    supported_platform = sys.platform in {"darwin", "win32"}
    add("platform", "PASS" if supported_platform else "FAIL", platform.platform())
    version_ok = (3, 11) <= sys.version_info[:2] < (3, 15)
    add("python", "PASS" if version_ok else "FAIL", platform.python_version())
    for package, expected in (("fonttools", "4.61.1"), ("vtracer", "1.0.0a3"), ("pillow", "12.3.0")):
        try:
            found = version(package)
            add(package, "PASS" if found == expected else "FAIL", f"{found} (expected {expected})")
        except Exception as error:
            add(package, "FAIL", str(error))
    add("skill", "PASS" if (skill_root / "SKILL.md").is_file() else "FAIL", str(skill_root))

    try:
        from illustrator_bridge import installed_illustrators, is_running, platform_name
        installed = installed_illustrators()
        add("illustrator", "PASS" if installed else "FAIL", ", ".join(item["version"] for item in installed) or "not found")
        running = is_running()
        add(
            "illustrator-open",
            "PASS" if running or not args.require_illustrator_open else "FAIL",
            "running" if running else f"not running; {platform_name()} playback will launch it and create a blank document",
            args.require_illustrator_open,
        )
    except Exception as error:
        add("illustrator", "FAIL", str(error))

    fatal = any(item["required"] and item["status"] == "FAIL" for item in checks)
    payload = {"product": "PainterX", "version": VERSION, "ok": not fatal, "checks": checks}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for item in checks:
            print(f"{item['status']}|{item['name']}|{item['message']}")
        print(f"DOCTOR_{'FAIL' if fatal else 'OK'}|version={VERSION}")
    return 1 if fatal else 0


if __name__ == "__main__":
    raise SystemExit(main())
