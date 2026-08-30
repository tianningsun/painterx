#!/usr/bin/env python3
"""Bootstrap PainterX when needed, then run its Illustrator workflow."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    bootstrap = Path(__file__).with_name("bootstrap.py")
    ready = subprocess.run([sys.executable, str(bootstrap), "--check"])
    if ready.returncode:
        subprocess.run([sys.executable, str(bootstrap)], check=True)
    python = root / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    runner = Path(__file__).with_name("run_cell_lct.py")
    return subprocess.run([str(python), str(runner), *sys.argv[1:]]).returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"PAINTERX_LAUNCH_ERROR|{exc}", file=sys.stderr)
        raise SystemExit(1)
