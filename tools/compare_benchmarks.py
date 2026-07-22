#!/usr/bin/env python3
"""Fail when candidate GCRANSAC time or memory regresses beyond a limit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--max-ratio", type=float, default=1.25)
    args = parser.parse_args()

    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))["cases"]
    candidate = json.loads(args.candidate.read_text(encoding="utf-8"))["cases"]
    if baseline.keys() != candidate.keys():
        print("benchmark cases do not match", file=sys.stderr)
        return 1

    failed = False
    for case in baseline:
        for metric in ("median_seconds", "peak_rss_bytes"):
            reference = baseline[case][metric]
            current = candidate[case][metric]
            ratio = current / reference
            print(
                f"{case} points {metric}: baseline={reference:.6g}, "
                f"candidate={current:.6g}, ratio={ratio:.3f}"
            )
            if ratio > args.max_ratio:
                failed = True
    if failed:
        print(f"performance regression exceeds {args.max_ratio:.2f}x", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
