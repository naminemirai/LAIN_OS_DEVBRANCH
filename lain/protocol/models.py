from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ActionStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"
    CONFIRMATION_REQUIRED = "confirmation_required"
    UNSUPPORTED = "unsupported"
    SKIPPED = "skipped"


class VerificationStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    NOT_APPLICABLE = "not_applicable"
    LIMITED = "limited"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class Action:
    id: str
    type: str
    arguments: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ActionEnvelope:
    version: str
    request_id: str
    intent: str
    actions: tuple[Action, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "request_id": self.request_id,
            "intent": self.intent,
            "actions": [
                {"id": action.id, "type": action.type, "arguments": dict(action.arguments)}
                for action in self.actions
            ],
        }


@dataclass(frozen=True, slots=True)
class VerificationResult:
    status: VerificationStatus
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"status": self.status.value, "details": dict(self.details)}


@dataclass(frozen=True, slots=True)
class ActionResult:
    action_id: str
    status: ActionStatus
    details: dict[str, Any] = field(default_factory=dict)
    verification: VerificationResult = field(
        default_factory=lambda: VerificationResult(VerificationStatus.NOT_APPLICABLE)
    )
    error_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "action_id": self.action_id,
            "status": self.status.value,
            "details": dict(self.details),
            "verification": self.verification.to_dict(),
        }
        if self.error_code is not None:
            data["error_code"] = self.error_code
        return data


@dataclass(frozen=True, slots=True)
class ResultEnvelope:
    version: str
    request_id: str
    intent: str
    results: tuple[ActionResult, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "request_id": self.request_id,
            "intent": self.intent,
            "results": [result.to_dict() for result in self.results],
        }
