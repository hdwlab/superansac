#!/usr/bin/env python3
"""Compare candidate GCRANSAC results and resource usage with a baseline."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path


def results_match(reference: dict[str, object], current: dict[str, object]) -> bool:
    if reference["inliers"] != current["inliers"]:
        return False
    if reference["iterations"] != current["iterations"]:
        return False
    if not math.isclose(
        float(reference["score"]),
        float(current["score"]),
        rel_tol=1e-10,
        abs_tol=1e-10,
    ):
        return False
    reference_model = reference["model"]
    current_model = current["model"]
    if not isinstance(reference_model, list) or not isinstance(current_model, list):
        return False
    if len(reference_model) != len(current_model):
        return False
    return all(
        len(reference_row) == len(current_row)
        and all(
            math.isclose(
                float(reference_value),
                float(current_value),
                rel_tol=1e-10,
                abs_tol=1e-10,
            )
            for reference_value, current_value in zip(reference_row, current_row)
        )
        for reference_row, current_row in zip(reference_model, current_model)
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--max-ratio", type=float, default=1.25)
    parser.add_argument("--results-only", action="store_true")
    args = parser.parse_args()

    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))["cases"]
    candidate = json.loads(args.candidate.read_text(encoding="utf-8"))["cases"]
    if baseline.keys() != candidate.keys():
        print("benchmark cases do not match", file=sys.stderr)
        return 1

    results_failed = False
    performance_failed = False
    for case in baseline:
        if not results_match(baseline[case]["result"], candidate[case]["result"]):
            print(f"{case} points result: candidate differs from baseline")
            results_failed = True
        else:
            print(f"{case} points result: equivalent")
        for metric in ("median_seconds", "peak_rss_bytes"):
            reference = baseline[case][metric]
            current = candidate[case][metric]
            ratio = current / reference
            print(
                f"{case} points {metric}: baseline={reference:.6g}, "
                f"candidate={current:.6g}, ratio={ratio:.3f}"
            )
            if not args.results_only and ratio > args.max_ratio:
                performance_failed = True
    if results_failed:
        print("benchmark results differ from the baseline", file=sys.stderr)
    if performance_failed:
        print(f"performance regression exceeds {args.max_ratio:.2f}x", file=sys.stderr)
    if results_failed or performance_failed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
