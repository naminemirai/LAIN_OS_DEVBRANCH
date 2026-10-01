import unittest
from uuid import uuid4

from lain.agent import (
    AgentActionRecord,
    AgentBudget,
    AgentIterationRecord,
    AgentSession,
    AgentSessionStatus,
)
from lain.errors import ErrorCode, LainError
from lain.planning import AgentPlannerStatus
from lain.protocol.models import Action, ActionResult, ActionStatus, VerificationResult, VerificationStatus


class AgentModelTests(unittest.TestCase):
    def sample_session(self):
        action = Action("i1a1", "android.open_uri", {"uri": "https://example.com"})
        result = ActionResult(
            action_id="i1a1",
            status=ActionStatus.SUCCESS,
            details={"opened": True},
            verification=VerificationResult(VerificationStatus.LIMITED, {"reason": "accepted"}),
        )
        iteration = AgentIterationRecord(
            number=1,
            planner_status=AgentPlannerStatus.CONTINUE,
            planner_reason="open the page",
            request_id=str(uuid4()),
            actions=(AgentActionRecord(action, result),),
        )
        return AgentSession(
            version="1",
            session_id=str(uuid4()),
            goal="open a page",
            status=AgentSessionStatus.EXECUTING,
            created_at="2026-09-29T20:00:00+00:00",
            updated_at="2026-09-29T20:00:01+00:00",
            iterations=(iteration,),
            total_attempted_actions=1,
            budget=AgentBudget(12, 8, 32, 900.0),
            cumulative_runtime_seconds=1.25,
            terminal_reason=None,
        )

    def test_round_trip_preserves_nested_enums_and_results(self):
        session = self.sample_session()
        raw = session.to_dict()
        self.assertEqual(raw["iteration_count"], 1)
        loaded = AgentSession.from_dict(raw)
        self.assertEqual(loaded, session)
        self.assertEqual(loaded.iteration_count, 1)
        self.assertIs(loaded.iterations[0].actions[0].result.status, ActionStatus.SUCCESS)
        self.assertIs(
            loaded.iterations[0].actions[0].result.verification.status,
            VerificationStatus.LIMITED,
        )

    def test_continue_iteration_requires_request_and_actions(self):
        with self.assertRaises(LainError) as ctx:
            AgentIterationRecord(
                number=1,
                planner_status=AgentPlannerStatus.CONTINUE,
                planner_reason="x",
                request_id=None,
                actions=(),
            )
        self.assertEqual(ctx.exception.code, ErrorCode.AGENT_SESSION_INVALID)

    def test_complete_and_blocked_iterations_have_no_request_or_actions(self):
        for status in (AgentPlannerStatus.COMPLETE, AgentPlannerStatus.BLOCKED):
            record = AgentIterationRecord(
                number=1,
                planner_status=status,
                planner_reason="done",
                request_id=None,
                actions=(),
            )
            self.assertEqual(record.actions, ())
            with self.assertRaises(LainError):
                AgentIterationRecord(
                    number=1,
                    planner_status=status,
                    planner_reason="bad",
                    request_id=str(uuid4()),
                    actions=(
                        AgentActionRecord(
                            Action("i1a1", "android.notify", {"title": "x", "content": "x"}),
                            None,
                        ),
                    ),
                )

    def test_transition_table_rejects_invalid_and_terminal_transitions(self):
        session = self.sample_session()
        complete = session.transition(
            AgentSessionStatus.COMPLETE,
            updated_at="2026-09-29T20:00:02+00:00",
            terminal_reason="planner marked complete",
        )
        for target in AgentSessionStatus:
            with self.subTest(target=target), self.assertRaises(LainError) as ctx:
                complete.transition(target, updated_at="2026-09-29T20:00:03+00:00")
            self.assertEqual(ctx.exception.code, ErrorCode.AGENT_STATE_INVALID)

        created = AgentSession(
            version="1",
            session_id=str(uuid4()),
            goal="x",
            status=AgentSessionStatus.CREATED,
            created_at="2026-09-29T20:00:00+00:00",
            updated_at="2026-09-29T20:00:00+00:00",
            iterations=(),
            total_attempted_actions=0,
            budget=AgentBudget(12, 8, 32, 900.0),
            cumulative_runtime_seconds=0.0,
            terminal_reason=None,
        )
        with self.assertRaises(LainError) as ctx:
            created.transition(AgentSessionStatus.COMPLETE, updated_at="2026-09-29T20:00:01+00:00")
        self.assertEqual(ctx.exception.code, ErrorCode.AGENT_STATE_INVALID)

        paused = session.transition(
            AgentSessionStatus.PAUSED_CONFIRMATION,
            updated_at="2026-09-29T20:00:02+00:00",
        )
        with self.assertRaises(LainError) as ctx:
            paused.transition(AgentSessionStatus.PLANNING, updated_at="2026-09-29T20:00:03+00:00")
        self.assertEqual(ctx.exception.code, ErrorCode.AGENT_STATE_INVALID)


if __name__ == "__main__":
    unittest.main()


class AgentFiniteBudgetRegressionTests(unittest.TestCase):
    def test_agent_budget_rejects_non_finite_runtime_limits(self):
        from lain.agent import AgentBudget
        from lain.errors import LainError
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value), self.assertRaises(LainError):
                AgentBudget(12, 8, 32, value)

    def test_session_rejects_non_finite_consumed_runtime(self):
        session = AgentModelTests().sample_session()
        raw = session.to_dict()
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                candidate = dict(raw)
                candidate["cumulative_runtime_seconds"] = value
                with self.assertRaises(LainError):
                    AgentSession.from_dict(candidate)
