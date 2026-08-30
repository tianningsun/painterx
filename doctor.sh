#!/bin/bash
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
skill_root="${CODEX_HOME:-$HOME/.codex}/skills/painterx"
python_bin="$skill_root/.venv/bin/python"
if [[ ! -x "$python_bin" ]]; then python_bin="$(command -v python3)"; fi
exec "$python_bin" "$repo_root/doctor.py" --skill-root "$skill_root" "$@"
