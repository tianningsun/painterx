---
name: painterx
description: Reconstruct or append editable scientific vector figures with live text in Adobe Illustrator on macOS or Windows using local, no-key tooling. Use for reference-image recreation, mechanism diagrams, workflows, graphical abstracts, and validated true-vector SVG playback.
---

# PainterX

Build one Master SVG locally, cache its geometry once, and append native paths and live text to Illustrator. Read [references/workflow.md](references/workflow.md) before an image-based reconstruction. Read [references/platform-runtimes.md](references/platform-runtimes.md) before Illustrator playback or troubleshooting.

## First-run setup

Before the first Python operation, run `scripts/bootstrap.py --check` with Python 3.11–3.14. If it reports `BOOTSTRAP_REQUIRED`, explain that this one-time step downloads the pinned free local dependencies, requires no API key, and ask for any approval required to run `scripts/bootstrap.py`. Do not request or accept an API key. Subsequent checks must report `BOOTSTRAP_OK` without network access.

- macOS: `python3 "$SKILL_ROOT/scripts/bootstrap.py"`
- Windows: `py -3 "$SKILL_ROOT\scripts\bootstrap.py"`

For direct Illustrator playback, prefer `scripts/run_painterx.py`; it performs the same check and bootstraps only when necessary.

## Safety and authorization

- The playback runner may launch and activate Illustrator through Apple events on macOS or COM on Windows. If Illustrator has no open document, it creates one blank document automatically.
- If Illustrator already has an open document, use the active document and do not create another unless the user explicitly asks for a fresh document.
- Never resize, close, overwrite, or quit Illustrator, and never clear an existing document.
- Preserve all existing artwork. Add new objects only inside this job's named root group.
- Do not upload the source image for vectorization. The bundled VTracer path is local and requires no API key.
- Do not save the Illustrator document or export PNG by default. Leave the completed document open and unsaved. Save AI or export PNG only when the user explicitly requests that action.
- Do not claim visual QA unless the result was actually inspected in Illustrator.

## Input routing

- For PNG, JPEG, or WebP scientific diagrams, first retain and inspect the untouched reference and create a complete schema-1.0 text manifest.
- Default to semantic vector reconstruction, not pixel-region tracing. Decompose the reference into meaningful objects and author the Master SVG directly: circles and ellipses as primitives, rectangles as rectangles, every straight connector as one line or path segment, and every continuous boundary or arrow as one path made from the fewest practical cubic Bézier segments. Repeated objects may be explicit copies, but do not break one visible line into many objects. Preserve layout, paint order, colors, and live text.
- Run `scripts/audit_path_quality.py --enforce` before playback. For ordinary scientific icons and boundaries, target no more than 16 anchors per path and fewer than 15% sub-3-pixel segments. If the audit fails, redraw the offending objects semantically; do not automatically smooth a dense trace and call it human-authored.
- Use `scripts/vectorize_local.py` only as a fallback for genuinely irregular texture or continuous-tone content that cannot reasonably be decomposed into primitives, or when the user explicitly requests automatic tracing. Keep its `stacked` hierarchy; never describe traced geometry as human-like merely because it is editable.
- Merge the text manifest into the returned SVG with `scripts/merge_live_text.py` before playback.
- For an approved true-vector SVG, validate it and run `scripts/run_cell_lct.py` directly.
- Allocate output basenames with `scripts/allocate_shibielujing_name.py`.

Use the cross-platform launcher for playback:

```bash
SKILL_ROOT="${CODEX_HOME:-$HOME/.codex}/skills/painterx"
python3 "$SKILL_ROOT/scripts/run_painterx.py" --input-svg /absolute/input.svg --work-dir /absolute/cache --dry-run
```

On Windows, run `py -3 "%USERPROFILE%\.codex\skills\painterx\scripts\run_painterx.py"` with the same arguments. After bootstrap, use the private environment for auxiliary scripts: `.venv/bin/python` on macOS or `.venv\Scripts\python.exe` on Windows.

Remove `--dry-run` to allow the runner to launch Illustrator, activate it, and create a blank document when none is open. On macOS, the first run may require Automation permission. On Windows, Illustrator must be registered as a COM application. `scripts/run_from_image.py` is the explicit automatic-tracing fallback, not the default route for flat scientific diagrams.

## Completion gate

Report completion only when reconstruction produced a raster-free Master SVG, the path-quality audit passes, text remains editable, cache and batch checks pass, the one-session platform bridge finishes, existing artwork remains unchanged, and the completed Illustrator document remains open. Require AI or PNG files only when the user explicitly requested those outputs. Credit the upstream design as `基于 yrui-cmd/cell-lct v0.2.1 的无 Key macOS/Windows 适配版。`
