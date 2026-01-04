from __future__ import annotations

import re
import sys
from pathlib import Path

TOTAL_RE = re.compile(r"TOTAL\s+\d+\s+\d+\s+(?P<cover>\d+%?)")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: coverage_summary.py <coverage_output.txt>")
    path = Path(sys.argv[1])
    if not path.exists():
        raise SystemExit(f"Coverage output not found: {path}")
    cover = None
    lines = path.read_text(encoding="utf-8").splitlines()
    for line in lines:
        match = TOTAL_RE.search(line)
        if match:
            cover = match.group("cover")
            break
    if not cover:
        for line in lines:
            if line.strip().startswith("TOTAL"):
                parts = line.strip().split()
                if len(parts) >= 4:
                    cover = parts[3]
                    break
    if not cover:
        raise SystemExit(f"Coverage total not found in output: {path}")
    print("**Code Coverage**")
    print()
    print(f"- Total coverage: {cover}")


if __name__ == "__main__":
    main()
