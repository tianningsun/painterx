#!/usr/bin/env python3
"""Audit whether SVG paths resemble sparse, human-authored pen-tool geometry."""

from __future__ import annotations

import argparse
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path

from fontTools.pens.recordingPen import RecordingPen
from fontTools.svgLib.path import parse_path


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def point(value: tuple[float, float]) -> tuple[float, float]:
    return float(value[0]), float(value[1])


def distance(first: tuple[float, float], second: tuple[float, float]) -> float:
    return math.hypot(second[0] - first[0], second[1] - first[1])


def inspect_path(path_data: str) -> dict:
    pen = RecordingPen()
    parse_path(path_data, pen)
    anchors = segments = short_segments = subpaths = 0
    current: tuple[float, float] | None = None
    start: tuple[float, float] | None = None
    for operation, arguments in pen.value:
        if operation == "moveTo":
            current = start = point(arguments[0])
            anchors += 1
            subpaths += 1
        elif operation == "lineTo":
            for value in arguments:
                endpoint = point(value)
                if current is not None:
                    segments += 1
                    short_segments += distance(current, endpoint) < 3.0
                anchors += 1
                current = endpoint
        elif operation == "curveTo":
            for index in range(0, len(arguments), 3):
                endpoint = point(arguments[index + 2])
                if current is not None:
                    segments += 1
                    short_segments += distance(current, endpoint) < 3.0
                anchors += 1
                current = endpoint
        elif operation == "closePath" and current is not None and start is not None:
            if distance(current, start) > 1e-6:
                segments += 1
                short_segments += distance(current, start) < 3.0
            current = start
    return {
        "anchors": anchors,
        "segments": segments,
        "short_segments": short_segments,
        "subpaths": subpaths,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--svg", required=True, type=Path)
    parser.add_argument("--max-anchors-per-path", type=int, default=16)
    parser.add_argument("--max-short-segment-fraction", type=float, default=0.15)
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args()
    tree = ET.parse(args.svg.resolve(strict=True))
    records = []
    for index, element in enumerate(tree.getroot().iter(), 1):
        if local_name(element.tag) != "path" or not element.get("d"):
            continue
        result = inspect_path(element.get("d", ""))
        result["id"] = element.get("id", f"path-{index}")
        records.append(result)
    total_segments = sum(item["segments"] for item in records)
    total_short = sum(item["short_segments"] for item in records)
    excessive = [item for item in records if item["anchors"] > args.max_anchors_per_path]
    short_fraction = total_short / total_segments if total_segments else 0.0
    report = {
        "ok": not excessive and short_fraction <= args.max_short_segment_fraction,
        "paths": len(records),
        "total_anchors": sum(item["anchors"] for item in records),
        "max_anchors": max((item["anchors"] for item in records), default=0),
        "short_segment_fraction": round(short_fraction, 6),
        "excessive_paths": sorted(excessive, key=lambda item: item["anchors"], reverse=True)[:20],
    }
    print(json.dumps(report, ensure_ascii=False))
    return 2 if args.enforce and not report["ok"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
