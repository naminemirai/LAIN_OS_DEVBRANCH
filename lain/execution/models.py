from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from lain.protocol.models import ActionStatus


@dataclass(frozen=True, slots=True)
class ExecutionOutcome:
    status: ActionStatus
    details: dict[str, Any] = field(default_factory=dict)
    error_code: str | None = None

    @classmethod
    def success(cls, **details: Any) -> "ExecutionOutcome":
        return cls(ActionStatus.SUCCESS, details)

    @classmethod
    def failure(cls, error_code: str, message: str, **details: Any) -> "ExecutionOutcome":
        payload = {"message": message, **details}
        return cls(ActionStatus.FAILURE, payload, error_code)

    @classmethod
    def unsupported(cls, error_code: str, message: str, **details: Any) -> "ExecutionOutcome":
        payload = {"message": message, **details}
        return cls(ActionStatus.UNSUPPORTED, payload, error_code)
