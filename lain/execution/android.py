from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any, Callable
from urllib.parse import urlparse

from lain.capabilities.registry import DEFAULT_REGISTRY
from lain.config import RuntimeConfig
from lain.errors import ErrorCode, LainError
from lain.execution.models import ExecutionOutcome
from lain.execution.termux import TermuxApiCommandRunner, bounded_run
from lain.protocol.models import ActionStatus
from lain.verification.battery import validate_battery

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
    return TermuxApiCommandRunner(config, which=shutil.which, runner=runner).execute_argv(argv).outcome


def execute_android_notify(
    arguments: dict[str, Any],
    config: RuntimeConfig,
    *,
    which: Which = shutil.which,
    runner: Runner = bounded_run,
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
    runner: Runner = bounded_run,
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


def _execute_expansion(name, arguments, config, which, runner):
    try:
        args = DEFAULT_REGISTRY.get(name).validate_arguments(arguments)
    except LainError as exc:
        return ExecutionOutcome.failure(exc.code.value, exc.message)
    commands = TermuxApiCommandRunner(config, which=which, runner=runner)
    if name == "android.battery_status":
        response = commands.run("termux-battery-status")
        if response.outcome.status is not ActionStatus.SUCCESS:
            return response.outcome
        try:
            battery = validate_battery(json.loads(response.stdout, object_pairs_hook=_unique_object))
        except (ValueError, TypeError, OverflowError, RecursionError):
            return ExecutionOutcome.failure(ErrorCode.EXECUTION_FAILED.value, "invalid structured battery result")
        return ExecutionOutcome.success(battery=battery)
    if name == "android.vibrate":
        return commands.run("termux-vibrate", ("-d", str(args["duration_ms"]))).outcome
    if name == "android.toast":
        return commands.run("termux-toast", ("-s",), input=args["content"]).outcome
    if name == "android.share_text":
        # No -d, receiver, file or model-controlled extras. Termux shows chooser.
        return commands.run("termux-share", ("-a", "send", "-c", "text/plain"), input=args["content"]).outcome
    response = commands.run("termux-clipboard-set", input=args["content"])
    if response.outcome.status is not ActionStatus.SUCCESS:
        return response.outcome
    readback = commands.run("termux-clipboard-get")
    if readback.outcome.status is not ActionStatus.SUCCESS:
        return ExecutionOutcome.success(readback="unavailable")
    # Termux ClipboardAPI uses out.print(text), with no line delimiter.
    # Compare exactly, including user whitespace; never return the read value.
    matches = readback.stdout == args["content"]
    return ExecutionOutcome.success(readback="matched" if matches else "mismatch")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate battery field")
        result[key] = value
    return result


def execute_android_battery_status(arguments, config, *, which=shutil.which, runner=bounded_run):
    return _execute_expansion("android.battery_status", arguments, config, which, runner)


def execute_android_vibrate(arguments, config, *, which=shutil.which, runner=bounded_run):
    return _execute_expansion("android.vibrate", arguments, config, which, runner)


def execute_android_toast(arguments, config, *, which=shutil.which, runner=bounded_run):
    return _execute_expansion("android.toast", arguments, config, which, runner)


def execute_android_clipboard_set(arguments, config, *, which=shutil.which, runner=bounded_run):
    return _execute_expansion("android.clipboard_set", arguments, config, which, runner)


def execute_android_share_text(arguments, config, *, which=shutil.which, runner=bounded_run):
    return _execute_expansion("android.share_text", arguments, config, which, runner)
