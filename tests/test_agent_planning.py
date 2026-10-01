import unittest

from lain.agent import AgentPlanningService
from lain.errors import ErrorCode, LainError
from lain.planning import AgentPlannerDecision, AgentPlannerStatus, ProposedAction


class FakeAgentPlanner:
    def __init__(self, decision):
        self.decision = decision
        self.calls = []

    def decide(self, goal, context, capabilities):
        self.calls.append((goal, context, capabilities))
        return self.decision


class AgentPlanningServiceTests(unittest.TestCase):
    def test_continue_decision_gets_trusted_ids_request_id_and_validated_arguments(self):
        planner = FakeAgentPlanner(
            AgentPlannerDecision(
                status=AgentPlannerStatus.CONTINUE,
                reason="write two files",
                actions=(
                    ProposedAction("file.write_text", {"path": "a.txt", "content": "a"}),
                    ProposedAction("file.write_text", {"path": "b.txt", "content": "b"}),
                ),
            )
        )
        service = AgentPlanningService(planner, max_actions=8)

        iteration = service.decide("make files", {"iteration_count": 0}, 1)

        self.assertEqual(iteration.number, 1)
        self.assertEqual(iteration.planner_status, AgentPlannerStatus.CONTINUE)
        self.assertTrue(iteration.request_id)
        self.assertEqual([r.action.id for r in iteration.actions], ["i1a1", "i1a2"])
        self.assertEqual(iteration.actions[0].action.arguments["overwrite"], False)
        self.assertEqual(planner.calls[0][0], "make files")
        self.assertEqual(planner.calls[0][1], {"iteration_count": 0})
        self.assertTrue(planner.calls[0][2])

    def test_complete_and_blocked_have_no_trusted_request_or_actions(self):
        for status in (AgentPlannerStatus.COMPLETE, AgentPlannerStatus.BLOCKED):
            planner = FakeAgentPlanner(AgentPlannerDecision(status, "done", ()))
            iteration = AgentPlanningService(planner).decide("goal", {}, 2)
            self.assertEqual(iteration.planner_status, status)
            self.assertIsNone(iteration.request_id)
            self.assertEqual(iteration.actions, ())

    def test_unknown_capability_and_invalid_arguments_fail_before_execution(self):
        cases = (
            (
                AgentPlannerDecision(
                    AgentPlannerStatus.CONTINUE,
                    "bad",
                    (ProposedAction("shell.exec", {}),),
                ),
                ErrorCode.CAPABILITY_UNKNOWN,
            ),
            (
                AgentPlannerDecision(
                    AgentPlannerStatus.CONTINUE,
                    "bad",
                    (ProposedAction("android.open_uri", {}),),
                ),
                ErrorCode.ARGUMENT_INVALID,
            ),
        )
        for decision, expected in cases:
            with self.subTest(expected=expected), self.assertRaises(LainError) as ctx:
                AgentPlanningService(FakeAgentPlanner(decision)).decide("goal", {}, 1)
            self.assertEqual(ctx.exception.code, expected)

    def test_malformed_injected_decisions_fail_closed(self):
        malformed = (
            object(),
            AgentPlannerDecision(AgentPlannerStatus.CONTINUE, "x", ()),
            AgentPlannerDecision(
                AgentPlannerStatus.COMPLETE,
                "x",
                (ProposedAction("android.open_uri", {"uri": "https://example.com"}),),
            ),
            AgentPlannerDecision(AgentPlannerStatus.BLOCKED, "", ()),
        )
        for decision in malformed:
            with self.subTest(decision=decision), self.assertRaises(LainError) as ctx:
                AgentPlanningService(FakeAgentPlanner(decision)).decide("goal", {}, 1)
            self.assertEqual(ctx.exception.code, ErrorCode.PLANNER_OUTPUT_INVALID)

    def test_excessive_batch_fails_closed(self):
        decision = AgentPlannerDecision(
            AgentPlannerStatus.CONTINUE,
            "too many",
            (
                ProposedAction("android.notify", {"title": "1", "content": "x"}),
                ProposedAction("android.notify", {"title": "2", "content": "x"}),
            ),
        )
        with self.assertRaises(LainError) as ctx:
            AgentPlanningService(FakeAgentPlanner(decision), max_actions=1).decide("goal", {}, 1)
        self.assertEqual(ctx.exception.code, ErrorCode.PLANNER_OUTPUT_INVALID)

    def test_invalid_service_inputs_fail_before_planner_call(self):
        planner = FakeAgentPlanner(AgentPlannerDecision(AgentPlannerStatus.COMPLETE, "done", ()))
        service = AgentPlanningService(planner)
        for goal, context, number in (("", {}, 1), ("x", [], 1), ("x", {}, 0)):
            with self.subTest(goal=goal, context=context, number=number), self.assertRaises(LainError):
                service.decide(goal, context, number)
        self.assertEqual(planner.calls, [])


if __name__ == "__main__":
    unittest.main()
