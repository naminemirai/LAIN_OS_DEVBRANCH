import subprocess
import tempfile
import tomllib
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from scripts import verify, verify_android

ROOT = Path(__file__).resolve().parents[1]


class DeveloperLoopTests(unittest.TestCase):
    def test_console_entrypoint_metadata(self):
        project = tomllib.loads((ROOT / "pyproject.toml").read_text())
        self.assertEqual(project["project"]["scripts"]["lain"], "lain.cli:main")
        self.assertEqual(project["project"]["scripts"]["lain-groq-planner"], "lain.planner_adapters.groq:main")
        self.assertEqual(project["project"]["dependencies"], [])

    def test_verifier_stops_at_first_failed_command(self):
        calls = []

        def runner(argv, **kwargs):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 9)

        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            result = verify.main(root=ROOT, runner=runner)
        self.assertEqual(result, 9)
        self.assertEqual(len(calls), 1)

    def test_verifier_succeeds_when_commands_and_scan_succeed(self):
        calls = []

        def runner(argv, **kwargs):
            calls.append(argv)
            output = "" if argv[:2] == ["git", "ls-files"] else None
            return subprocess.CompletedProcess(argv, 0, stdout=output)

        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            result = verify.main(root=ROOT, runner=runner)
        self.assertEqual(result, 0)
        self.assertIn(["git", "diff", "--cached", "--check"], calls)
        self.assertIn(["git", "diff", "--check"], calls)

    def test_verifier_checks_committed_diff_range(self):
        calls = []

        def runner(argv, **kwargs):
            calls.append(argv)
            output = "" if argv[:2] == ["git", "ls-files"] else None
            return subprocess.CompletedProcess(argv, 0, stdout=output)

        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            result = verify.main(root=ROOT, runner=runner, diff_range="base..head")
        self.assertEqual(result, 0)
        self.assertIn(["git", "diff", "--check", "base..head"], calls)

    def test_scanner_reports_runtime_security_pattern(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "lain" / "bad.py"
            source.parent.mkdir()
            source.write_text("danger = eval(user_input)\n")

            def runner(argv, **kwargs):
                return subprocess.CompletedProcess(argv, 0, stdout="lain/bad.py\0")

            self.assertTrue(verify.scan_repository(root, runner))

    def test_ci_uses_only_canonical_verifier_for_tests(self):
        workflow = (ROOT / ".github" / "workflows" / "verify.yml").read_text()
        self.assertIn("python scripts/verify.py", workflow)
        self.assertIn("--diff-range", workflow)
        self.assertIn("github.event.pull_request.base.sha", workflow)
        self.assertIn("github.event.pull_request.head.sha", workflow)
        self.assertIn("github.event.before", workflow)
        self.assertNotIn("unittest", workflow)
        self.assertNotIn("compileall", workflow)

    def test_android_default_only_inspects_then_verifies(self):
        looked_up = []
        with patch.object(verify_android.importlib.util, "find_spec", return_value=object()), patch.object(
            verify_android.verify, "main", return_value=0
        ) as verifier:
            with redirect_stdout(StringIO()):
                result = verify_android.main(which=lambda command: looked_up.append(command) or None)
        self.assertEqual(result, 0)
        self.assertEqual(looked_up, list(verify_android.TERMUX_COMMANDS))
        verifier.assert_called_once_with()

    def test_android_helper_inspects_expansion_commands_without_actions(self):
        looked_up = []
        with patch.object(verify_android.verify, 'main', return_value=0):
            with redirect_stdout(StringIO()):
                result = verify_android.main(which=lambda name: looked_up.append(name) or None)
        self.assertEqual(result, 0)
        self.assertTrue({'termux-battery-status', 'termux-vibrate', 'termux-toast',
                         'termux-clipboard-set', 'termux-clipboard-get', 'termux-share'} <= set(looked_up))


if __name__ == "__main__":
    unittest.main()
