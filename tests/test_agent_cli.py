import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from lain.cli import main


MULTI_SCRIPT = r"""
import json, sys
request = json.load(sys.stdin)
if request.get("mode") == "agent":
    if request["context"]["iteration_count"] == 0:
        response = {
            "status": "continue",
            "reason": "write both files",
            "actions": [
                {"type": "file.write_text", "arguments": {"path": "hello.txt", "content": "hello"}},
                {"type": "file.write_text", "arguments": {"path": "done.txt", "content": "finished"}},
            ],
        }
    else:
        response = {"status": "complete", "reason": "files created", "actions": []}
else:
    response = {"actions": [{"type": "file.write_text", "arguments": {"path": "hello.txt", "content": "hello"}}]}
print(json.dumps(response))
"""

CONFIRM_SCRIPT = r"""
import json, sys
request = json.load(sys.stdin)
if request.get("mode") == "agent":
    if request["context"]["iteration_count"] == 0:
        response = {
            "status": "continue",
            "reason": "overwrite x",
            "actions": [
                {
                    "type": "file.write_text",
                    "arguments": {"path": "x.txt", "content": "new secret text", "overwrite": True},
                }
            ],
        }
    else:
        response = {"status": "complete", "reason": "overwrite verified", "actions": []}
else:
    response = {"actions": [{"type": "file.write_text", "arguments": {"path": "x.txt", "content": "new secret text", "overwrite": True}}]}
print(json.dumps(response))
"""


def write_config(root: Path, script: str) -> tuple[Path, Path]:
    workspace = root / "workspace"
    workspace.mkdir()
    config = root / "config.toml"
    config.write_text(
        f"allowed_roots = [{json.dumps(str(workspace))}]\n"
        f"audit_path = {json.dumps(str(root / '.lain' / 'audit.jsonl'))}\n"
        f"planner_command = [\"python\", \"-c\", {json.dumps(script)}]\n",
        encoding="utf-8",
    )
    return config, workspace


class AgentCliTests(unittest.TestCase):
    def run_cli(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_run_executes_multi_iteration_goal_and_persists_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config, workspace = write_config(root, MULTI_SCRIPT)

            code, out, _ = self.run_cli(
                ["--config", str(config), "run", "create two files", "--json"]
            )

            self.assertEqual(code, 0)
            payload = json.loads(out)
            self.assertEqual(payload["status"], "complete")
            self.assertEqual((workspace / "hello.txt").read_text(), "hello")
            self.assertEqual((workspace / "done.txt").read_text(), "finished")
            state = root / ".lain" / "sessions" / payload["session_id"] / "state.json"
            self.assertTrue(state.exists())

    def test_sessions_session_and_cancel_use_durable_state_and_redact_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config, workspace = write_config(root, CONFIRM_SCRIPT)
            (workspace / "x.txt").write_text("old")

            run_code, run_out, _ = self.run_cli(
                ["--config", str(config), "run", "overwrite x", "--json"]
            )
            self.assertEqual(run_code, 3)
            paused = json.loads(run_out)
            session_id = paused["session_id"]

            list_code, list_out, _ = self.run_cli(
                ["--config", str(config), "sessions", "--json"]
            )
            self.assertEqual(list_code, 0)
            listing = json.loads(list_out)["sessions"]
            self.assertEqual(listing[0]["session_id"], session_id)
            self.assertEqual(listing[0]["status"], "paused_confirmation")

            show_code, show_out, _ = self.run_cli(
                ["--config", str(config), "session", session_id, "--json"]
            )
            self.assertEqual(show_code, 0)
            shown = json.loads(show_out)
            self.assertEqual(shown["status"], "paused_confirmation")
            self.assertEqual(
                shown["iterations"][0]["actions"][0]["action"]["arguments"]["content"],
                "[REDACTED]",
            )

            cancel_code, cancel_out, _ = self.run_cli(
                ["--config", str(config), "cancel", session_id, "--json"]
            )
            self.assertEqual(cancel_code, 3)
            self.assertEqual(json.loads(cancel_out)["status"], "cancelled")
            self.assertEqual((workspace / "x.txt").read_text(), "old")

    def test_resume_requires_exact_confirmation_then_continues_to_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config, workspace = write_config(root, CONFIRM_SCRIPT)
            target = workspace / "x.txt"
            target.write_text("old")

            code, out, _ = self.run_cli(
                ["--config", str(config), "run", "overwrite x", "--json"]
            )
            self.assertEqual(code, 3)
            paused = json.loads(out)
            session_id = paused["session_id"]
            request_id = paused["iterations"][0]["request_id"]
            self.assertEqual(paused["status"], "paused_confirmation")
            self.assertEqual(target.read_text(), "old")

            code, out, _ = self.run_cli(
                ["--config", str(config), "resume", session_id, "--json"]
            )
            self.assertEqual(code, 3)
            self.assertEqual(json.loads(out)["status"], "paused_confirmation")
            self.assertEqual(target.read_text(), "old")

            code, out, _ = self.run_cli(
                [
                    "--config",
                    str(config),
                    "resume",
                    session_id,
                    "--confirm",
                    "wrong",
                    "--json",
                ]
            )
            self.assertEqual(code, 3)
            self.assertEqual(json.loads(out)["status"], "paused_confirmation")
            self.assertEqual(target.read_text(), "old")

            code, out, _ = self.run_cli(
                [
                    "--config",
                    str(config),
                    "resume",
                    session_id,
                    "--confirm",
                    "i1a1",
                    "--json",
                ]
            )
            self.assertEqual(code, 0)
            final = json.loads(out)
            self.assertEqual(final["status"], "complete")
            self.assertEqual(final["iterations"][0]["request_id"], request_id)
            self.assertEqual(target.read_text(), "new secret text")


if __name__ == "__main__":
    unittest.main()
