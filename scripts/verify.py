#!/usr/bin/env python3
"""Run the canonical, portable LAIN_OS developer verification suite."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
Runner = Callable[..., subprocess.CompletedProcess[str]]
COMMANDS = (
    (sys.executable, "-m", "compileall", "-q", "lain"),
    (sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"),
    ("git", "diff", "--cached", "--check"),
    ("git", "diff", "--check"),
)
SECURITY_PATTERNS = tuple(
    re.compile(pattern)
    for pattern in (r"shell\s*=\s*True", r"os\.system\s*\(", r"\beval\s*\(", r"\bexec\s*\(")
)
STALE_NAMES = ("L" + ".A.I.N", "loopmother/" + "L.A.I.N")


def _tracked_files(root: Path, runner: Runner) -> list[Path]:
    result = runner(["git", "ls-files", "-z"], cwd=root, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError("git ls-files failed")
    return [root / name for name in result.stdout.split("\0") if name]


def scan_repository(root: Path = ROOT, runner: Runner = subprocess.run) -> list[str]:
    """Return actionable security and stale-name violations in tracked files."""
    violations: list[str] = []
    for path in _tracked_files(root, runner):
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        relative = path.relative_to(root).as_posix()
        # Tests/docs intentionally name forbidden APIs; runtime source must not use them.
        if relative.startswith("lain/") and path.suffix == ".py":
            for number, line in enumerate(content.splitlines(), 1):
                if any(pattern.search(line) for pattern in SECURITY_PATTERNS):
                    violations.append(f"{relative}:{number}: forbidden execution pattern")
        if relative != "scripts/verify.py":
            for number, line in enumerate(content.splitlines(), 1):
                if any(name in line for name in STALE_NAMES):
                    violations.append(f"{relative}:{number}: stale project naming")
    return violations


def main(
    *, root: Path = ROOT, runner: Runner = subprocess.run, diff_range: str | None = None
) -> int:
    commands = list(COMMANDS)
    if diff_range:
        commands.append(("git", "diff", "--check", diff_range))
    for command in commands:
        rendered = " ".join(("python", *command[2:])) if command[0] == sys.executable else " ".join(command)
        print(f"==> {rendered}", flush=True)
        result = runner(list(command), cwd=root, check=False)
        if result.returncode:
            print(f"FAILED ({result.returncode}): {rendered}", file=sys.stderr)
            return result.returncode or 1
    print("==> security and stale naming scans", flush=True)
    try:
        violations = scan_repository(root, runner)
    except RuntimeError as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    if violations:
        print("\n".join(violations), file=sys.stderr)
        print("FAILED: repository scan", file=sys.stderr)
        return 1
    print("Verification passed.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--diff-range",
        help="also check whitespace in the specified committed Git range (for example BASE..HEAD)",
    )
    raise SystemExit(main(diff_range=parser.parse_args().diff_range))
