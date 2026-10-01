import subprocess
import tempfile
import unittest
from pathlib import Path

from lain.config import RuntimeConfig
from lain.errors import ErrorCode
from lain.execution.android import execute_android_notify, execute_android_open_uri
from lain.protocol.models import ActionStatus, VerificationStatus
from lain.verification.android import verify_android_command


class AndroidAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.config = RuntimeConfig.for_workspace(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_notify_is_unsupported_without_termux_command(self):
        outcome = execute_android_notify(
            {"title": "Hi", "content": "There"}, self.config, which=lambda _: None
        )
        self.assertEqual(outcome.status, ActionStatus.UNSUPPORTED)
        self.assertEqual(outcome.error_code, ErrorCode.PLATFORM_UNSUPPORTED.value)
        self.assertEqual(verify_android_command(outcome).status, VerificationStatus.NOT_APPLICABLE)

    def test_notify_uses_fixed_argv_and_shell_false(self):
        calls = []
        def runner(argv, **kwargs):
            calls.append((argv, kwargs))
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")
        outcome = execute_android_notify(
            {"title": "Hello", "content": "World"},
            self.config,
            which=lambda name: "/bin/termux-notification" if name == "termux-notification" else None,
            runner=runner,
        )
        self.assertEqual(outcome.status, ActionStatus.SUCCESS)
        argv, kwargs = calls[0]
        self.assertEqual(argv, ["/bin/termux-notification", "--title", "Hello", "--content", "World"])
        self.assertFalse(kwargs["shell"])
        self.assertEqual(verify_android_command(outcome).status, VerificationStatus.LIMITED)

    def test_open_uri_prefers_termux_open_url(self):
        calls = []
        def runner(argv, **kwargs):
            calls.append((argv, kwargs))
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")
        outcome = execute_android_open_uri(
            {"uri": "geo:40,-80"},
            self.config,
            which=lambda name: "/bin/termux-open-url" if name == "termux-open-url" else None,
            runner=runner,
        )
        self.assertEqual(outcome.status, ActionStatus.SUCCESS)
        self.assertEqual(calls[0][0], ["/bin/termux-open-url", "geo:40,-80"])

    def test_open_uri_can_fall_back_to_android_activity_manager(self):
        calls = []
        def runner(argv, **kwargs):
            calls.append((argv, kwargs))
            return subprocess.CompletedProcess(argv, 0, stdout="Starting", stderr="")
        outcome = execute_android_open_uri(
            {"uri": "https://example.com"},
            self.config,
            which=lambda name: "/system/bin/am" if name == "am" else None,
            runner=runner,
        )
        self.assertEqual(outcome.status, ActionStatus.SUCCESS)
        self.assertEqual(calls[0][0], [
            "/system/bin/am", "start", "-a", "android.intent.action.VIEW", "-d", "https://example.com"
        ])
        self.assertFalse(calls[0][1]["shell"])

    def test_rejects_nonstandard_intent_uri_scheme_before_launch(self):
        calls = []
        def runner(argv, **kwargs):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")
        outcome = execute_android_open_uri(
            {"uri": "intent://evil#Intent;scheme=https;end"},
            self.config,
            which=lambda _: "/bin/fake",
            runner=runner,
        )
        self.assertEqual(outcome.status, ActionStatus.FAILURE)
        self.assertEqual(outcome.error_code, ErrorCode.ARGUMENT_INVALID.value)
        self.assertEqual(calls, [])

    def test_invalid_uri_is_argument_failure(self):
        outcome = execute_android_open_uri({"uri": "not a uri"}, self.config, which=lambda _: "/bin/x")
        self.assertEqual(outcome.status, ActionStatus.FAILURE)
        self.assertEqual(outcome.error_code, ErrorCode.ARGUMENT_INVALID.value)

    def test_timeout_is_structured_failure(self):
        def runner(argv, **kwargs):
            raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
        outcome = execute_android_notify(
            {"title": "Hello", "content": "World"},
            self.config,
            which=lambda _: "/bin/termux-notification",
            runner=runner,
        )
        self.assertEqual(outcome.status, ActionStatus.FAILURE)
        self.assertEqual(outcome.error_code, ErrorCode.TIMEOUT.value)

    def test_nonzero_exit_is_structured_failure(self):
        def runner(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 7, stdout="", stderr="nope")
        outcome = execute_android_notify(
            {"title": "Hello", "content": "World"},
            self.config,
            which=lambda _: "/bin/termux-notification",
            runner=runner,
        )
        self.assertEqual(outcome.status, ActionStatus.FAILURE)
        self.assertEqual(outcome.error_code, ErrorCode.EXECUTION_FAILED.value)


if __name__ == "__main__":
    unittest.main()
