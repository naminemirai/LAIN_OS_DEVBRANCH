import os
import tempfile
import unittest
from pathlib import Path

from lain.errors import ErrorCode, LainError
from lain.security.paths import resolve_allowed_path


class PathSafetyTests(unittest.TestCase):
    def test_relative_path_is_anchored_to_first_allowed_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self.assertEqual(resolve_allowed_path("notes/a.md", (root,)), root / "notes" / "a.md")

    def test_rejects_parent_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp, "allowed").resolve()
            root.mkdir()
            with self.assertRaises(LainError) as ctx:
                resolve_allowed_path("../../etc/passwd", (root,))
            self.assertEqual(ctx.exception.code, ErrorCode.PATH_OUTSIDE_ALLOWED_ROOT)

    def test_rejects_absolute_path_outside_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp, "allowed").resolve()
            root.mkdir()
            outside = Path(tmp, "private", "x.txt").resolve()
            with self.assertRaises(LainError) as ctx:
                resolve_allowed_path(outside, (root,))
            self.assertEqual(ctx.exception.code, ErrorCode.PATH_OUTSIDE_ALLOWED_ROOT)

    def test_rejects_embedded_nul(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(LainError) as ctx:
                resolve_allowed_path("bad\x00name", (Path(tmp),))
            self.assertEqual(ctx.exception.code, ErrorCode.ARGUMENT_INVALID)

    def test_rejects_extremely_long_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(LainError) as ctx:
                resolve_allowed_path("a" * 5000, (Path(tmp),))
            self.assertEqual(ctx.exception.code, ErrorCode.ARGUMENT_INVALID)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_rejects_symlink_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp, "allowed").resolve()
            outside = Path(tmp, "outside").resolve()
            root.mkdir(); outside.mkdir()
            (root / "escape").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(LainError) as ctx:
                resolve_allowed_path("escape/secret.txt", (root,))
            self.assertEqual(ctx.exception.code, ErrorCode.PATH_OUTSIDE_ALLOWED_ROOT)

    def test_must_exist_reports_missing_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            with self.assertRaises(LainError) as ctx:
                resolve_allowed_path("missing", (root,), must_exist=True)
            self.assertEqual(ctx.exception.code, ErrorCode.SOURCE_NOT_FOUND)


if __name__ == "__main__":
    unittest.main()
