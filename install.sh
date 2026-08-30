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
source_skill="$repo_root/plugins/painterx/skills/painterx"
target="$destination/painterx"
mkdir -p "$destination"
if [[ -e "$target" && "$force" -ne 1 ]]; then
  echo "Target exists: $target (pass --force to replace it)" >&2
  exit 1
fi
if [[ -e "$target" ]]; then
  backup="$target.backup.$(date +%Y%m%d%H%M%S)"
  mv "$target" "$backup"
  echo "Existing skill moved to: $backup"
fi
mkdir -p "$target"
/usr/bin/rsync -a --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc' "$source_skill/" "$target/"
echo "INSTALL_OK|skill=$target"
