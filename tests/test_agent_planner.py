import json
import os
import unittest
from unittest.mock import patch

from lain.capabilities.registry import DEFAULT_REGISTRY
from lain.config import PlannerConfig
from lain.errors import ErrorCode, LainError
from lain.planning import (
    AgentPlannerStatus,
    SubprocessPlanner,
    agent_planner_request,
    parse_agent_decision,
)


class AgentPlannerProtocolTests(unittest.TestCase):
    def test_valid_lifecycle_decisions(self):
        cont = parse_agent_decision(
            b'{"status":"continue","reason":"work remains","actions":[{"type":"android.open_uri","arguments":{"uri":"https://example.com"}}]}',
            max_output_bytes=65536,
            max_actions=8,
        )
        self.assertEqual(cont.status, AgentPlannerStatus.CONTINUE)
        self.assertEqual(len(cont.actions), 1)

        complete = parse_agent_decision(
            b'{"status":"complete","reason":"goal satisfied","actions":[]}',
            max_output_bytes=65536,
            max_actions=8,
        )
        self.assertEqual(complete.status, AgentPlannerStatus.COMPLETE)
        self.assertEqual(complete.actions, ())

        blocked = parse_agent_decision(
            b'{"status":"blocked","reason":"needs user input","actions":[]}',
            max_output_bytes=65536,
            max_actions=8,
        )
        self.assertEqual(blocked.status, AgentPlannerStatus.BLOCKED)
        self.assertEqual(blocked.actions, ())

    def test_invalid_lifecycle_combinations_fail_closed(self):
        invalid = (
            b'{"status":"continue","reason":"x","actions":[]}',
            b'{"status":"complete","reason":"x","actions":[{"type":"android.open_uri","arguments":{"uri":"x"}}]}',
            b'{"status":"blocked","reason":"x","actions":[{"type":"android.open_uri","arguments":{"uri":"x"}}]}',
            b'{"status":"other","reason":"x","actions":[]}',
            b'{"status":"complete","reason":"","actions":[]}',
            b'{"status":"complete","reason":1,"actions":[]}',
            b'{"status":"complete","reason":"x","actions":[],"extra":true}',
            b'{"status":"continue","reason":"x","actions":[{"type":"android.open_uri","arguments":{"uri":"x"},"extra":true}]}',
            b'not json',
            b'\`\`\`json\n{"status":"complete","reason":"x","actions":[]}\n\`\`\`',
            b'{"status":"complete","reason":"x","actions":[]} trailing',
        )
        for document in invalid:
            with self.subTest(document=document), self.assertRaises(LainError) as ctx:
                parse_agent_decision(document, max_output_bytes=65536, max_actions=8)
            self.assertEqual(ctx.exception.code, ErrorCode.PLANNER_OUTPUT_INVALID)

    def test_excessive_continue_batch_fails(self):
        doc = {
            "status": "continue",
            "reason": "x",
            "actions": [
                {"type": "android.notify", "arguments": {"title": "x", "content": "x"}},
                {"type": "android.notify", "arguments": {"title": "y", "content": "y"}},
            ],
        }
        with self.assertRaises(LainError) as ctx:
            parse_agent_decision(json.dumps(doc).encode(), max_output_bytes=65536, max_actions=1)
        self.assertEqual(ctx.exception.code, ErrorCode.PLANNER_OUTPUT_INVALID)

    def test_agent_request_contains_context_catalog_and_constraints(self):
        context = {"iteration": 2, "history": [{"result": "success"}]}
        request = agent_planner_request("finish the task", context, DEFAULT_REGISTRY.definitions(), 3)
        self.assertEqual(request["mode"], "agent")
        self.assertEqual(request["goal"], "finish the task")
        self.assertEqual(request["context"], context)
        self.assertEqual(request["constraints"]["max_actions"], 3)
        self.assertIn("unknown_capabilities_forbidden", request["constraints"])
        self.assertIn("data", request["instructions"].lower())
        self.assertIn("authority", request["instructions"].lower())
        names = {item["name"] for item in request["capabilities"]}
        self.assertEqual(names, set(DEFAULT_REGISTRY.names()))


class AgentSubprocessPlannerTests(unittest.TestCase):
    def planner(self, script):
        return SubprocessPlanner(PlannerConfig(command=("python", "-c", script)))

    def test_decide_uses_agent_mode_and_returns_decision(self):
        script = (
            "import json,sys; "
            "r=json.load(sys.stdin); "
            "assert r['mode']=='agent'; "
            "print(json.dumps({'status':'continue','reason':'next','actions':["
            "{'type':'android.open_uri','arguments':{'uri':'https://example.com'}}]}))"
        )
        decision = self.planner(script).decide("open it", {"iteration": 1}, DEFAULT_REGISTRY.definitions())
        self.assertEqual(decision.status, AgentPlannerStatus.CONTINUE)
        self.assertEqual(decision.actions[0].type, "android.open_uri")

    def test_decide_keeps_runtime_secrets_out_of_environment(self):
        script = (
            "import json,os,sys; json.load(sys.stdin); "
            "visible=[os.getenv('GROQ_API_KEY'),os.getenv('LAIN_REDDIT_CLIENT_ID'),"
            "os.getenv('LAIN_REDDIT_CLIENT_SECRET'),os.getenv('LAIN_REDDIT_REFRESH_TOKEN')]; "
            "print(json.dumps({'status':'blocked','reason':str(visible),'actions':[]}))"
        )
        with patch.dict(
            os.environ,
            {
                "GROQ_API_KEY": "g",
                "LAIN_REDDIT_CLIENT_ID": "id",
                "LAIN_REDDIT_CLIENT_SECRET": "secret",
                "LAIN_REDDIT_REFRESH_TOKEN": "refresh",
            },
        ):
            decision = self.planner(script).decide("x", {}, DEFAULT_REGISTRY.definitions())
        self.assertEqual(decision.reason, "[None, None, None, None]")


if __name__ == "__main__":
    unittest.main()
