from __future__ import annotations

from pathlib import Path

from lain.execution.filesystem import sha256_file
from lain.execution.models import ExecutionOutcome
from lain.protocol.models import ActionStatus, VerificationResult, VerificationStatus


def _failed(reason: str) -> VerificationResult:
    return VerificationResult(VerificationStatus.FAILED, {"reason": reason})


def _not_applicable(outcome: ExecutionOutcome) -> VerificationResult:
    return VerificationResult(
        VerificationStatus.NOT_APPLICABLE,
        {"reason": "execution did not succeed", "execution_status": outcome.status.value},
    )


def verify_file_write_text(outcome: ExecutionOutcome) -> VerificationResult:
    if outcome.status is not ActionStatus.SUCCESS:
        return _not_applicable(outcome)
    path = Path(outcome.details["path"])
    try:
        if not path.is_file():
            return _failed("destination missing")
        actual_hash = sha256_file(path)
        if actual_hash != outcome.details["sha256"]:
            return _failed("content hash mismatch")
        if path.stat().st_size != outcome.details["size"]:
            return _failed("content size mismatch")
        return VerificationResult(VerificationStatus.PASSED, {"sha256": actual_hash})
    except OSError as exc:
        return _failed(f"verification error: {type(exc).__name__}")


def verify_file_copy(outcome: ExecutionOutcome) -> VerificationResult:
    if outcome.status is not ActionStatus.SUCCESS:
        return _not_applicable(outcome)
    destination = Path(outcome.details["destination"])
    try:
        if not destination.is_file():
            return _failed("destination missing")
        actual_hash = sha256_file(destination)
        if actual_hash != outcome.details["sha256_before"]:
            return _failed("destination hash mismatch")
        return VerificationResult(VerificationStatus.PASSED, {"sha256": actual_hash})
    except OSError as exc:
        return _failed(f"verification error: {type(exc).__name__}")


def verify_file_move(outcome: ExecutionOutcome) -> VerificationResult:
    if outcome.status is not ActionStatus.SUCCESS:
        return _not_applicable(outcome)
    source = Path(outcome.details["source"])
    destination = Path(outcome.details["destination"])
    try:
        if source.exists():
            return _failed("source still exists")
        if not destination.is_file():
            return _failed("destination missing")
        actual_hash = sha256_file(destination)
        if actual_hash != outcome.details["sha256_before"]:
            return _failed("destination hash mismatch")
        return VerificationResult(VerificationStatus.PASSED, {"sha256": actual_hash})
    except OSError as exc:
        return _failed(f"verification error: {type(exc).__name__}")
