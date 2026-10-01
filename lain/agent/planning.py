from __future__ import annotations

from typing import Any
from uuid import uuid4

from lain.agent.models import AgentActionRecord, AgentIterationRecord
from lain.capabilities.registry import CapabilityRegistry, DEFAULT_REGISTRY
from lain.errors import ErrorCode, LainError
from lain.planning.models import (
    AgentPlanner,
    AgentPlannerDecision,
    AgentPlannerStatus,
    ProposedAction,
)
from lain.protocol.models import Action


class AgentPlanningService:
    def __init__(
        self,
        planner: AgentPlanner,
        *,
        registry: CapabilityRegistry = DEFAULT_REGISTRY,
        max_actions: int = 8,
    ):
        if max_actions < 1:
            raise ValueError("max_actions must be >= 1")
        self.planner = planner
        self.registry = registry
        self.max_actions = max_actions

    def decide(
        self,
        goal: str,
        context: dict[str, Any],
        iteration_number: int,
    ) -> AgentIterationRecord:
        if not isinstance(goal, str) or not goal.strip():
            raise LainError(ErrorCode.ARGUMENT_INVALID, "goal must be a non-empty string")
        if not isinstance(context, dict):
            raise LainError(ErrorCode.ARGUMENT_INVALID, "agent context must be an object")
        if not isinstance(iteration_number, int) or isinstance(iteration_number, bool) or iteration_number < 1:
            raise LainError(ErrorCode.ARGUMENT_INVALID, "iteration_number must be >= 1")

        decision = self.planner.decide(goal, context, self.registry.definitions())
        self._validate_decision(decision)

        if decision.status in {AgentPlannerStatus.COMPLETE, AgentPlannerStatus.BLOCKED}:
            return AgentIterationRecord(
                number=iteration_number,
                planner_status=decision.status,
                planner_reason=decision.reason,
                request_id=None,
                actions=(),
            )

        records: list[AgentActionRecord] = []
        for index, proposed in enumerate(decision.actions, 1):
            capability = self.registry.get(proposed.type)
            arguments = capability.validate_arguments(proposed.arguments)
            records.append(
                AgentActionRecord(
                    Action(
                        id=f"i{iteration_number}a{index}",
                        type=proposed.type,
                        arguments=arguments,
                    )
                )
            )
        return AgentIterationRecord(
            number=iteration_number,
            planner_status=decision.status,
            planner_reason=decision.reason,
            request_id=str(uuid4()),
            actions=tuple(records),
        )

    def _validate_decision(self, decision: object) -> None:
        if not isinstance(decision, AgentPlannerDecision):
            raise LainError(ErrorCode.PLANNER_OUTPUT_INVALID, "planner returned an invalid agent decision")
        if not isinstance(decision.status, AgentPlannerStatus):
            raise LainError(ErrorCode.PLANNER_OUTPUT_INVALID, "planner returned an invalid lifecycle status")
        if not isinstance(decision.reason, str) or not decision.reason.strip():
            raise LainError(ErrorCode.PLANNER_OUTPUT_INVALID, "planner returned an invalid reason")
        if not isinstance(decision.actions, tuple):
            raise LainError(ErrorCode.PLANNER_OUTPUT_INVALID, "planner returned an invalid action collection")
        if any(not isinstance(action, ProposedAction) for action in decision.actions):
            raise LainError(ErrorCode.PLANNER_OUTPUT_INVALID, "planner returned an invalid action")
        if len(decision.actions) > self.max_actions:
            raise LainError(
                ErrorCode.PLANNER_OUTPUT_INVALID,
                "planner returned too many actions",
                details={"max_actions": self.max_actions},
            )
        if decision.status is AgentPlannerStatus.CONTINUE and not decision.actions:
            raise LainError(ErrorCode.PLANNER_OUTPUT_INVALID, "continue requires actions")
        if decision.status in {AgentPlannerStatus.COMPLETE, AgentPlannerStatus.BLOCKED} and decision.actions:
            raise LainError(ErrorCode.PLANNER_OUTPUT_INVALID, f"{decision.status.value} requires no actions")
