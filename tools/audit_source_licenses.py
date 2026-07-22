#!/usr/bin/env python3
"""Prevent removed restricted graph-cut sources from returning unnoticed."""

from __future__ import annotations

import sys
from pathlib import Path

from license_policy import REMOVED_GRAPH_CUT_FILES, RESTRICTED_LICENSE_PHRASES

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    local_optimization = ROOT / "include" / "local_optimization"
    returned = sorted(
        path.name
        for path in local_optimization.iterdir()
        if path.name in REMOVED_GRAPH_CUT_FILES
    )
    violations: list[str] = []
    for source_root in (ROOT / "include", ROOT / "src", ROOT / "python"):
        for path in source_root.rglob("*"):
            if not path.is_file():
                continue
            contents = path.read_bytes().lower()
            for phrase in RESTRICTED_LICENSE_PHRASES:
                if phrase in contents:
                    violations.append(
                        f"{path.relative_to(ROOT)} contains {phrase.decode('ascii')!r}"
                    )

    if returned or violations:
        if returned:
            print(f"removed restricted source files returned: {returned}", file=sys.stderr)
        for violation in violations:
            print(violation, file=sys.stderr)
        return 1
    print("source license audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
