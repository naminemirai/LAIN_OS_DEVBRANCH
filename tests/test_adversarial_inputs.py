import tempfile
import unittest
from pathlib import Path

from lain.config import RuntimeConfig
from lain.errors import ErrorCode
from lain.execution.filesystem import execute_file_write_text
from lain.protocol.models import ActionStatus


class AdversarialInputTests(unittest.TestCase):
    def test_shell_metacharacters_are_literal_filename_characters(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            config = RuntimeConfig.for_workspace(root)
            name = "literal;&&|$()`ticks`.txt"
            outcome = execute_file_write_text({"path": name, "content": "safe", "overwrite": False}, config)
            self.assertEqual(outcome.status, ActionStatus.SUCCESS)
            self.assertEqual((root / name).read_text(), "safe")

    def test_traversal_is_failure_without_external_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp, "allowed").resolve(); root.mkdir()
            config = RuntimeConfig.for_workspace(root)
            outcome = execute_file_write_text({"path": "../outside.txt", "content": "bad", "overwrite": False}, config)
            self.assertEqual(outcome.status, ActionStatus.FAILURE)
            self.assertEqual(outcome.error_code, ErrorCode.PATH_OUTSIDE_ALLOWED_ROOT.value)
            self.assertFalse(Path(tmp, "outside.txt").exists())


if __name__ == "__main__":
    unittest.main()
