import tempfile
import unittest
from pathlib import Path

from lain.config import RuntimeConfig
from lain.execution.filesystem import execute_file_copy, execute_file_move, execute_file_write_text
from lain.protocol.models import VerificationStatus
from lain.verification.filesystem import verify_file_copy, verify_file_move, verify_file_write_text


class FilesystemVerificationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.config = RuntimeConfig.for_workspace(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_write_verification_passes_then_detects_tampering(self):
        outcome = execute_file_write_text({"path": "x", "content": "one", "overwrite": False}, self.config)
        self.assertEqual(verify_file_write_text(outcome).status, VerificationStatus.PASSED)
        (self.root / "x").write_text("tampered")
        self.assertEqual(verify_file_write_text(outcome).status, VerificationStatus.FAILED)

    def test_copy_verification_compares_hash(self):
        (self.root / "source").write_text("one")
        outcome = execute_file_copy({"source": "source", "destination": "copy", "overwrite": False}, self.config)
        self.assertEqual(verify_file_copy(outcome).status, VerificationStatus.PASSED)
        (self.root / "copy").write_text("two")
        self.assertEqual(verify_file_copy(outcome).status, VerificationStatus.FAILED)

    def test_move_verification_requires_source_absent(self):
        (self.root / "source").write_text("one")
        outcome = execute_file_move({"source": "source", "destination": "moved", "overwrite": False}, self.config)
        self.assertEqual(verify_file_move(outcome).status, VerificationStatus.PASSED)
        (self.root / "source").write_text("resurrected")
        self.assertEqual(verify_file_move(outcome).status, VerificationStatus.FAILED)


if __name__ == "__main__":
    unittest.main()
