from __future__ import annotations

import shutil
import subprocess
from typing import Any, Callable
from urllib.parse import urlparse

from lain.capabilities.registry import DEFAULT_REGISTRY
from lain.config import RuntimeConfig
from lain.errors import ErrorCode, LainError
from lain.execution.models import ExecutionOutcome

Runner = Callable[..., subprocess.CompletedProcess[str]]
Which = Callable[[str], str | None]

_ALLOWED_URI_SCHEMES = frozenset({"http", "https", "geo", "mailto"})


def validate_android_uri(uri: str) -> str:
    parsed = urlparse(uri)
    scheme = parsed.scheme.lower()
    if scheme not in _ALLOWED_URI_SCHEMES:
        raise LainError(
            ErrorCode.ARGUMENT_INVALID,
            "uri scheme is not allowed",
            details={"scheme": scheme or None},
        )
    return uri



def _run_command(argv: list[str], config: RuntimeConfig, runner: Runner) -> ExecutionOutcome:
    try:
        completed = runner(
            argv,
            shell=False,
            capture_output=True,
            text=True,
            timeout=config.android_timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return ExecutionOutcome.failure(
            ErrorCode.TIMEOUT.value,
            "Android adapter command timed out",
            executable=argv[0],
        )
    except OSError as exc:
        return ExecutionOutcome.failure(
            ErrorCode.EXECUTION_FAILED.value,
            "Android adapter command could not be started",
            executable=argv[0],
            exception=type(exc).__name__,
        )
    if completed.returncode != 0:
        return ExecutionOutcome.failure(
            ErrorCode.EXECUTION_FAILED.value,
            "Android adapter command failed",
            executable=argv[0],
            returncode=completed.returncode,
            stderr=(completed.stderr or "")[:1000],
        )
    return ExecutionOutcome.success(executable=argv[0], returncode=completed.returncode)


def execute_android_notify(
    arguments: dict[str, Any],
    config: RuntimeConfig,
    *,
    which: Which = shutil.which,
    runner: Runner = subprocess.run,
) -> ExecutionOutcome:
    try:
        args = DEFAULT_REGISTRY.get("android.notify").validate_arguments(arguments)
    except LainError as exc:
        return ExecutionOutcome.failure(exc.code.value, exc.message, **exc.details)
    if config.android_adapter == "disabled":
        return ExecutionOutcome.unsupported(ErrorCode.PLATFORM_UNSUPPORTED.value, "Android adapter is disabled")
    executable = which("termux-notification")
    if not executable:
        return ExecutionOutcome.unsupported(
            ErrorCode.PLATFORM_UNSUPPORTED.value,
            "termux-notification is unavailable",
        )
    return _run_command(
        [executable, "--title", args["title"], "--content", args["content"]],
        config,
        runner,
    )


def execute_android_open_uri(
    arguments: dict[str, Any],
    config: RuntimeConfig,
    *,
    which: Which = shutil.which,
    runner: Runner = subprocess.run,
) -> ExecutionOutcome:
    try:
        args = DEFAULT_REGISTRY.get("android.open_uri").validate_arguments(arguments)
    except LainError as exc:
        return ExecutionOutcome.failure(exc.code.value, exc.message, **exc.details)
    try:
        uri = validate_android_uri(args["uri"])
    except LainError as exc:
        return ExecutionOutcome.failure(exc.code.value, exc.message, **exc.details)
    if config.android_adapter == "disabled":
        return ExecutionOutcome.unsupported(ErrorCode.PLATFORM_UNSUPPORTED.value, "Android adapter is disabled")

    termux_open = which("termux-open-url")
    if termux_open:
        return _run_command([termux_open, uri], config, runner)

    if config.android_adapter == "auto":
        activity_manager = which("am")
        if activity_manager:
            return _run_command(
                [activity_manager, "start", "-a", "android.intent.action.VIEW", "-d", uri],
                config,
                runner,
            )

    return ExecutionOutcome.unsupported(
        ErrorCode.PLATFORM_UNSUPPORTED.value,
        "no supported Android URI launcher is available",
    )
