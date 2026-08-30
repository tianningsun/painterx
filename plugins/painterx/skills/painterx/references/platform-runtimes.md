# Illustrator platform runtimes

The Python runner selects one bridge while keeping the geometry cache and ExtendScript drawing session identical on both platforms. Neither route uploads the source or uses an API key.

## macOS

Resolve the newest Illustrator application bundle, launch it with `open` when needed, and create one blank document only when no document is open. AppleScript calls Illustrator's `do javascript` once for the complete session. Supported baseline: macOS 12+, Python 3.11–3.14, Illustrator 2021 version 25.2 or newer. The first run may require Automation permission.

## Windows

Use Windows PowerShell and Illustrator's registered COM automation object. Try the generic `Illustrator.Application` ProgID, then versioned ProgIDs from newest to Illustrator 2021. COM may launch Illustrator; create one blank document only when none exists. Pass the same complete ExtendScript session through `DoJavaScript`. Supported baseline: Windows 10/11 x64, Windows PowerShell 5.1 or PowerShell 7, Python 3.11–3.14, Illustrator 2021 or newer.

## Shared invariants

The cached runtime creates native `PathItem`, `CompoundPathItem`, and `TextFrame` objects directly. It never closes or quits Illustrator, never clears existing artwork, and never saves or exports unless explicitly requested. On interruption, rerun with the same SVG and work directory; use a new work directory if the SVG or batch parameters change.
