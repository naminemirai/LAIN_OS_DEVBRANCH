#!/usr/bin/env python3
"""Non-destructive Android/Termux environment and test-suite smoke check."""

from __future__ import annotations

import importlib.util
import platform
import shutil
import sys
from collections.abc import Callable
from pathlib import Path

if __package__:
    from . import verify
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts import verify

Which = Callable[[str], str | None]
TERMUX_COMMANDS = ("termux-notification", "termux-open-url", "am")


def main(*, which: Which = shutil.which) -> int:
    print(f"Python: {sys.version.split()[0]}")
    print(f"Platform: {platform.platform()}")
    importable = importlib.util.find_spec("lain") is not None
    print(f"LAIN importable: {'yes' if importable else 'no'}")
    if not importable:
        return 1
    print("Termux/Android commands (informational; absence is expected on ordinary Linux):")
    for command in TERMUX_COMMANDS:
        print(f"  {command}: {which(command) or 'unavailable'}")
    print("No device actions are performed by this helper.")
    return verify.main()


if __name__ == "__main__":
    raise SystemExit(main())
