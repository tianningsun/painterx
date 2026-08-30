#!/usr/bin/env python3
"""Cross-platform Illustrator bridge for macOS Apple events and Windows COM."""

from __future__ import annotations

import json
import plistlib
import shutil
import subprocess
import sys
import time
from pathlib import Path

BUNDLE_ID = "com.adobe.illustrator"


def platform_name() -> str:
    if sys.platform == "darwin":
        return "macos"
    if sys.platform == "win32":
        return "windows"
    return "unsupported"


def _mac_installed() -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for app in sorted(Path("/Applications").glob("Adobe Illustrator*/Adobe Illustrator.app")):
        plist = app / "Contents/Info.plist"
        try:
            with plist.open("rb") as handle:
                info = plistlib.load(handle)
            if info.get("CFBundleIdentifier", "").lower() != BUNDLE_ID.lower():
                continue
            results.append({"path": str(app), "version": str(info.get("CFBundleShortVersionString", "unknown"))})
        except (OSError, plistlib.InvalidFileException):
            continue
    return results


def _powershell() -> str | None:
    for executable in ("powershell.exe", "pwsh.exe", "pwsh"):
        found = shutil.which(executable)
        if found:
            return found
    return None


def _windows_bridge(mode: str, bootstrap: Path | None = None, minimum_major: int = 25) -> subprocess.CompletedProcess[str]:
    executable = _powershell()
    if not executable:
        raise RuntimeError("POWERSHELL_NOT_FOUND|Windows PowerShell 5.1 or PowerShell 7 is required.")
    script = Path(__file__).with_name("illustrator_bridge_windows.ps1")
    command = [
        executable, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script),
        "-Mode", mode, "-MinimumIllustratorMajor", str(minimum_major),
    ]
    if bootstrap is not None:
        command.extend(["-BootstrapPath", str(bootstrap)])
    return subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)


def installed_illustrators() -> list[dict[str, str]]:
    if platform_name() == "macos":
        return _mac_installed()
    if platform_name() == "windows":
        process = _windows_bridge("Probe")
        if process.returncode == 0 and process.stdout.strip().startswith("REGISTERED|"):
            version = process.stdout.strip().split("version=", 1)[-1] or "registered"
            return [{"path": "Windows COM registration", "version": version}]
        return []
    return []


def selected_illustrator() -> dict[str, str] | None:
    installed = installed_illustrators()
    if not installed:
        return None
    if platform_name() == "windows":
        return installed[0]
    return max(installed, key=lambda item: tuple(int(part) for part in item["version"].split(".") if part.isdigit()))


def is_running(app_path: str | None = None) -> bool:
    if platform_name() == "windows":
        process = _windows_bridge("IsRunning")
        return process.returncode == 0 and process.stdout.strip().lower() == "true"
    if platform_name() != "macos" or (not app_path and not selected_illustrator()):
        return False
    probe = subprocess.run(
        ["/usr/bin/osascript", "-l", "JavaScript", "-e", f'Application("{BUNDLE_ID}").running()'],
        capture_output=True,
        text=True,
        check=False,
    )
    return probe.returncode == 0 and probe.stdout.strip().lower() == "true"


def ensure_ready(app_path: str | None = None, timeout_seconds: float = 90.0, minimum_major: int = 25) -> dict:
    """Launch Illustrator if needed and create one document only when none exists."""
    if platform_name() == "windows":
        process = _windows_bridge("EnsureReady", minimum_major=minimum_major)
        if process.returncode:
            raise RuntimeError("ILLUSTRATOR_DOCUMENT_ERROR|" + (process.stderr or process.stdout).strip())
        fields = dict(part.split("=", 1) for part in process.stdout.strip().split("|")[1:] if "=" in part)
        return {
            "running": True,
            "launched": fields.get("launched") == "true",
            "documentCreated": fields.get("created") == "true",
            "documentCount": int(fields.get("documents", "0")),
            "version": fields.get("version", "unknown"),
        }
    if platform_name() != "macos":
        raise RuntimeError("UNSUPPORTED_PLATFORM|PainterX supports macOS and Windows only.")
    selected = {"path": app_path} if app_path else selected_illustrator()
    if not selected:
        raise RuntimeError("ILLUSTRATOR_NOT_INSTALLED|Install Adobe Illustrator 2021 (25.2+) or newer.")
    launched = not is_running(selected["path"])
    if launched:
        opened = subprocess.run(["/usr/bin/open", "-a", selected["path"]], capture_output=True, text=True, check=False)
        if opened.returncode:
            raise RuntimeError("ILLUSTRATOR_LAUNCH_ERROR|" + (opened.stderr or opened.stdout).strip())
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if is_running(selected["path"]):
                break
            time.sleep(0.5)
        else:
            raise RuntimeError(f"ILLUSTRATOR_START_TIMEOUT|Illustrator did not become ready within {timeout_seconds:g} seconds.")
    apple_script = f"""
on run argv
  set launchedText to item 1 of argv
  set createdText to "false"
  tell application id "{BUNDLE_ID}"
    activate
    if (count of documents) is 0 then
      make new document
      set createdText to "true"
    end if
    set documentTotal to count of documents
  end tell
  return launchedText & "|" & createdText & "|" & (documentTotal as text)
end run
"""
    process = subprocess.run(["/usr/bin/osascript", "-e", apple_script, "true" if launched else "false"], capture_output=True, text=True, check=False)
    if process.returncode:
        raise RuntimeError("ILLUSTRATOR_DOCUMENT_ERROR|" + (process.stderr or process.stdout).strip())
    parts = process.stdout.strip().split("|")
    return {"running": True, "launched": parts[0] == "true", "documentCreated": parts[1] == "true", "documentCount": int(parts[2])}


def run_session(plan: dict, session_runtime: Path, temp_dir: Path) -> str:
    if platform_name() == "unsupported":
        raise RuntimeError("UNSUPPORTED_PLATFORM|PainterX supports macOS and Windows only.")
    if platform_name() == "macos" and not selected_illustrator():
        raise RuntimeError("ILLUSTRATOR_NOT_INSTALLED|Install Adobe Illustrator 2021 (25.2+) or newer.")
    temp_dir.mkdir(parents=True, exist_ok=True)
    plan_json = json.dumps(plan, ensure_ascii=False, separators=(",", ":"))
    bootstrap = temp_dir / "painterx-bootstrap.jsx"
    bootstrap.write_text(
        "var PAINTERX_PLAN = " + plan_json + ";\n" +
        "$.evalFile(new File(" + json.dumps(session_runtime.as_posix()) + "));\n",
        encoding="utf-8",
    )
    try:
        if platform_name() == "windows":
            process = _windows_bridge("Run", bootstrap=bootstrap, minimum_major=int(plan["minimumIllustratorMajor"]))
        else:
            ensure_ready()
            javascript_command = "$.evalFile(new File(" + json.dumps(str(bootstrap)) + "));"
            apple_script = f"""
on run argv
  tell application id "{BUNDLE_ID}"
    return do javascript (item 1 of argv)
  end tell
end run
"""
            process = subprocess.run(["/usr/bin/osascript", "-e", apple_script, javascript_command], capture_output=True, text=True, check=False)
    finally:
        bootstrap.unlink(missing_ok=True)
    if process.returncode:
        raise RuntimeError("ILLUSTRATOR_BRIDGE_ERROR|" + (process.stderr or process.stdout).strip().replace("\n", " "))
    return process.stdout.strip()


if __name__ == "__main__":
    print(json.dumps({"platform": platform_name(), "running": is_running(), "selected": selected_illustrator(), "installed": installed_illustrators()}, ensure_ascii=False))
