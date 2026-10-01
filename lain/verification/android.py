from __future__ import annotations

from lain.execution.models import ExecutionOutcome
from lain.protocol.models import ActionStatus, VerificationResult, VerificationStatus


def verify_android_command(outcome: ExecutionOutcome) -> VerificationResult:
    if outcome.status is ActionStatus.SUCCESS:
        return VerificationResult(
            VerificationStatus.LIMITED,
            {"reason": "Android accepted the adapter command; downstream UI state is not observable"},
        )
    return VerificationResult(
        VerificationStatus.NOT_APPLICABLE,
        {"reason": "Android command did not execute successfully"},
    )
