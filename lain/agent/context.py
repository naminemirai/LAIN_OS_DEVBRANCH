from __future__ import annotations

from typing import Any

from lain.agent.models import AgentSession
from lain.audit.logger import redact


def build_agent_context(session: AgentSession) -> dict[str, Any]:
    history: list[dict[str, Any]] = []
    for iteration in session.iterations:
        actions: list[dict[str, Any]] = []
        for record in iteration.actions:
            result = record.result
            result_context: dict[str, Any] | None = None
            if result is not None:
                result_context = {
                    "status": result.status.value,
                    "details": redact(result.details),
                    "verification": {
                        "status": result.verification.status.value,
                        "details": redact(result.verification.details),
                    },
                    "error_code": result.error_code,
                }
            actions.append(
                {
                    "id": record.action.id,
                    "type": record.action.type,
                    "arguments": redact(record.action.arguments),
                    "result": result_context,
                }
            )
        history.append(
            {
                "number": iteration.number,
                "status": iteration.planner_status.value,
                "reason": iteration.planner_reason,
                "actions": actions,
            }
        )

    return {
        "goal": session.goal,
        "iteration_count": session.iteration_count,
        "remaining_budget": {
            "iterations": max(0, session.budget.max_iterations - session.iteration_count),
            "actions": max(0, session.budget.max_total_actions - session.total_attempted_actions),
            "runtime_seconds": max(
                0.0,
                session.budget.max_runtime_seconds - session.cumulative_runtime_seconds,
            ),
        },
        "history": history,
    }
