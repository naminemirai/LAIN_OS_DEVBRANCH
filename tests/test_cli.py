import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from uuid import uuid4

from lain.cli import main


def write_request(path: Path, actions):
    path.write_text(json.dumps({
        "version": "0",
        "request_id": str(uuid4()),
        "intent": "cli test",
        "actions": actions,
    }))


class CliTests(unittest.TestCase):
    def run_cli(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_capabilities_json_lists_v0_actions(self):
        code, out, _ = self.run_cli(["capabilities", "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertIn("file.write_text", [item["name"] for item in payload["capabilities"]])
        self.assertNotIn("shell.exec", [item["name"] for item in payload["capabilities"]])

    def test_validate_rejects_unknown_capability(self):
        with tempfile.TemporaryDirectory() as tmp:
            request = Path(tmp, "request.json")
            write_request(request, [{"id": "a1", "type": "shell.exec", "arguments": {}}])
            code, out, _ = self.run_cli(["--workspace", tmp, "validate", str(request), "--json"])
            self.assertNotEqual(code, 0)
            self.assertEqual(json.loads(out)["error"]["code"], "CAPABILITY_UNKNOWN")

    def test_policy_check_reports_confirmation_requirement(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "x").write_text("old")
            request = Path(tmp, "request.json")
            write_request(request, [{
                "id": "a1", "type": "file.write_text",
                "arguments": {"path": "x", "content": "new", "overwrite": True},
            }])
            code, out, _ = self.run_cli(["--workspace", tmp, "policy-check", str(request), "--json"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["actions"][0]["decision"], "require_confirmation")

    def test_execute_writes_file_and_emits_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            request = Path(tmp, "request.json")
            write_request(request, [{"id": "a1", "type": "file.write_text", "arguments": {"path": "x.md", "content": "hi"}}])
            code, out, _ = self.run_cli(["--workspace", tmp, "execute", str(request), "--json"])
            self.assertEqual(code, 0)
            payload = json.loads(out)
            self.assertEqual(payload["results"][0]["status"], "success")
            self.assertEqual(Path(tmp, "x.md").read_text(), "hi")

    def test_audit_tail_returns_recent_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            request = Path(tmp, "request.json")
            write_request(request, [{"id": "a1", "type": "file.write_text", "arguments": {"path": "x", "content": "hi"}}])
            self.run_cli(["--workspace", tmp, "execute", str(request), "--json"])
            code, out, _ = self.run_cli(["--workspace", tmp, "audit", "tail", "--limit", "1", "--json"])
            self.assertEqual(code, 0)
            payload = json.loads(out)
            self.assertEqual(len(payload["records"]), 1)
            self.assertEqual(payload["records"][0]["capability"], "file.write_text")


if __name__ == "__main__":
    unittest.main()
