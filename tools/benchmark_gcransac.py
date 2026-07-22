#!/usr/bin/env python3
"""Benchmark the public GCRANSAC homography path in an isolated environment."""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import statistics
import sys
import time
from pathlib import Path

import numpy as np
import pysuperansac

if os.name != "nt":
    import resource


def make_case(point_count: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    source = rng.uniform([50.0, 50.0], [1820.0, 1000.0], (point_count, 2))
    matrix = np.array(
        [[1.005, 0.008, 18.0], [-0.006, 0.997, 24.0], [4e-6, -7e-6, 1.0]],
        dtype=np.float64,
    )
    homogeneous = np.column_stack((source, np.ones(point_count))) @ matrix.T
    destination = homogeneous[:, :2] / homogeneous[:, 2:]
    destination += rng.normal(0.0, 0.2, destination.shape)
    outliers = rng.choice(point_count, point_count // 4, replace=False)
    destination[outliers] = rng.uniform([0.0, 0.0], [1920.0, 1080.0], (len(outliers), 2))
    return (
        np.ascontiguousarray(np.column_stack((source, destination)), dtype=np.float64),
        np.array([1920.0, 1080.0, 1920.0, 1080.0], dtype=np.float64),
    )


def settings() -> pysuperansac.RANSACSettings:
    result = pysuperansac.RANSACSettings()
    result.min_iterations = 100
    result.max_iterations = 500
    result.inlier_threshold = 2.0
    result.confidence = 0.999
    result.scoring = pysuperansac.ScoringType.MSAC
    result.sampler = pysuperansac.SamplerType.Uniform
    result.neighborhood = pysuperansac.NeighborhoodType.Grid
    result.local_optimization = pysuperansac.LocalOptimizationType.GCRANSAC
    result.final_optimization = pysuperansac.LocalOptimizationType.LSQ
    result.local_opt_k = 1
    result.use_sprt = False
    return result


def peak_rss_bytes() -> int:
    if os.name == "nt":
        from ctypes import wintypes

        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.c_ulong),
                ("PageFaultCount", ctypes.c_ulong),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel32.GetCurrentProcess.argtypes = []
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(ProcessMemoryCounters),
            wintypes.DWORD,
        ]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL

        process = kernel32.GetCurrentProcess()
        if not psapi.GetProcessMemoryInfo(process, ctypes.byref(counters), counters.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return int(counters.PeakWorkingSetSize)

    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(peak if sys.platform == "darwin" else peak * 1024)


def measured_call(
    correspondences: np.ndarray, image_sizes: np.ndarray
) -> tuple[float, int, tuple[object, object, object, object]]:
    started = time.perf_counter()
    result = pysuperansac.estimateHomography(correspondences, image_sizes, None, settings())
    elapsed = time.perf_counter() - started
    if not np.isfinite(np.asarray(result[0])).all():
        raise RuntimeError("benchmark produced a non-finite homography")
    return elapsed, peak_rss_bytes(), result


def result_payload(result: tuple[object, object, object, object]) -> dict[str, object]:
    model = np.asarray(result[0], dtype=np.float64)
    scale = model[-1, -1]
    if abs(scale) > np.finfo(np.float64).eps:
        model = model / scale
    return {
        "model": model.tolist(),
        "inliers": np.asarray(result[1], dtype=np.int64).tolist(),
        "score": float(result[2]),
        "iterations": int(result[3]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sizes", default="1000,5000")
    parser.add_argument("--warmups", type=int, default=3)
    parser.add_argument("--repetitions", type=int, default=10)
    args = parser.parse_args()

    cases: dict[str, dict[str, float | int]] = {}
    for point_count in (int(value) for value in args.sizes.split(",")):
        correspondences, image_sizes = make_case(point_count, seed=0xB00 + point_count)
        for _ in range(args.warmups):
            pysuperansac.estimateHomography(correspondences, image_sizes, None, settings())
        measurements = [
            measured_call(correspondences, image_sizes) for _ in range(args.repetitions)
        ]
        cases[str(point_count)] = {
            "median_seconds": statistics.median(value[0] for value in measurements),
            "peak_rss_bytes": max(value[1] for value in measurements),
            "repetitions": args.repetitions,
            "result": result_payload(measurements[0][2]),
        }

    payload = {
        "module": str(Path(pysuperansac.__file__).resolve()),
        "cases": cases,
    }
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = {
        "module": payload["module"],
        "cases": {
            case: {
                "median_seconds": values["median_seconds"],
                "peak_rss_bytes": values["peak_rss_bytes"],
                "repetitions": values["repetitions"],
                "inlier_count": len(values["result"]["inliers"]),
                "score": values["result"]["score"],
                "iterations": values["result"]["iterations"],
            }
            for case, values in cases.items()
        },
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
