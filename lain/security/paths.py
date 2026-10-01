from __future__ import annotations

import os
from pathlib import Path

from lain.errors import ErrorCode, LainError

MAX_PATH_BYTES = 4096


def _is_within(candidate: Path, root: Path) -> bool:
    return candidate == root or root in candidate.parents


def resolve_allowed_path(
    path: str | Path,
    roots: tuple[Path, ...],
    *,
    must_exist: bool = False,
) -> Path:
    raw = os.fspath(path)
    if not isinstance(raw, str):
        raise LainError(ErrorCode.ARGUMENT_INVALID, "path must be text")
    if "\x00" in raw:
        raise LainError(ErrorCode.ARGUMENT_INVALID, "path contains NUL byte")
    if len(raw.encode("utf-8")) > MAX_PATH_BYTES:
        raise LainError(ErrorCode.ARGUMENT_INVALID, "path exceeds maximum length")
    if not roots:
        raise LainError(ErrorCode.PATH_OUTSIDE_ALLOWED_ROOT, "no filesystem roots are allowed")

    normalized_roots = tuple(Path(root).expanduser().resolve() for root in roots)
    candidate_input = Path(raw).expanduser()
    if not candidate_input.is_absolute():
        candidate_input = normalized_roots[0] / candidate_input
    try:
        candidate = candidate_input.resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        raise LainError(ErrorCode.ARGUMENT_INVALID, "path could not be resolved") from exc

    if not any(_is_within(candidate, root) for root in normalized_roots):
        raise LainError(
            ErrorCode.PATH_OUTSIDE_ALLOWED_ROOT,
            "path is outside configured filesystem roots",
        )
    if must_exist and not candidate.exists():
        raise LainError(ErrorCode.SOURCE_NOT_FOUND, "source path does not exist")
    return candidate
