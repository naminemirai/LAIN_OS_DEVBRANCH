from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol

from lain.capabilities.registry import CapabilityDefinition


@dataclass(frozen=True, slots=True)
class ProposedAction:
    type: str
    arguments: dict[str, Any]


@dataclass(frozen=True, slots=True)
class PlannerProposal:
    actions: tuple[ProposedAction, ...]


class AgentPlannerStatus(str, Enum):
    CONTINUE = "continue"
    COMPLETE = "complete"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class AgentPlannerDecision:
    status: AgentPlannerStatus
    reason: str
    actions: tuple[ProposedAction, ...]


class Planner(Protocol):
    def propose(
        self,
        intent: str,
        capabilities: tuple[CapabilityDefinition, ...],
    ) -> PlannerProposal: ...


class AgentPlanner(Protocol):
    def decide(
        self,
        goal: str,
        context: dict[str, Any],
        capabilities: tuple[CapabilityDefinition, ...],
    ) -> AgentPlannerDecision: ...
