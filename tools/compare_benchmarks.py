#!/usr/bin/env python3
"""Compare candidate GCRANSAC results and resource usage with a baseline."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path


def results_match(
    reference: dict[str, object],
    current: dict[str, object],
    *,
    relative_tolerance: float,
    absolute_tolerance: float,
) -> bool:
    if reference["inliers"] != current["inliers"]:
        return False
    if reference["iterations"] != current["iterations"]:
        return False
    if not math.isclose(
        float(reference["score"]),
        float(current["score"]),
        rel_tol=relative_tolerance,
        abs_tol=absolute_tolerance,
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
                rel_tol=relative_tolerance,
                abs_tol=absolute_tolerance,
            )
            for reference_value, current_value in zip(reference_row, current_row)
        )
        for reference_row, current_row in zip(reference_model, current_model)
    )


def compare_quality(
    case: str,
    reference: dict[str, object],
    current: dict[str, object],
    *,
    max_rmse_ratio: float,
    max_rmse_increase: float,
    max_precision_drop: float,
    max_recall_drop: float,
    min_inlier_precision: float,
    min_inlier_recall: float,
    max_reprojection_rmse: float,
) -> bool:
    required_metrics = (
        "inlier_precision",
        "inlier_recall",
        "reprojection_rmse",
    )
    if any(metric not in reference or metric not in current for metric in required_metrics):
        print(f"{case} quality: required metrics are missing")
        return False

    reference_precision = float(reference["inlier_precision"])
    current_precision = float(current["inlier_precision"])
    reference_recall = float(reference["inlier_recall"])
    current_recall = float(current["inlier_recall"])
    reference_rmse = float(reference["reprojection_rmse"])
    current_rmse = float(current["reprojection_rmse"])
    if reference_rmse > 0:
        rmse_ratio = current_rmse / reference_rmse
    else:
        rmse_ratio = 1.0 if current_rmse == 0 else math.inf
    rmse_limit = max(
        reference_rmse * max_rmse_ratio,
        reference_rmse + max_rmse_increase,
    )

    case_label = f"{case} points" if case.isdigit() else case
    print(
        f"{case_label} inlier_precision: baseline={reference_precision:.6g}, "
        f"candidate={current_precision:.6g}, "
        f"delta={current_precision - reference_precision:+.3g}, "
        f"floor={min_inlier_precision:.6g}"
    )
    print(
        f"{case_label} inlier_recall: baseline={reference_recall:.6g}, "
        f"candidate={current_recall:.6g}, "
        f"delta={current_recall - reference_recall:+.3g}, "
        f"floor={min_inlier_recall:.6g}"
    )
    print(
        f"{case_label} reprojection_rmse: baseline={reference_rmse:.6g}, "
        f"candidate={current_rmse:.6g}, ratio={rmse_ratio:.3f}, "
        f"relative_limit={rmse_limit:.6g}, absolute_limit={max_reprojection_rmse:.6g}"
    )

    return all(
        math.isfinite(value)
        for value in (
            reference_precision,
            current_precision,
            reference_recall,
            current_recall,
            reference_rmse,
            current_rmse,
        )
    ) and (
        current_precision >= reference_precision - max_precision_drop
        and current_recall >= reference_recall - max_recall_drop
        and current_rmse <= rmse_limit
        and current_precision >= min_inlier_precision
        and current_recall >= min_inlier_recall
        and current_rmse <= max_reprojection_rmse
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--max-ratio", type=float, default=1.25)
    parser.add_argument("--relative-tolerance", type=float, default=1e-10)
    parser.add_argument("--absolute-tolerance", type=float, default=1e-10)
    parser.add_argument("--max-rmse-ratio", type=float, default=1.10)
    parser.add_argument("--max-rmse-increase", type=float, default=0.05)
    parser.add_argument("--max-precision-drop", type=float, default=0.005)
    parser.add_argument("--max-recall-drop", type=float, default=0.005)
    parser.add_argument("--min-inlier-precision", type=float, default=0.0)
    parser.add_argument("--min-inlier-recall", type=float, default=0.0)
    parser.add_argument("--max-reprojection-rmse", type=float, default=math.inf)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--results-only", action="store_true")
    mode.add_argument("--quality-only", action="store_true")
    mode.add_argument("--performance-only", action="store_true")
    args = parser.parse_args()

    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))["cases"]
    candidate = json.loads(args.candidate.read_text(encoding="utf-8"))["cases"]
    if baseline.keys() != candidate.keys():
        print("benchmark cases do not match", file=sys.stderr)
        return 1

    results_failed = False
    quality_failed = False
    performance_failed = False
    for case in baseline:
        case_label = f"{case} points" if case.isdigit() else case
        if not args.performance_only and not args.quality_only:
            if not results_match(
                baseline[case]["result"],
                candidate[case]["result"],
                relative_tolerance=args.relative_tolerance,
                absolute_tolerance=args.absolute_tolerance,
            ):
                print(f"{case_label} result: candidate differs from baseline")
                results_failed = True
            else:
                print(f"{case_label} result: equivalent")

        if args.quality_only and not compare_quality(
            case,
            baseline[case].get("quality", {}),
            candidate[case].get("quality", {}),
            max_rmse_ratio=args.max_rmse_ratio,
            max_rmse_increase=args.max_rmse_increase,
            max_precision_drop=args.max_precision_drop,
            max_recall_drop=args.max_recall_drop,
            min_inlier_precision=args.min_inlier_precision,
            min_inlier_recall=args.min_inlier_recall,
            max_reprojection_rmse=args.max_reprojection_rmse,
        ):
            quality_failed = True

        if not args.results_only and not args.quality_only:
            for metric in ("median_seconds", "peak_rss_bytes"):
                reference = baseline[case][metric]
                current = candidate[case][metric]
                ratio = current / reference
                print(
                    f"{case_label} {metric}: baseline={reference:.6g}, "
                    f"candidate={current:.6g}, ratio={ratio:.3f}"
                )
                if ratio > args.max_ratio:
                    performance_failed = True
    if results_failed:
        print("benchmark results differ from the baseline", file=sys.stderr)
    if quality_failed:
        print("benchmark quality regressed from the baseline", file=sys.stderr)
    if performance_failed:
        print(f"performance regression exceeds {args.max_ratio:.2f}x", file=sys.stderr)
    if results_failed or quality_failed or performance_failed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
