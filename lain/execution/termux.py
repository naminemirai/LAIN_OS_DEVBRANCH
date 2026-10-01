"""Private command transport; capability adapters alone select commands/flags."""
from __future__ import annotations

import os
import selectors
import signal
import subprocess
import time
from dataclasses import dataclass
from typing import Callable

from lain.config import RuntimeConfig
from lain.errors import ErrorCode, LainError
from lain.execution.models import ExecutionOutcome

STDOUT_LIMIT = 65536
STDERR_LIMIT = 4096
_ENVIRONMENT = (
    "PATH", "HOME", "PREFIX", "TMPDIR", "LANG", "LC_ALL", "LC_CTYPE",
    "ANDROID_ROOT", "ANDROID_DATA", "LD_LIBRARY_PATH",
)


def command_environment() -> dict[str, str]:
    """Keep Termux launch/IPC essentials; exclude provider/executor secrets."""
    return {name: os.environ[name] for name in _ENVIRONMENT if name in os.environ}


def bounded_run(argv, *, shell, capture_output, text, check, input, timeout, env):
    """subprocess.run-compatible injection seam with actively bounded pipe I/O.

    POSIX is the supported execution environment (Linux/Termux). A process group
    allows timeout/output-limit cleanup of API script descendants as well.
    """
    if shell or not capture_output or not text or check:
        raise ValueError("unsupported command transport options")
    process = subprocess.Popen(
        argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        shell=False, env=env, start_new_session=True,
    )
    selector = selectors.DefaultSelector()
    streams = (process.stdin, process.stdout, process.stderr)
    output = {"stdout": bytearray(), "stderr": bytearray()}
    limits = {"stdout": STDOUT_LIMIT, "stderr": STDERR_LIMIT}
    request = input.encode("utf-8")
    offset = 0
    deadline = time.monotonic() + timeout
    try:
        for stream in streams:
            assert stream is not None
            os.set_blocking(stream.fileno(), False)
        if request:
            selector.register(process.stdin, selectors.EVENT_WRITE, "stdin")
        else:
            process.stdin.close()
        selector.register(process.stdout, selectors.EVENT_READ, "stdout")
        selector.register(process.stderr, selectors.EVENT_READ, "stderr")
        group_cleaned = False
        while selector.get_map():
            parent_exited = process.poll() is not None
            if parent_exited and not group_cleaned:
                # Termux API helpers may leave short-lived broadcast descendants
                # holding inherited stdout/stderr descriptors open after the
                # direct helper has completed.  The session is private to this
                # command, so terminate only those leftover descendants.
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                group_cleaned = True
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(argv, timeout)
            events = selector.select(0 if parent_exited else remaining)
            if parent_exited and not events:
                break
            for key, _ in events:
                stream, name = key.fileobj, key.data
                if name == "stdin":
                    try:
                        offset += os.write(stream.fileno(), request[offset:offset + 8192])
                    except BrokenPipeError:
                        offset = len(request)
                    if offset == len(request):
                        selector.unregister(stream)
                        stream.close()
                else:
                    chunk = os.read(stream.fileno(), min(8192, limits[name] + 1 - len(output[name])))
                    if not chunk:
                        selector.unregister(stream)
                        stream.close()
                        continue
                    output[name].extend(chunk)
                    if len(output[name]) > limits[name]:
                        raise LainError(ErrorCode.EXECUTION_FAILED, "Android command output exceeds byte limit")
        if process.poll() is None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(argv, timeout)
            process.wait(timeout=remaining)
        return subprocess.CompletedProcess(
            argv, process.returncode, stdout=output["stdout"].decode("utf-8"),
            stderr=output["stderr"].decode("utf-8"),
        )
    except BaseException:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        raise
    finally:
        selector.close()
        for stream in streams:
            if stream is not None and not stream.closed:
                stream.close()


@dataclass(frozen=True, slots=True)
class CommandResult:
    outcome: ExecutionOutcome
    # Private evidence. Never embed command output in runtime/session/audit data.
    stdout: str = ""


class TermuxApiCommandRunner:
    def __init__(self, config: RuntimeConfig, *, which: Callable, runner: Callable = bounded_run):
        self.config, self.which, self.runner = config, which, runner

    def run(self, command: str, options: tuple[str, ...] = (), *, input: str = "") -> CommandResult:
        if self.config.android_adapter == "disabled":
            return CommandResult(ExecutionOutcome.unsupported(
                ErrorCode.PLATFORM_UNSUPPORTED.value, "Android adapter is disabled"))
        executable = self.which(command)
        if not executable:
            return CommandResult(ExecutionOutcome.unsupported(
                ErrorCode.PLATFORM_UNSUPPORTED.value, f"{command} is unavailable"))
        return self.execute_argv([executable, *options], input=input)

    def execute_argv(self, argv: list[str], *, input: str = "") -> CommandResult:
        try:
            result = self.runner(
                argv, shell=False, capture_output=True, text=True, check=False,
                input=input, timeout=self.config.android_timeout_seconds, env=command_environment(),
            )
            if (len((result.stdout or "").encode("utf-8")) > STDOUT_LIMIT
                    or len((result.stderr or "").encode("utf-8")) > STDERR_LIMIT):
                raise LainError(ErrorCode.EXECUTION_FAILED, "Android command output exceeds byte limit")
        except subprocess.TimeoutExpired:
            return CommandResult(ExecutionOutcome.failure(ErrorCode.TIMEOUT.value, "Android adapter command timed out"))
        except (OSError, UnicodeError, ValueError, LainError):
            return CommandResult(ExecutionOutcome.failure(
                ErrorCode.EXECUTION_FAILED.value, "Android adapter command failed or returned invalid output"))
        if result.returncode != 0:
            return CommandResult(ExecutionOutcome.failure(
                ErrorCode.EXECUTION_FAILED.value, "Android adapter command failed", returncode=result.returncode))
        return CommandResult(ExecutionOutcome.success(executable=argv[0], returncode=0), result.stdout or "")
