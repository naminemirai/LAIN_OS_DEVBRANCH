import unittest
from uuid import uuid4

from lain.agent import (
    AgentActionRecord,
    AgentBudget,
    AgentIterationRecord,
    AgentSession,
    AgentSessionStatus,
    build_agent_context,
)
from lain.planning import AgentPlannerStatus
from lain.protocol.models import Action, ActionResult, ActionStatus, VerificationResult, VerificationStatus


class AgentContextTests(unittest.TestCase):
    def test_context_contains_progress_budgets_and_redacted_history(self):
        action = Action(
            "i1a1",
            "android.notify",
            {
                "title": "hello",
                "content": "private message",
                "token": "planner-must-not-see-this",
            },
        )
        result = ActionResult(
            action_id="i1a1",
            status=ActionStatus.SUCCESS,
            details={
                "message": "accepted",
                "authorization": "Bearer hidden",
                "nested": {"body": "secret body", "safe": "visible"},
            },
            verification=VerificationResult(
                VerificationStatus.LIMITED,
                {"reason": "accepted", "api_key": "hidden-key"},
            ),
        )
        iteration = AgentIterationRecord(
            number=1,
            planner_status=AgentPlannerStatus.CONTINUE,
            planner_reason="send notification",
            request_id=str(uuid4()),
            actions=(AgentActionRecord(action, result),),
        )
        session = AgentSession(
            version="1",
            session_id=str(uuid4()),
            goal="finish the notification task",
            status=AgentSessionStatus.PLANNING,
            created_at="2026-09-29T20:00:00+00:00",
            updated_at="2026-09-29T20:01:00+00:00",
            iterations=(iteration,),
            total_attempted_actions=1,
            budget=AgentBudget(12, 8, 32, 900.0),
            cumulative_runtime_seconds=2.5,
            terminal_reason=None,
        )

        context = build_agent_context(session)

        self.assertEqual(context["goal"], session.goal)
        self.assertEqual(context["iteration_count"], 1)
        self.assertEqual(
            context["remaining_budget"],
            {"iterations": 11, "actions": 31, "runtime_seconds": 897.5},
        )
        history = context["history"][0]
        self.assertEqual(history["status"], "continue")
        self.assertEqual(history["reason"], "send notification")
        action_context = history["actions"][0]
        self.assertEqual(action_context["type"], "android.notify")
        self.assertEqual(action_context["arguments"]["title"], "hello")
        self.assertEqual(action_context["arguments"]["content"], "[REDACTED]")
        self.assertEqual(action_context["arguments"]["token"], "[REDACTED]")
        self.assertEqual(action_context["result"]["status"], "success")
        self.assertEqual(action_context["result"]["details"]["authorization"], "[REDACTED]")
        self.assertEqual(action_context["result"]["details"]["nested"]["body"], "[REDACTED]")
        self.assertEqual(action_context["result"]["details"]["nested"]["safe"], "visible")
        self.assertEqual(action_context["result"]["verification"]["status"], "limited")
        self.assertEqual(
            action_context["result"]["verification"]["details"]["api_key"],
            "[REDACTED]",
        )

    def test_remaining_budgets_are_never_negative(self):
        session = AgentSession(
            version="1",
            session_id=str(uuid4()),
            goal="x",
            status=AgentSessionStatus.PLANNING,
            created_at="2026-09-29T20:00:00+00:00",
            updated_at="2026-09-29T20:00:00+00:00",
            iterations=(),
            total_attempted_actions=40,
            budget=AgentBudget(1, 1, 1, 1.0),
            cumulative_runtime_seconds=5.0,
            terminal_reason=None,
        )
        context = build_agent_context(session)
        self.assertEqual(context["remaining_budget"]["actions"], 0)
        self.assertEqual(context["remaining_budget"]["runtime_seconds"], 0.0)


if __name__ == "__main__":
    unittest.main()
