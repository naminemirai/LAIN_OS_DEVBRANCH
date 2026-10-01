import json
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from lain.audit.logger import AuditLogger
from lain.config import RuntimeConfig
from lain.errors import ErrorCode, LainError
from lain.protocol.models import ActionStatus, VerificationStatus
from lain.protocol.parser import parse_envelope
from lain.runtime.engine import RuntimeEngine


class EndToEndTests(unittest.TestCase):
    def test_write_copy_move_pipeline_is_verified_and_audited(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            config = RuntimeConfig.for_workspace(root)
            engine = RuntimeEngine(config)
            request = parse_envelope({
                "version": "0",
                "request_id": str(uuid4()),
                "intent": "create a markdown note then copy and move the copy",
                "actions": [
                    {"id": "a1", "type": "file.write_text", "arguments": {"path": "demo.md", "content": "# LAIN_OS\n"}},
                    {"id": "a2", "type": "file.copy", "arguments": {"source": "demo.md", "destination": "demo-copy.md"}},
                    {"id": "a3", "type": "file.move", "arguments": {"source": "demo-copy.md", "destination": "demo-final.md"}},
                ],
            }, max_actions=config.max_actions)

            result = engine.execute(request)

            self.assertEqual([item.status for item in result.results], [ActionStatus.SUCCESS] * 3)
            self.assertTrue(all(item.verification.status is VerificationStatus.PASSED for item in result.results))
            self.assertEqual((root / "demo.md").read_text(), "# LAIN_OS\n")
            self.assertFalse((root / "demo-copy.md").exists())
            self.assertEqual((root / "demo-final.md").read_text(), "# LAIN_OS\n")
            records = list(AuditLogger(config.audit_path).records())
            self.assertEqual(len(records), 3)
            self.assertTrue(all(record["execution_attempted"] for record in records))
            self.assertTrue(all(record["verification_status"] == "passed" for record in records))

    def test_unsafe_later_uri_is_rejected_before_prior_file_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            config = RuntimeConfig.for_workspace(root)
            engine = RuntimeEngine(config)
            request = parse_envelope({
                "version": "0",
                "request_id": str(uuid4()),
                "intent": "unsafe URI must fail preflight",
                "actions": [
                    {"id": "a1", "type": "file.write_text", "arguments": {"path": "safe.md", "content": "must not happen"}},
                    {"id": "a2", "type": "android.open_uri", "arguments": {"uri": "intent://evil#Intent;scheme=https;end"}},
                ],
            }, max_actions=config.max_actions)

            with self.assertRaises(LainError) as ctx:
                engine.execute(request)

            self.assertEqual(ctx.exception.code, ErrorCode.ARGUMENT_INVALID)
            self.assertFalse((root / "safe.md").exists())

    def test_invalid_later_path_is_rejected_before_any_prior_action_executes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp, "allowed").resolve()
            root.mkdir()
            config = RuntimeConfig.for_workspace(root)
            engine = RuntimeEngine(config)
            request = parse_envelope({
                "version": "0",
                "request_id": str(uuid4()),
                "intent": "malicious path must fail closed",
                "actions": [
                    {"id": "a1", "type": "file.write_text", "arguments": {"path": "safe.md", "content": "must not happen"}},
                    {"id": "a2", "type": "file.write_text", "arguments": {"path": "../escaped.md", "content": "nope"}},
                ],
            }, max_actions=config.max_actions)

            with self.assertRaises(LainError) as ctx:
                engine.execute(request)

            self.assertEqual(ctx.exception.code, ErrorCode.PATH_OUTSIDE_ALLOWED_ROOT)
            self.assertFalse((root / "safe.md").exists())
            self.assertFalse(Path(tmp, "escaped.md").exists())
            self.assertEqual(list(AuditLogger(config.audit_path).records()), [])


if __name__ == "__main__":
    unittest.main()
