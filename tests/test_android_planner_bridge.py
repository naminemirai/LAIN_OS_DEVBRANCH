import json
import tempfile
import unittest
from pathlib import Path

from lain.agent import AgentBudget, AgentController, AgentPlanningService, AgentSessionStatus, AgentSessionStore
from lain.agent.models import OFFLINE_DEMO_BINDING, PlannerBinding
from lain.app.demo import DemoPlanner
from lain.app.planner_bridge import AndroidPlannerFactory
from lain.errors import ErrorCode, LainError
from lain.planning import AgentPlannerStatus
from lain.runtime.engine import RuntimeEngine
from lain.config import RuntimeConfig


class FakeNativePlannerBridge:
    def __init__(self, response=None):
        self.response = response or {
            "ok": True,
            "body": json.dumps({
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "status": "complete",
                            "reason": "finished",
                            "actions": [],
                        })
                    },
                    "finish_reason": "stop",
                }]
            }),
        }
        self.calls = []
        self.cancelled = False

    def execute(self, binding_json, request_body):
        self.calls.append((binding_json, request_body))
        return json.dumps(self.response, separators=(",", ":"))

    def cancel(self):
        self.cancelled = True


def cloud_binding(mode="cloud"):
    return PlannerBinding(
        profile_id=f"{mode}-primary",
        mode=mode,
        protocol="openai_compatible_v1",
        base_url="https://planner.example.invalid/v1",
        model="model-a",
        credential_ref="cred_0123456789abcdef0123456789abcdef" if mode == "cloud" else None,
        timeout_seconds=30.0,
        max_response_bytes=1_048_576,
        response_mode="json_schema",
        allow_insecure_lan_http=False,
    )


class AndroidPlannerFactoryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.workspace = Path(self.directory.name)

    def test_demo_binding_stays_offline_and_does_not_call_native_bridge(self):
        bridge = FakeNativePlannerBridge()
        planner = AndroidPlannerFactory(self.workspace, bridge)(OFFLINE_DEMO_BINDING)

        self.assertIsInstance(planner, DemoPlanner)
        self.assertEqual(bridge.calls, [])

    def test_cloud_and_local_use_pinned_binding_and_normalize_native_response(self):
        for mode in ("cloud", "local"):
            with self.subTest(mode=mode):
                bridge = FakeNativePlannerBridge()
                binding = cloud_binding(mode)
                planner = AndroidPlannerFactory(self.workspace, bridge)(binding)

                decision = planner.decide("finish", {"iteration_count": 0}, ())

                self.assertEqual(decision.status, AgentPlannerStatus.COMPLETE)
                self.assertEqual(decision.reason, "finished")
                self.assertEqual(decision.actions, ())
                self.assertEqual(len(bridge.calls), 1)
                sent_binding = json.loads(bridge.calls[0][0])
                sent_request = json.loads(bridge.calls[0][1])
                self.assertEqual(sent_binding["profile_id"], binding.profile_id)
                self.assertEqual(sent_binding["mode"], mode)
                self.assertEqual(sent_binding["credential_ref"], binding.credential_ref)
                self.assertEqual(sent_request["model"], "model-a")
                self.assertNotIn("secret", bridge.calls[0][0].lower())

    def test_native_cancellation_maps_to_planner_cancelled(self):
        bridge = FakeNativePlannerBridge({"ok": False, "error": "PLANNER_CANCELLED"})
        planner = AndroidPlannerFactory(self.workspace, bridge)(cloud_binding())

        with self.assertRaises(LainError) as raised:
            planner.decide("finish", {"iteration_count": 0}, ())

        self.assertEqual(raised.exception.code, ErrorCode.PLANNER_CANCELLED)


class PlannerCancellationControllerTests(unittest.TestCase):
    def test_planner_cancelled_transitions_session_to_cancelled(self):
        class CancelledPlanner:
            def decide(self, goal, context, capabilities):
                raise LainError(ErrorCode.PLANNER_CANCELLED, "planner call cancelled")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = RuntimeConfig.for_workspace(root / "workspace")
            runtime = RuntimeEngine(config)
            store = AgentSessionStore(root / "sessions")
            controller = AgentController(
                AgentPlanningService(CancelledPlanner(), max_actions=1),
                runtime,
                store,
                AgentBudget(2, 1, 2, 30.0),
            )
            session = controller.create("finish")

            cancelled = controller.step(session.session_id)

            self.assertEqual(cancelled.status, AgentSessionStatus.CANCELLED)
            self.assertEqual(store.load(session.session_id).status, AgentSessionStatus.CANCELLED)


if __name__ == "__main__":
    unittest.main()
