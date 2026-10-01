from __future__ import annotations

import json
import os
import selectors
import subprocess
import time
from typing import Any

from lain.capabilities.registry import CapabilityDefinition
from lain.config import PlannerConfig
from lain.errors import ErrorCode, LainError
from lain.planning.models import AgentPlannerDecision, PlannerProposal
from lain.planning.protocol import agent_planner_request, parse_agent_decision, parse_proposal, planner_request


class SubprocessPlanner:
    def __init__(self, config: PlannerConfig):
        self.config = config

    def propose(self, intent: str, capabilities: tuple[CapabilityDefinition, ...]) -> PlannerProposal:
        request = planner_request(intent, capabilities, self.config.max_actions)
        stdout = self._invoke(request)
        return parse_proposal(stdout, max_output_bytes=self.config.max_output_bytes, max_actions=self.config.max_actions)

    def decide(
        self,
        goal: str,
        context: dict[str, Any],
        capabilities: tuple[CapabilityDefinition, ...],
    ) -> AgentPlannerDecision:
        request = agent_planner_request(goal, context, capabilities, self.config.max_actions)
        stdout = self._invoke(request)
        return parse_agent_decision(
            stdout,
            max_output_bytes=self.config.max_output_bytes,
            max_actions=self.config.max_actions,
        )

    def _invoke(self, payload: dict[str, Any]) -> bytes:
        if not self.config.command:
            raise LainError(ErrorCode.PLANNER_UNAVAILABLE, "no planner command is configured")
        request = json.dumps(payload, ensure_ascii=False).encode()
        try:
            process = subprocess.Popen(
                list(self.config.command),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                env=_planner_environment(),
            )
        except OSError as exc:
            raise LainError(
                ErrorCode.PLANNER_FAILED,
                "planner process could not be started",
                details={"exception": type(exc).__name__},
            ) from exc
        stdout, stderr = self._exchange(process, request)
        if process.returncode:
            diagnostic = stderr.decode("utf-8", errors="replace")
            raise LainError(
                ErrorCode.PLANNER_FAILED,
                "planner process failed",
                details={"exit_code": process.returncode, "stderr": diagnostic},
            )
        return stdout

    def _exchange(self, process: subprocess.Popen[bytes], request: bytes) -> tuple[bytes, bytes]:
        assert process.stdin is not None and process.stdout is not None and process.stderr is not None
        selector = selectors.DefaultSelector()
        streams = (process.stdin, process.stdout, process.stderr)
        for stream in streams:
            os.set_blocking(stream.fileno(), False)
        selector.register(process.stdin, selectors.EVENT_WRITE, "stdin")
        selector.register(process.stdout, selectors.EVENT_READ, "stdout")
        selector.register(process.stderr, selectors.EVENT_READ, "stderr")
        output = {"stdout": bytearray(), "stderr": bytearray()}
        limits = {"stdout": self.config.max_output_bytes, "stderr": 4096}
        request_offset = 0
        deadline = time.monotonic() + self.config.timeout_seconds
        try:
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self._terminate(process)
                    raise LainError(ErrorCode.PLANNER_TIMEOUT, "planner process timed out")
                for key, _ in selector.select(remaining):
                    stream = key.fileobj
                    name = key.data
                    if name == "stdin":
                        try:
                            written = os.write(stream.fileno(), request[request_offset:])
                        except BrokenPipeError:
                            written = 0
                            request_offset = len(request)
                        else:
                            request_offset += written
                        if request_offset == len(request):
                            selector.unregister(stream)
                            stream.close()
                        continue
                    chunk = os.read(stream.fileno(), 8192)
                    if not chunk:
                        selector.unregister(stream)
                        stream.close()
                        continue
                    output[name].extend(chunk)
                    if len(output[name]) > limits[name]:
                        self._terminate(process)
                        raise LainError(
                            ErrorCode.PLANNER_OUTPUT_TOO_LARGE,
                            f"planner {name} exceeds configured byte limit",
                            details={"stream": name, "limit": limits[name]},
                        )
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self._terminate(process)
                raise LainError(ErrorCode.PLANNER_TIMEOUT, "planner process timed out")
            process.wait(timeout=remaining)
        except subprocess.TimeoutExpired as exc:
            self._terminate(process)
            raise LainError(ErrorCode.PLANNER_TIMEOUT, "planner process timed out") from exc
        finally:
            selector.close()
            for stream in streams:
                if not stream.closed:
                    stream.close()
        return bytes(output["stdout"]), bytes(output["stderr"])

    @staticmethod
    def _terminate(process: subprocess.Popen[bytes]) -> None:
        process.kill()
        process.wait()


_PLANNER_ENV_ALLOWLIST = (
    "PATH",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "TMPDIR",
    "TEMP",
    "TMP",
    "SYSTEMROOT",
    "COMSPEC",
    "PATHEXT",
)


def _planner_environment() -> dict[str, str]:
    """Return only process-launch and locale variables, never executor credentials."""
    return {name: os.environ[name] for name in _PLANNER_ENV_ALLOWLIST if name in os.environ}
