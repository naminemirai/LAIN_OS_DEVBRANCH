from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from lain.agent import (
    AgentBudget,
    AgentController,
    AgentPlanningService,
    AgentSessionStatus,
    AgentSessionStore,
)
from lain.audit.logger import AuditLogger, redact
from lain.capabilities.registry import DEFAULT_REGISTRY
from lain.config import RuntimeConfig, load_config
from lain.errors import ErrorCode, LainError
from lain.policy.engine import evaluate_policy
from lain.planning import PlanningService, SubprocessPlanner
from lain.protocol.models import ActionStatus
from lain.protocol.parser import parse_envelope
from lain.runtime.engine import RuntimeEngine


def _json_dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)


def _load_runtime_config(args: argparse.Namespace) -> RuntimeConfig:
    if args.config and args.workspace:
        raise LainError(ErrorCode.ARGUMENT_INVALID, "--config and --workspace are mutually exclusive")
    if args.workspace:
        return RuntimeConfig.for_workspace(Path(args.workspace))
    try:
        return load_config(Path(args.config)) if args.config else load_config(None)
    except (OSError, ValueError) as exc:
        raise LainError(
            ErrorCode.ARGUMENT_INVALID,
            "configuration could not be loaded",
            details={"exception": type(exc).__name__},
        ) from exc


def _read_request(path: str, config: RuntimeConfig):
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise LainError(
            ErrorCode.ARGUMENT_INVALID,
            "request file could not be read",
            details={"exception": type(exc).__name__},
        ) from exc
    return parse_envelope(raw, max_actions=config.max_actions)


def _emit(payload: Any, *, json_mode: bool, stream=None) -> None:
    stream = stream or sys.stdout
    if json_mode:
        print(_json_dump(payload), file=stream)
    else:
        if isinstance(payload, str):
            print(payload, file=stream)
        else:
            print(_json_dump(payload), file=stream)


def _capability_payload():
    items = []
    for cap in DEFAULT_REGISTRY.definitions():
        items.append(
            {
                "name": cap.name,
                "risk_class": int(cap.risk_class),
                "required_permissions": list(cap.required_permissions),
                "reversible": cap.reversible,
                "confirmation_required": cap.confirmation_required,
                "network_required": cap.network_required,
                "environments": list(cap.environments),
                "verification": cap.verification,
                "arguments": {
                    name: {
                        "types": [typ.__name__ for typ in spec.types],
                        "required": spec.required,
                    }
                    for name, spec in cap.arguments.items()
                },
            }
        )
    return {"capabilities": items}


def _build_agent_stack(config: RuntimeConfig) -> tuple[AgentController, AgentSessionStore]:
    planner = SubprocessPlanner(config.planner)
    planning = AgentPlanningService(
        planner,
        max_actions=config.planner.max_actions,
    )
    runtime = RuntimeEngine(config)
    store = AgentSessionStore(config.audit_path.parent / "sessions")
    budget = AgentBudget(
        max_iterations=config.agent.max_iterations,
        max_actions_per_batch=config.planner.max_actions,
        max_total_actions=config.agent.max_total_actions,
        max_runtime_seconds=config.agent.max_runtime_seconds,
    )
    return AgentController(planning, runtime, store, budget), store


def _safe_session_payload(session) -> dict[str, Any]:
    return redact(session.to_dict())


def _safe_plan_payload(envelope) -> dict[str, Any]:
    payload = envelope.to_dict()
    for action in payload["actions"]:
        if action["type"] in {"android.clipboard_set", "android.share_text"}:
            action["arguments"] = redact(action["arguments"])
    return payload


def _session_summary(session) -> dict[str, Any]:
    return {
        "session_id": session.session_id,
        "goal": session.goal,
        "status": session.status.value,
        "iteration_count": session.iteration_count,
        "updated_at": session.updated_at,
    }


def _agent_exit_code(session) -> int:
    return 0 if session.status is AgentSessionStatus.COMPLETE else 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lain")
    parser.add_argument("--config")
    parser.add_argument("--workspace")
    subs = parser.add_subparsers(dest="command", required=True)

    validate = subs.add_parser("validate")
    validate.add_argument("request")
    validate.add_argument("--json", action="store_true")

    execute = subs.add_parser("execute")
    execute.add_argument("request")
    execute.add_argument("--confirm", action="append", default=[])
    execute.add_argument("--json", action="store_true")

    plan = subs.add_parser("plan")
    plan.add_argument("intent")
    plan.add_argument("--json", action="store_true")

    do = subs.add_parser("do")
    do.add_argument("intent")
    do.add_argument("--json", action="store_true")

    run = subs.add_parser("run")
    run.add_argument("goal")
    run.add_argument("--json", action="store_true")

    sessions = subs.add_parser("sessions")
    sessions.add_argument("--json", action="store_true")

    session = subs.add_parser("session")
    session.add_argument("session_id")
    session.add_argument("--json", action="store_true")

    resume = subs.add_parser("resume")
    resume.add_argument("session_id")
    resume.add_argument("--confirm", action="append", default=[])
    resume.add_argument("--json", action="store_true")

    cancel = subs.add_parser("cancel")
    cancel.add_argument("session_id")
    cancel.add_argument("--json", action="store_true")

    capabilities = subs.add_parser("capabilities")
    capabilities.add_argument("--json", action="store_true")

    policy = subs.add_parser("policy-check")
    policy.add_argument("request")
    policy.add_argument("--json", action="store_true")

    audit = subs.add_parser("audit")
    audit_subs = audit.add_subparsers(dest="audit_command", required=True)
    tail = audit_subs.add_parser("tail")
    tail.add_argument("--limit", type=int, default=20)
    tail.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    json_mode = bool(getattr(args, "json", False))
    try:
        if args.command == "capabilities":
            _emit(_capability_payload(), json_mode=json_mode)
            return 0

        config = _load_runtime_config(args)

        if args.command in {"run", "sessions", "session", "resume", "cancel"}:
            controller, store = _build_agent_stack(config)

            if args.command == "run":
                session = controller.create(args.goal)
                session = controller.run_until_stop(session.session_id)
                _emit(_safe_session_payload(session), json_mode=json_mode)
                return _agent_exit_code(session)

            if args.command == "sessions":
                payload = {
                    "sessions": [
                        _session_summary(session)
                        for session in store.list_sessions()
                    ]
                }
                _emit(payload, json_mode=json_mode)
                return 0

            if args.command == "session":
                session = store.load(args.session_id)
                _emit(_safe_session_payload(session), json_mode=json_mode)
                return 0

            if args.command == "resume":
                session = controller.run_until_stop(
                    args.session_id,
                    confirmed_action_ids=frozenset(args.confirm),
                )
                _emit(_safe_session_payload(session), json_mode=json_mode)
                return _agent_exit_code(session)

            if args.command == "cancel":
                session = controller.cancel(args.session_id)
                _emit(_safe_session_payload(session), json_mode=json_mode)
                return _agent_exit_code(session)

        engine = RuntimeEngine(config)

        if args.command in {"plan", "do"}:
            planner = SubprocessPlanner(config.planner)
            envelope = PlanningService(
                planner,
                max_actions=config.planner.max_actions,
            ).plan(args.intent)
            engine.preflight(envelope)
            if args.command == "plan":
                _emit(_safe_plan_payload(envelope), json_mode=json_mode)
                return 0
            result = engine.execute(envelope)
            payload = result.to_dict()
            payload["actions"] = _safe_plan_payload(envelope)["actions"]
            _emit(payload, json_mode=json_mode)
            return 0 if all(item.status is ActionStatus.SUCCESS for item in result.results) else 3

        if args.command == "validate":
            envelope = _read_request(args.request, config)
            engine.preflight(envelope)
            _emit({"valid": True, "request_id": envelope.request_id}, json_mode=json_mode)
            return 0

        if args.command == "policy-check":
            envelope = _read_request(args.request, config)
            prepared = engine.preflight(envelope)
            payload = {
                "request_id": envelope.request_id,
                "actions": [
                    {
                        "id": action.id,
                        "type": action.type,
                        "decision": evaluate_policy(capability, action, config).value,
                    }
                    for action, capability in prepared
                ],
            }
            _emit(payload, json_mode=json_mode)
            return 0

        if args.command == "execute":
            envelope = _read_request(args.request, config)
            result = engine.execute(
                envelope,
                confirmed_action_ids=frozenset(args.confirm),
            )
            payload = result.to_dict()
            _emit(payload, json_mode=json_mode)
            return 0 if all(item.status is ActionStatus.SUCCESS for item in result.results) else 3

        if args.command == "audit" and args.audit_command == "tail":
            if args.limit < 1:
                raise LainError(ErrorCode.ARGUMENT_INVALID, "--limit must be >= 1")
            records = list(AuditLogger(config.audit_path).records())[-args.limit:]
            _emit({"records": records}, json_mode=json_mode)
            return 0

        raise LainError(ErrorCode.INTERNAL_ERROR, "unhandled command")
    except LainError as exc:
        payload = exc.to_dict()
        if json_mode:
            _emit(payload, json_mode=True)
        else:
            _emit(
                f"{exc.code.value}: {exc.message}",
                json_mode=False,
                stream=sys.stderr,
            )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
