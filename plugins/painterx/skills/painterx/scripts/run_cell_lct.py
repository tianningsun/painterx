#!/usr/bin/env python3
"""Prepare cached geometry and play it into Illustrator on macOS or Windows."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from illustrator_bridge import run_session


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    temporary.replace(path)


def paint_names(cache: dict, batch: dict) -> list[str]:
    names: list[str] = []
    for atom_index in batch["atom_indices"]:
        atom = cache["atoms"][int(atom_index)]
        if atom["kind"] == "text" or len(atom["paintParts"]) <= 1:
            names.append(atom["objectName"])
        else:
            names.extend(f"{atom['objectName']}_P{index}" for index in range(len(atom["paintParts"])))
    return names


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-svg", required=True, type=Path)
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--output-ai", type=Path)
    parser.add_argument("--output-png", type=Path)
    parser.add_argument("--min-batch-size", type=int, default=20)
    parser.add_argument("--max-batch-size", type=int, default=50)
    parser.add_argument("--complex-point-threshold", type=int, default=320)
    parser.add_argument("--max-batch-points", type=int, default=2200)
    parser.add_argument("--delay-ms", type=int, default=0)
    parser.add_argument("--target-layer-name", default="")
    parser.add_argument("--placement", choices=("center", "top-center", "left-center", "bottom-center", "bottom-right", "top-right", "bottom-left", "top-left"), default="center")
    parser.add_argument("--max-width-fraction", type=float, default=0.72)
    parser.add_argument("--max-height-fraction", type=float, default=0.78)
    parser.add_argument("--checkpoint-every-batches", type=int, default=5)
    parser.add_argument("--minimum-illustrator-major", type=int, default=25)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.min_batch_size <= args.max_batch_size <= 50:
        parser.error("batch sizes must satisfy 1 <= min <= max <= 50")
    if not 0 <= args.delay_ms <= 1000:
        parser.error("delay-ms must be 0..1000")

    input_svg = args.input_svg.resolve(strict=True)
    work_dir = args.work_dir.resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    output_ai = args.output_ai.resolve() if args.output_ai else None
    output_png = args.output_png.resolve() if args.output_png else None
    if output_ai:
        output_ai.parent.mkdir(parents=True, exist_ok=True)
    if output_png:
        output_png.parent.mkdir(parents=True, exist_ok=True)

    cache_path = work_dir / "geometry-cache.json"
    if cache_path.exists():
        job_seed = str(json.loads(cache_path.read_text(encoding="utf-8-sig"))["job_id"])
    else:
        job_seed = input_svg.stem
    job_id = re.sub(r"[^A-Za-z0-9_-]", "_", job_seed).strip("_")[:48] or "job"
    prepare = Path(__file__).with_name("prepare_geometry_cache.py")
    command = [
        sys.executable, str(prepare), "--input", str(input_svg), "--output-dir", str(work_dir),
        "--job-id", job_id, "--min-batch-size", str(args.min_batch_size), "--max-batch-size", str(args.max_batch_size),
        "--complex-point-threshold", str(args.complex_point_threshold), "--max-batch-points", str(args.max_batch_points),
    ]
    prepared = subprocess.run(command, capture_output=True, text=True)
    if prepared.returncode:
        raise RuntimeError("Geometry cache preparation failed: " + prepared.stderr.strip())

    cache = json.loads(cache_path.read_text(encoding="utf-8-sig"))
    state_path = work_dir / "playback.json"
    state = json.loads(state_path.read_text(encoding="utf-8-sig"))
    if args.dry_run:
        print(f"DRY_RUN|cache={cache_path}|state={state_path}|atoms={cache['total_atoms']}|batches={len(state['batches'])}|illustrator_untouched=true")
        return 0

    batches_dir = work_dir / "batches"
    batches_dir.mkdir(exist_ok=True)
    plan_batches = []
    qa_batches = []
    for batch_state in state["batches"]:
        atoms = [cache["atoms"][int(index)] for index in batch_state["atom_indices"]]
        batch_path = batches_dir / f"batch-{int(batch_state['index']):04d}.json"
        atomic_json(batch_path, {"viewBox": cache["view_box"], "atoms": atoms})
        plan_batches.append({"batchJsonPath": batch_path.as_posix(), "groupName": batch_state["group_name"]})
        qa_batches.append({"groupName": batch_state["group_name"], "paintNames": paint_names(cache, batch_state)})

    progress_path = work_dir / "session-progress.json"
    progress_path.unlink(missing_ok=True)
    runtime = Path(__file__).with_name("cell_lct_cached_runtime.jsx").resolve()
    session_runtime = Path(__file__).with_name("painterx_session.jsx").resolve()
    plan = {
        "runtimePath": runtime.as_posix(), "progressPath": progress_path.as_posix(),
        "rootGroupName": state["root_group_name"], "batches": plan_batches,
        "batchGroupNames": [item["group_name"] for item in state["batches"]], "qaBatches": qa_batches,
        "placement": args.placement, "maxWidthFraction": args.max_width_fraction,
        "maxHeightFraction": args.max_height_fraction, "delayMs": args.delay_ms,
        "targetLayerName": args.target_layer_name, "outputAi": output_ai.as_posix() if output_ai else "",
        "outputPng": output_png.as_posix() if output_png else "", "checkpointEveryBatches": max(1, args.checkpoint_every_batches),
        "minimumIllustratorMajor": args.minimum_illustrator_major,
    }
    result = ""
    try:
        result = run_session(plan, session_runtime, work_dir)
    finally:
        progress = json.loads(progress_path.read_text(encoding="utf-8")) if progress_path.exists() else {"completed": 0}
        completed = int(progress.get("completed", 0))
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        for index, batch_state in enumerate(state["batches"]):
            if index < completed:
                batch_state["completed"] = True
                batch_state["completed_at"] = batch_state.get("completed_at") or now
                batch_state["last_error"] = None
            elif index == completed and not progress.get("ok", True):
                batch_state["attempts"] = int(batch_state.get("attempts", 0)) + 1
                batch_state["last_error"] = str(progress.get("message", "Illustrator session failed"))
        state["updated_at"] = now
        atomic_json(state_path, state)

    if not result.startswith("OK|"):
        raise RuntimeError(result or "Illustrator session returned no result")
    if (output_ai and not output_ai.is_file()) or (output_png and not output_png.is_file()):
        raise RuntimeError("QA_FAILED|An explicitly requested output is missing.")
    ai_result = str(output_ai) if output_ai else "not-requested"
    png_result = str(output_png) if output_png else "not-requested"
    print(f"PAINTERX_COMPLETE|cache={cache_path}|ai={ai_result}|png={png_result}|batches={len(state['batches'])}|illustrator_window_untouched=true")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"PAINTERX_ERROR|{exc}", file=sys.stderr)
        raise SystemExit(1)
