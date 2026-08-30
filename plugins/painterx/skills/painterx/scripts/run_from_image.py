#!/usr/bin/env python3
"""Vectorize a cleaned reference, merge live text, and draw it in Illustrator."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def run(command: list[str], label: str) -> None:
    process = subprocess.run(command, capture_output=True, text=True)
    if process.returncode:
        raise RuntimeError(f"{label}: {(process.stderr or process.stdout).strip()}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-image", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--text-manifest", required=True, type=Path)
    parser.add_argument("--placement", default="center")
    parser.add_argument("--max-width-fraction", type=float, default=0.72)
    parser.add_argument("--max-height-fraction", type=float, default=0.78)
    parser.add_argument("--delay-ms", type=int, default=0)
    parser.add_argument("--min-batch-size", type=int, default=20)
    parser.add_argument("--max-batch-size", type=int, default=50)
    parser.add_argument("--trace-preset", choices=("poster", "photo", "bw"), default="poster")
    parser.add_argument("--trace-detail", choices=("auto", "standard", "high"), default="auto")
    parser.add_argument("--trace-upscale-factor", type=int, default=0)
    parser.add_argument("--trace-max-colors", type=int)
    parser.add_argument("--save-ai", action="store_true", help="Save AI only when explicitly requested")
    parser.add_argument("--export-png", action="store_true", help="Export PNG only when explicitly requested")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    scripts = Path(__file__).resolve().parent
    input_image = args.input_image.resolve(strict=True)
    manifest = args.text_manifest.resolve(strict=True)
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    allocator = subprocess.run(
        [sys.executable, str(scripts / "allocate_shibielujing_name.py"), "--root", str(output_root)],
        capture_output=True, text=True,
    )
    if allocator.returncode:
        raise RuntimeError("Output-name allocation failed: " + allocator.stderr.strip())
    base_name = allocator.stdout.strip().splitlines()[-1]
    job_root = output_root / base_name
    job_root.mkdir(parents=True, exist_ok=True)
    raw_svg = job_root / f"{base_name}-vector.svg"
    master_svg = job_root / f"{base_name}.svg"
    output_ai = job_root / f"{base_name}.ai" if args.save_ai else None
    output_png = job_root / f"{base_name}.png" if args.export_png else None
    cache_dir = job_root / ".cell-lct-internal" / "live-cache"

    vectorize = [
        sys.executable, str(scripts / "vectorize_local.py"),
        "--input-image", str(input_image), "--output-svg", str(raw_svg),
        "--preset", args.trace_preset, "--detail", args.trace_detail,
        "--upscale-factor", str(args.trace_upscale_factor),
    ]
    if args.trace_max_colors is not None:
        vectorize.extend(["--max-colors", str(args.trace_max_colors)])
    run(vectorize, "Local vectorization failed")
    run([sys.executable, str(scripts / "merge_live_text.py"), "--input-svg", str(raw_svg), "--text-manifest", str(manifest), "--output-svg", str(master_svg)], "Live-text merge failed")
    draw = [
        sys.executable, str(scripts / "run_cell_lct.py"), "--input-svg", str(master_svg),
        "--work-dir", str(cache_dir),
        "--placement", args.placement, "--max-width-fraction", str(args.max_width_fraction),
        "--max-height-fraction", str(args.max_height_fraction), "--delay-ms", str(args.delay_ms),
        "--min-batch-size", str(args.min_batch_size), "--max-batch-size", str(args.max_batch_size),
    ]
    if output_ai:
        draw.extend(["--output-ai", str(output_ai)])
    if output_png:
        draw.extend(["--output-png", str(output_png)])
    if args.dry_run:
        draw.append("--dry-run")
    run(draw, "Illustrator playback failed")
    print(json.dumps({
        "ok": True, "mode": "dry-run" if args.dry_run else "draw", "base_name": base_name,
        "vectorizer": "vtracer-local", "network_used": False, "api_key_used": False,
        "svg": str(master_svg), "vector_svg": str(raw_svg), "text_manifest": str(manifest),
        "ai": str(output_ai) if output_ai and not args.dry_run else None,
        "png": str(output_png) if output_png and not args.dry_run else None,
        "work_dir": str(cache_dir),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"RUN_FROM_IMAGE_ERROR|{exc}", file=sys.stderr)
        raise SystemExit(1)
