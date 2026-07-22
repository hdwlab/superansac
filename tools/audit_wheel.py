#!/usr/bin/env python3
"""Audit a pysuperansac wheel without importing it."""

from __future__ import annotations

import argparse
import re
import sys
from email.parser import BytesParser
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

REQUIRED_LICENSES = {
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "Apache-2.0.txt",
    "BSD-2-Clause.txt",
    "BSD-3-Clause.txt",
    "MPL-2.0.txt",
    "Zlib.txt",
}
EXPECTED_LICENSE_EXPRESSION = (
    "MIT AND BSD-2-Clause AND BSD-3-Clause AND MPL-2.0 AND Apache-2.0 AND Zlib"
)
FORBIDDEN_BINARY_FRAGMENTS = (
    b"c:\\users\\runneradmin",
    b"c:/users/runneradmin",
    b"d:\\a\\",
    b"d:/a/",
    b"vcpkg\\buildtrees",
    b"vcpkg/buildtrees",
    b"hostedtoolcache",
    b"appdata\\local\\temp",
    b"appdata/local/temp",
    b"github\\workspace",
    b"github/workspace",
    b"research purposes only",
    b"gcoptimization",
)


def fail(message: str) -> None:
    raise RuntimeError(message)


def audit(wheel: Path, platform: str) -> None:
    expected_suffix = "win_amd64.whl" if platform == "windows" else "linux_x86_64.whl"
    if not wheel.name.endswith(expected_suffix):
        fail(f"unexpected wheel platform tag: {wheel.name}")

    with ZipFile(wheel) as archive:
        names = archive.namelist()
        metadata_names = [name for name in names if name.endswith(".dist-info/METADATA")]
        if len(metadata_names) != 1:
            fail(f"expected one METADATA file, found {metadata_names}")

        metadata = BytesParser().parsebytes(archive.read(metadata_names[0]))
        if metadata["Name"] != "pysuperansac":
            fail(f"unexpected distribution name: {metadata['Name']!r}")
        requires_python = (metadata["Requires-Python"] or "").replace(" ", "")
        if set(requires_python.split(",")) != {">=3.10", "<3.13"}:
            fail(f"unexpected Requires-Python: {metadata['Requires-Python']!r}")
        requirements = metadata.get_all("Requires-Dist", [])
        if not any(re.match(r"numpy\s*[<(]", requirement) for requirement in requirements):
            fail(f"NumPy runtime dependency is missing: {requirements}")
        expression = metadata["License-Expression"] or ""
        if expression != EXPECTED_LICENSE_EXPRESSION:
            fail(f"unexpected License-Expression: {expression!r}")

        urls = metadata.get_all("Project-URL", [])
        if not any("https://github.com/hdwlab/superansac" in url for url in urls):
            fail(f"fork project URL is missing: {urls}")

        included_license_names = {
            PurePosixPath(name).name for name in names if ".dist-info/licenses/" in name
        }
        missing_licenses = REQUIRED_LICENSES - included_license_names
        if missing_licenses:
            fail(f"wheel is missing license files: {sorted(missing_licenses)}")
        unexpected_licenses = included_license_names - REQUIRED_LICENSES
        if unexpected_licenses:
            fail(f"wheel has undeclared license files: {sorted(unexpected_licenses)}")

        extension_suffix = ".pyd" if platform == "windows" else ".so"
        extension_names = [
            name
            for name in names
            if PurePosixPath(name).name.startswith("pysuperansac")
            and name.endswith(extension_suffix)
        ]
        if len(extension_names) != 1:
            fail(f"expected one Python extension, found {extension_names}")

        forbidden_suffixes = (".lib", ".a", ".pdb", ".h", ".hpp")
        forbidden_files = [name for name in names if name.lower().endswith(forbidden_suffixes)]
        if forbidden_files:
            fail(f"wheel contains build-only files: {forbidden_files}")

        if platform == "windows":
            dynamic_libraries = [name for name in names if name.lower().endswith(".dll")]
            if dynamic_libraries:
                fail(f"Windows wheel unexpectedly contains DLLs: {dynamic_libraries}")

        binary_names = [name for name in names if name.lower().endswith((".pyd", ".dll", ".so"))]
        for name in binary_names:
            lowered = archive.read(name).lower()
            found = [
                fragment.decode("ascii", errors="replace")
                for fragment in FORBIDDEN_BINARY_FRAGMENTS
                if fragment in lowered
            ]
            if found:
                fail(f"{name} contains forbidden build/license strings: {found}")

    print(f"wheel audit passed: {wheel}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--platform", choices=("windows", "linux"), required=True)
    args = parser.parse_args()
    try:
        audit(args.wheel, args.platform)
    except (OSError, RuntimeError) as error:
        print(f"wheel audit failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
