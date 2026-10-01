from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from time import monotonic
from typing import Any

from lain.audit.logger import AuditLogger, redact
from lain.capabilities.registry import CapabilityDefinition, CapabilityRegistry, DEFAULT_REGISTRY, RiskClass
from lain.config import RuntimeConfig
from lain.errors import ErrorCode, LainError
from lain.execution.android import (
    execute_android_notify, execute_android_open_uri, validate_android_uri,
    execute_android_battery_status, execute_android_vibrate, execute_android_toast,
    execute_android_clipboard_set, execute_android_share_text,
)
from lain.execution.filesystem import execute_file_copy, execute_file_move, execute_file_write_text
from lain.execution.models import ExecutionOutcome
from lain.policy.engine import PolicyDecision, evaluate_policy
from lain.protocol.models import (
    Action,
    ActionEnvelope,
    ActionResult,
    ActionStatus,
    ResultEnvelope,
    VerificationResult,
    VerificationStatus,
)
from lain.security.paths import resolve_allowed_path
from lain.verification.android import verify_android_command, verify_android_expansion
from lain.verification.filesystem import verify_file_copy, verify_file_move, verify_file_write_text
from lain.integrations.reddit import RedditClient


class RuntimeEngine:
    def __init__(
        self,
        config: RuntimeConfig,
        *,
        registry: CapabilityRegistry = DEFAULT_REGISTRY,
        audit: AuditLogger | None = None,
        reddit_client: RedditClient | None = None,
    ):
        self.config = config
        self.registry = registry
        self.audit = audit or AuditLogger(config.audit_path)
        self.reddit_client = reddit_client

    def preflight(self, envelope: ActionEnvelope) -> tuple[tuple[Action, CapabilityDefinition], ...]:
        if len(envelope.actions) > self.config.max_actions:
            raise LainError(ErrorCode.PROTOCOL_INVALID, "too many actions")
        prepared: list[tuple[Action, CapabilityDefinition]] = []
        for action in envelope.actions:
            capability = self.registry.get(action.type)
            normalized = capability.validate_arguments(action.arguments)
            if "overwrite" in capability.arguments and "overwrite" not in action.arguments:
                normalized["overwrite"] = self.config.overwrite_default
            if action.type == "file.write_text":
                resolve_allowed_path(normalized["path"], self.config.allowed_roots)
                if len(normalized["content"].encode("utf-8")) > self.config.max_text_write_bytes:
                    raise LainError(
                        ErrorCode.ARGUMENT_INVALID,
                        "text write exceeds configured byte limit",
                        details={"limit": self.config.max_text_write_bytes},
                    )
            elif action.type in {"file.copy", "file.move"}:
                resolve_allowed_path(normalized["source"], self.config.allowed_roots)
                resolve_allowed_path(normalized["destination"], self.config.allowed_roots)
            elif action.type == "android.open_uri":
                validate_android_uri(normalized["uri"])
            elif action.type == "reddit.create_post":
                if not normalized["subreddit"] or not normalized["title"] or not normalized["body"]:
                    raise LainError(ErrorCode.ARGUMENT_INVALID, "Reddit arguments must not be empty")
            prepared.append((replace(action, arguments=normalized), capability))
        return tuple(prepared)

    def execute(
        self,
        envelope: ActionEnvelope,
        *,
        confirmed_action_ids: frozenset[str] = frozenset(),
    ) -> ResultEnvelope:
        if self.audit.has_executed_request(envelope.request_id):
            raise LainError(
                ErrorCode.DUPLICATE_REQUEST,
                "request_id has already attempted execution",
                details={"request_id": envelope.request_id},
            )

        prepared = self.preflight(envelope)
        results: list[ActionResult] = []
        for action, capability in prepared:
            result = self._execute_prepared_action(
                envelope,
                action,
                capability,
                confirmed_action_ids=confirmed_action_ids,
            )
            results.append(result)
            if result.status is not ActionStatus.SUCCESS:
                break

        return ResultEnvelope(envelope.version, envelope.request_id, envelope.intent, tuple(results))

    def execute_action(
        self,
        envelope: ActionEnvelope,
        action_id: str,
        *,
        confirmed_action_ids: frozenset[str] = frozenset(),
    ) -> ActionResult:
        prepared = self.preflight(envelope)
        selected = next(((action, capability) for action, capability in prepared if action.id == action_id), None)
        if selected is None:
            raise LainError(
                ErrorCode.ARGUMENT_INVALID,
                "action_id is not present in request",
                details={"action_id": action_id},
            )
        if self.audit.has_executed_action(envelope.request_id, action_id):
            raise LainError(
                ErrorCode.DUPLICATE_REQUEST,
                "request action has already attempted execution",
                details={"request_id": envelope.request_id, "action_id": action_id},
            )
        action, capability = selected
        return self._execute_prepared_action(
            envelope,
            action,
            capability,
            confirmed_action_ids=confirmed_action_ids,
        )

    def _execute_prepared_action(
        self,
        envelope: ActionEnvelope,
        action: Action,
        capability: CapabilityDefinition,
        *,
        confirmed_action_ids: frozenset[str],
    ) -> ActionResult:
        started = monotonic()
        decision = evaluate_policy(capability, action, self.config)

        if decision is PolicyDecision.DENY:
            result = ActionResult(
                action_id=action.id,
                status=ActionStatus.DENIED,
                details={"policy": decision.value},
                verification=VerificationResult(VerificationStatus.NOT_APPLICABLE),
                error_code=ErrorCode.POLICY_DENIED.value,
            )
            self._audit_action(envelope, action, capability, decision, result, False, started)
            return result

        if decision is PolicyDecision.REQUIRE_CONFIRMATION and action.id not in confirmed_action_ids:
            result = ActionResult(
                action_id=action.id,
                status=ActionStatus.CONFIRMATION_REQUIRED,
                details={"policy": decision.value},
                verification=VerificationResult(VerificationStatus.NOT_APPLICABLE),
                error_code=ErrorCode.CONFIRMATION_REQUIRED.value,
            )
            self._audit_action(envelope, action, capability, decision, result, False, started)
            return result

        if capability.risk_class is RiskClass.EXTERNAL_WRITE:
            self._audit_external_attempt(envelope, action, capability, decision, started)
        outcome = self._execute_action(action)
        verification = self._verify_action(action, outcome)
        status = outcome.status
        error_code = outcome.error_code
        if outcome.status is ActionStatus.SUCCESS and verification.status is VerificationStatus.FAILED:
            status = ActionStatus.FAILURE
            error_code = ErrorCode.VERIFICATION_FAILED.value

        result = ActionResult(
            action_id=action.id,
            status=status,
            details=dict(outcome.details),
            verification=verification,
            error_code=error_code,
        )
        self._audit_action(envelope, action, capability, decision, result, True, started)
        return result

    def _audit_external_attempt(
        self,
        envelope: ActionEnvelope,
        action: Action,
        capability: CapabilityDefinition,
        decision: PolicyDecision,
        started: float,
    ) -> None:
        """Persist the idempotency barrier before crossing an external-write boundary."""
        self.audit.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": envelope.request_id,
                "action_id": action.id,
                "capability": capability.name,
                "risk_class": int(capability.risk_class),
                "policy_decision": decision.value,
                "arguments": redact(action.arguments),
                "execution_attempted": True,
                "execution_status": "started",
                "verification_status": VerificationStatus.NOT_APPLICABLE.value,
                "duration_ms": round((monotonic() - started) * 1000, 3),
                "error_code": None,
            }
        )

    def _execute_action(self, action: Action) -> ExecutionOutcome:
        if action.type == "file.write_text":
            return execute_file_write_text(action.arguments, self.config)
        if action.type == "file.copy":
            return execute_file_copy(action.arguments, self.config)
        if action.type == "file.move":
            return execute_file_move(action.arguments, self.config)
        if action.type == "android.notify":
            return execute_android_notify(action.arguments, self.config)
        if action.type == "android.open_uri":
            return execute_android_open_uri(action.arguments, self.config)
        if action.type == "android.battery_status":
            return execute_android_battery_status(action.arguments, self.config)
        if action.type == "android.vibrate":
            return execute_android_vibrate(action.arguments, self.config)
        if action.type == "android.toast":
            return execute_android_toast(action.arguments, self.config)
        if action.type == "android.clipboard_set":
            return execute_android_clipboard_set(action.arguments, self.config)
        if action.type == "android.share_text":
            return execute_android_share_text(action.arguments, self.config)
        if action.type == "reddit.create_post":
            try:
                client = self.reddit_client or RedditClient.from_environment()
            except LainError as exc:
                return ExecutionOutcome.failure(exc.code.value, exc.message, **exc.details)
            return client.create_post(**action.arguments)
        return ExecutionOutcome.unsupported(
            ErrorCode.PLATFORM_UNSUPPORTED.value,
            "capability executor is unavailable in this runtime",
            capability=action.type,
        )

    def _verify_action(self, action: Action, outcome: ExecutionOutcome) -> VerificationResult:
        if action.type == "file.write_text":
            return verify_file_write_text(outcome)
        if action.type == "file.copy":
            return verify_file_copy(outcome)
        if action.type == "file.move":
            return verify_file_move(outcome)
        if action.type in {"android.notify", "android.open_uri"}:
            return verify_android_command(outcome)
        if action.type in {"android.battery_status", "android.vibrate", "android.toast",
                           "android.clipboard_set", "android.share_text"}:
            return verify_android_expansion(action.type, outcome)
        if action.type == "reddit.create_post":
            if outcome.status is not ActionStatus.SUCCESS:
                return VerificationResult(VerificationStatus.UNAVAILABLE, {"reason": "execution failed"})
            client = self.reddit_client or RedditClient.from_environment()
            return client.verify_post(
                post_id=str(outcome.details["post_id"]),
                subreddit=action.arguments["subreddit"],
                title=action.arguments["title"],
            )
        return VerificationResult(VerificationStatus.UNAVAILABLE, {"reason": "no verifier installed"})

    def _audit_action(
        self,
        envelope: ActionEnvelope,
        action: Action,
        capability: CapabilityDefinition,
        decision: PolicyDecision,
        result: ActionResult,
        execution_attempted: bool,
        started: float,
    ) -> None:
        self.audit.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": envelope.request_id,
                "action_id": action.id,
                "capability": capability.name,
                "risk_class": int(capability.risk_class),
                "policy_decision": decision.value,
                "arguments": redact(action.arguments),
                "execution_attempted": execution_attempted,
                "execution_status": result.status.value,
                "verification_status": result.verification.status.value,
                "duration_ms": round((monotonic() - started) * 1000, 3),
                "error_code": result.error_code,
            }
        )
