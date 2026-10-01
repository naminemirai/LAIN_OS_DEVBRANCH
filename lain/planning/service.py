from __future__ import annotations

from uuid import uuid4

from lain.capabilities.registry import CapabilityRegistry, DEFAULT_REGISTRY
from lain.errors import ErrorCode, LainError
from lain.planning.models import Planner, PlannerProposal, ProposedAction
from lain.protocol.models import Action, ActionEnvelope


class PlanningService:
    def __init__(self, planner: Planner, *, registry: CapabilityRegistry = DEFAULT_REGISTRY, max_actions: int = 8):
        self.planner = planner
        self.registry = registry
        self.max_actions = max_actions

    def plan(self, intent: str) -> ActionEnvelope:
        if not isinstance(intent, str) or not intent.strip():
            raise LainError(ErrorCode.ARGUMENT_INVALID, "intent must be a non-empty string")
        proposal = self.planner.propose(intent, self.registry.definitions())
        if not isinstance(proposal, PlannerProposal) or not proposal.actions or len(proposal.actions) > self.max_actions:
            raise LainError(ErrorCode.PLANNER_OUTPUT_INVALID, "planner returned an invalid action count")
        actions = []
        for index, proposed in enumerate(proposal.actions, 1):
            if not isinstance(proposed, ProposedAction):
                raise LainError(ErrorCode.PLANNER_OUTPUT_INVALID, "planner returned an invalid action")
            capability = self.registry.get(proposed.type)
            arguments = capability.validate_arguments(proposed.arguments)
            actions.append(Action(f"a{index}", proposed.type, arguments))
        return ActionEnvelope("0", str(uuid4()), intent, tuple(actions))
