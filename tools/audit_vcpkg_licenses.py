#!/usr/bin/env python3
"""Ensure every target vcpkg package is covered by the wheel notices."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

LICENSE_PATTERNS = (
    (re.compile(r"eigen3$"), "MPL-2.0.txt"),
    (re.compile(r"opencv4$"), "Apache-2.0.txt"),
    (re.compile(r"zlib$"), "Zlib.txt"),
)


def installed_ports(info_directory: Path, triplet: str) -> set[str]:
    ports: set[str] = set()
    for entry in info_directory.glob(f"*_{triplet}.list"):
        # vcpkg list names are <port>_<version>_<triplet>.list. The version
        # starts with a digit, so this also handles hyphens in port names.
        match = re.match(r"(.+?)_[0-9]", entry.name)
        if match:
            ports.add(match.group(1))
    return ports


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("installed_root", type=Path)
    parser.add_argument("--triplet", required=True)
    parser.add_argument(
        "--licenses",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "THIRD_PARTY_LICENSES",
    )
    args = parser.parse_args()

    info = args.installed_root / "vcpkg" / "info"
    if not info.is_dir():
        print(f"vcpkg license audit failed: missing {info}", file=sys.stderr)
        return 1

    ports = installed_ports(info, args.triplet)
    ignored_host_helpers = {"vcpkg-cmake", "vcpkg-cmake-config", "vcpkg-get-python-packages"}
    unknown: list[str] = []
    covered: dict[str, str] = {}
    for port in sorted(ports - ignored_host_helpers):
        for pattern, license_name in LICENSE_PATTERNS:
            if pattern.fullmatch(port) or pattern.match(port):
                if not (args.licenses / license_name).is_file():
                    print(
                        f"vcpkg license audit failed: missing {license_name} for {port}",
                        file=sys.stderr,
                    )
                    return 1
                covered[port] = license_name
                break
        else:
            unknown.append(port)

    if unknown:
        print(
            "vcpkg license audit failed: add these resolved ports to "
            f"THIRD_PARTY_NOTICES.md and this audit: {unknown}",
            file=sys.stderr,
        )
        return 1
    if not {"eigen3", "opencv4", "zlib"}.issubset(ports):
        print(
            f"vcpkg license audit failed: incomplete dependency set: {sorted(ports)}",
            file=sys.stderr,
        )
        return 1

    print("vcpkg license audit passed:")
    for port, license_name in covered.items():
        print(f"  {port}: {license_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
