#!/usr/bin/env python3
"""Validate dumpbin /DEPENDENTS output for a statically linked wheel."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

ALLOWED = (
    re.compile(r"python3(?:10|11|12)\.dll", re.IGNORECASE),
    re.compile(r"kernel32\.dll", re.IGNORECASE),
    re.compile(r"msvcp140(?:_[0-9]+)?\.dll", re.IGNORECASE),
    re.compile(r"concrt140\.dll", re.IGNORECASE),
    re.compile(r"vcruntime140(?:_[0-9]+)?\.dll", re.IGNORECASE),
    re.compile(r"api-ms-win-crt-[a-z0-9-]+\.dll", re.IGNORECASE),
)
DLL_LINE = re.compile(r"^\s*([A-Za-z0-9_.+-]+\.dll)\s*$", re.IGNORECASE)
FORBIDDEN_VENDOR_DLL = re.compile(r"^(?:opencv|boost).+\.dll$", re.IGNORECASE)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dumpbin_output", type=Path)
    args = parser.parse_args()

    dependencies = {
        match.group(1)
        for line in args.dumpbin_output.read_text(encoding="utf-8", errors="replace").splitlines()
        if (match := DLL_LINE.match(line))
    }
    system_directory = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
    unexpected = []
    for dependency in sorted(dependencies):
        if FORBIDDEN_VENDOR_DLL.fullmatch(dependency):
            unexpected.append(dependency)
            continue
        if any(pattern.fullmatch(dependency) for pattern in ALLOWED):
            continue
        if (system_directory / dependency).is_file():
            continue
        unexpected.append(dependency)
    if unexpected:
        print(f"unexpected non-system DLL dependencies: {unexpected}", file=sys.stderr)
        return 1
    if not any(dependency.lower().startswith("python3") for dependency in dependencies):
        print(
            f"Python DLL was not found in dumpbin output: {sorted(dependencies)}", file=sys.stderr
        )
        return 1
    print(f"Windows dependency audit passed: {sorted(dependencies)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
