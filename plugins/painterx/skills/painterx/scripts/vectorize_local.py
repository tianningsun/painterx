#!/usr/bin/env python3
"""Convert a local raster image to SVG with VTracer; no upload or API key."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

ET.register_namespace("", "http://www.w3.org/2000/svg")


def image_dimensions(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        return int(image.width), int(image.height)


def normalize_svg(path: Path, original_size: tuple[int, int], trace_scale: int) -> None:
    tree = ET.parse(path)
    root = tree.getroot()
    if root.tag.rsplit("}", 1)[-1] != "svg":
        raise ValueError("VTracer output root is not SVG.")
    if not root.get("viewBox"):
        numbers = []
        for key in ("width", "height"):
            match = re.search(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)", root.get(key, ""))
            numbers.append(float(match.group(0)) if match else 0.0)
        if numbers[0] <= 0 or numbers[1] <= 0:
            raise ValueError("VTracer output has no usable canvas dimensions.")
        root.set("viewBox", f"0 0 {numbers[0]:g} {numbers[1]:g}")
    if trace_scale > 1:
        namespace = root.tag.rsplit("}", 1)[0].lstrip("{") if "}" in root.tag else "http://www.w3.org/2000/svg"
        group = ET.Element(
            f"{{{namespace}}}g",
            {"id": "vtracer-detail-normalization", "transform": f"scale({1.0 / trace_scale:g})"},
        )
        for child in list(root):
            if child.tag.rsplit("}", 1)[-1] in {"defs", "title", "desc", "metadata"}:
                continue
            root.remove(child)
            group.append(child)
        root.append(group)
        root.set("viewBox", f"0 0 {original_size[0]} {original_size[1]}")
        root.set("width", str(original_size[0]))
        root.set("height", str(original_size[1]))

    counter = 0
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] in {"path", "rect", "circle", "ellipse", "line", "polyline", "polygon"}:
            counter += 1
            if not element.get("id"):
                element.set("id", f"vtracer-{counter:06d}")
    if counter == 0:
        raise ValueError("VTracer produced no editable vector geometry.")
    tree.write(path, encoding="utf-8", xml_declaration=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-image", required=True, type=Path)
    parser.add_argument("--output-svg", required=True, type=Path)
    parser.add_argument("--preset", choices=("poster", "photo", "bw"), default="poster")
    parser.add_argument("--detail", choices=("auto", "standard", "high"), default="auto")
    parser.add_argument("--hierarchy", choices=("stacked", "cutout"), default="stacked", help="stacked favors continuous smooth shapes; cutout creates mosaic-like tiles")
    parser.add_argument("--upscale-factor", type=int, default=0, help="0 chooses automatically; balanced high-detail tracing uses up to 2x")
    parser.add_argument("--max-colors", type=int)
    parser.add_argument("--filter-speckle", type=int)
    parser.add_argument("--simplify", type=float)
    args = parser.parse_args()
    if args.max_colors is not None and not 0 <= args.max_colors <= 256:
        parser.error("max-colors must be 0..256; use 0 to keep the preset default")
    if args.filter_speckle is not None and not 0 <= args.filter_speckle <= 1024:
        parser.error("filter-speckle must be 0..1024")
    if args.simplify is not None and not 0 <= args.simplify <= 10:
        parser.error("simplify must be 0..10")
    if not 0 <= args.upscale_factor <= 8:
        parser.error("upscale-factor must be 0..8")

    try:
        import vtracer
    except ImportError as error:
        raise RuntimeError("VTracer is not installed; run setup.sh.") from error

    input_path = args.input_image.resolve(strict=True)
    if input_path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}:
        raise ValueError("Local vectorization accepts PNG, JPEG, WebP, BMP, or GIF.")
    output_path = args.output_svg.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(output_path.stem + f".tmp.{os.getpid()}.svg")
    temporary_upscaled = output_path.with_name(output_path.stem + f".tmp.{os.getpid()}.upscaled.png")

    source_width, source_height = image_dimensions(input_path)
    longest_side = max(source_width, source_height)
    effective_detail = args.detail
    if effective_detail == "auto":
        effective_detail = "high" if longest_side < 1600 else "standard"
    if args.upscale_factor:
        upscale_factor = args.upscale_factor
    elif effective_detail == "high":
        # Upscaling medium-size artwork introduces interpolated edge colors,
        # which can become thousands of short, wobbly paths. Reserve 2x for
        # genuinely small references; normal figures trace at native size.
        upscale_factor = 2 if longest_side < 1000 else 1
    else:
        upscale_factor = 1

    max_colors = args.max_colors if args.max_colors is not None else 16
    # Upscaling creates interpolated edge pixels. A larger speckle threshold
    # merges those tiny fragments while the denser sampling retains compact
    # organelles and thin connectors.
    filter_speckle = args.filter_speckle if args.filter_speckle is not None else (8 if effective_detail == "high" else 4)
    simplify = args.simplify if args.simplify is not None else (4.0 if effective_detail == "high" else 2.0)
    trace_input = input_path
    if upscale_factor > 1:
        trace_width = source_width * upscale_factor
        trace_height = source_height * upscale_factor
        with Image.open(input_path) as image:
            image.resize((trace_width, trace_height), Image.Resampling.LANCZOS).save(temporary_upscaled, format="PNG")
        trace_input = temporary_upscaled

    if args.preset == "bw":
        config = vtracer.Config.bw()
    elif args.preset == "photo":
        config = vtracer.Config.photo()
    else:
        config = vtracer.Config.poster()
    config.hierarchical = args.hierarchy
    config.filter_speckle = filter_speckle
    config.simplify = simplify or None
    config.path_precision = 4 if effective_detail == "high" else 3
    config.optimize = 2
    if args.preset != "bw" and max_colors:
        config.max_colors = max_colors

    try:
        config.convert_file(str(trace_input), str(temporary))
        normalize_svg(temporary, (source_width, source_height), upscale_factor)
        validator = Path(__file__).with_name("validate_vector_svg.py")
        validation = subprocess.run(
            [sys.executable, str(validator), "--svg", str(temporary)],
            capture_output=True,
            text=True,
        )
        if validation.returncode:
            raise RuntimeError("VTracer output failed true-vector validation: " + (validation.stderr or validation.stdout).strip())
        temporary.replace(output_path)
    finally:
        temporary.unlink(missing_ok=True)
        temporary_upscaled.unlink(missing_ok=True)

    print(json.dumps({
        "ok": True,
        "engine": "vtracer-local",
        "preset": args.preset,
        "detail": effective_detail,
        "hierarchy": args.hierarchy,
        "upscale_factor": upscale_factor,
        "source_size": [source_width, source_height],
        "trace_size": [source_width * upscale_factor, source_height * upscale_factor],
        "max_colors": max_colors,
        "filter_speckle": filter_speckle,
        "simplify": simplify,
        "input_image": str(input_path),
        "output_svg": str(output_path),
        "network_used": False,
        "api_key_used": False,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"LOCAL_VECTORIZE_ERROR|{exc}", file=sys.stderr)
        raise SystemExit(1)
