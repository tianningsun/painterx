#!/bin/bash
set -euo pipefail

destination="${CODEX_HOME:-$HOME/.codex}/skills"
force=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --destination) destination="$2"; shift 2 ;;
    --force) force=1; shift ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

repo_root="$(cd "$(dirname "$0")" && pwd)"
install_args=(--destination "$destination")
if [[ "$force" -eq 1 ]]; then install_args+=(--force); fi
"$repo_root/install.sh" "${install_args[@]}"

skill_root="$destination/painterx"
python3 -m venv "$skill_root/.venv"
"$skill_root/.venv/bin/python" -m pip install --disable-pip-version-check -r "$repo_root/requirements.lock"
"$skill_root/.venv/bin/python" "$repo_root/doctor.py" --skill-root "$skill_root"
echo "SETUP_OK|version=0.4.0-desktop.3|skill=$skill_root"
echo "Restart Codex and start a new task before first use."
