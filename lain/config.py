from __future__ import annotations

import math
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class PlannerConfig:
    command: tuple[str, ...] = ()
    timeout_seconds: float = 30.0
    max_output_bytes: int = 65_536
    max_actions: int = 8

    def __post_init__(self) -> None:
        if not all(isinstance(value, str) and value for value in self.command):
            raise ValueError("planner_command must contain non-empty strings")
        if self.timeout_seconds <= 0:
            raise ValueError("planner_timeout_seconds must be > 0")
        if self.max_output_bytes < 1:
            raise ValueError("planner_max_output_bytes must be >= 1")
        if self.max_actions < 1:
            raise ValueError("planner_max_actions must be >= 1")


@dataclass(frozen=True, slots=True)
class AgentConfig:
    max_iterations: int = 12
    max_total_actions: int = 32
    max_runtime_seconds: float = 900.0

    def __post_init__(self) -> None:
        if not isinstance(self.max_iterations, int) or isinstance(self.max_iterations, bool) or self.max_iterations < 1:
            raise ValueError("agent_max_iterations must be a positive integer")
        if not isinstance(self.max_total_actions, int) or isinstance(self.max_total_actions, bool) or self.max_total_actions < 1:
            raise ValueError("agent_max_total_actions must be a positive integer")
        if (
            not isinstance(self.max_runtime_seconds, (int, float))
            or isinstance(self.max_runtime_seconds, bool)
            or not math.isfinite(self.max_runtime_seconds)
            or self.max_runtime_seconds <= 0
        ):
            raise ValueError("agent_max_runtime_seconds must be a finite positive number")


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    allowed_roots: tuple[Path, ...]
    audit_path: Path
    max_actions: int = 32
    max_text_write_bytes: int = 1_048_576
    overwrite_default: bool = False
    confirmation_risk_threshold: int = 2
    deny_risk_threshold: int = 3
    android_adapter: str = "auto"
    android_timeout_seconds: float = 10.0
    planner: PlannerConfig = PlannerConfig()
    agent: AgentConfig = AgentConfig()

    def __post_init__(self) -> None:
        roots = tuple(Path(root).expanduser().resolve() for root in self.allowed_roots)
        if not roots:
            raise ValueError("allowed_roots must not be empty")
        if self.max_actions < 1:
            raise ValueError("max_actions must be >= 1")
        if self.max_text_write_bytes < 1:
            raise ValueError("max_text_write_bytes must be >= 1")
        if self.android_timeout_seconds <= 0:
            raise ValueError("android_timeout_seconds must be > 0")
        if self.android_adapter not in {"auto", "termux", "disabled"}:
            raise ValueError("android_adapter must be auto, termux, or disabled")
        if not (0 <= self.confirmation_risk_threshold <= 3):
            raise ValueError("confirmation_risk_threshold must be between 0 and 3")
        if not (0 <= self.deny_risk_threshold <= 3):
            raise ValueError("deny_risk_threshold must be between 0 and 3")
        object.__setattr__(self, "allowed_roots", roots)
        object.__setattr__(self, "audit_path", Path(self.audit_path).expanduser().resolve())

    @classmethod
    def default(cls) -> "RuntimeConfig":
        root = (Path.home() / ".lain" / "workspace").resolve()
        return cls(allowed_roots=(root,), audit_path=(Path.home() / ".lain" / "audit.jsonl"))

    @classmethod
    def for_workspace(cls, workspace: Path) -> "RuntimeConfig":
        root = Path(workspace).expanduser().resolve()
        return cls(allowed_roots=(root,), audit_path=(root / ".lain" / "audit.jsonl"))


_ALLOWED_CONFIG_KEYS = {
    "allowed_roots",
    "audit_path",
    "max_actions",
    "max_text_write_bytes",
    "overwrite_default",
    "confirmation_risk_threshold",
    "deny_risk_threshold",
    "android_adapter",
    "android_timeout_seconds",
    "planner_command",
    "planner_timeout_seconds",
    "planner_max_output_bytes",
    "planner_max_actions",
    "agent_max_iterations",
    "agent_max_total_actions",
    "agent_max_runtime_seconds",
}


def load_config(path: Path | str | None = None) -> RuntimeConfig:
    if path is None:
        return RuntimeConfig.default()
    config_path = Path(path).expanduser().resolve()
    raw = tomllib.loads(config_path.read_text(encoding="utf-8"))
    unknown = set(raw) - _ALLOWED_CONFIG_KEYS
    if unknown:
        raise ValueError(f"unknown configuration keys: {', '.join(sorted(unknown))}")
    data: dict[str, Any] = dict(raw)
    if "allowed_roots" not in data or "audit_path" not in data:
        raise ValueError("configuration requires allowed_roots and audit_path")
    roots = data["allowed_roots"]
    if not isinstance(roots, list) or not all(isinstance(item, str) for item in roots):
        raise ValueError("allowed_roots must be an array of paths")
    data["allowed_roots"] = tuple(Path(item) for item in roots)
    data["audit_path"] = Path(data["audit_path"])
    planner_command = data.pop("planner_command", [])
    if not isinstance(planner_command, list) or not all(isinstance(item, str) for item in planner_command):
        raise ValueError("planner_command must be an array of strings")
    data["planner"] = PlannerConfig(
        command=tuple(planner_command),
        timeout_seconds=data.pop("planner_timeout_seconds", 30.0),
        max_output_bytes=data.pop("planner_max_output_bytes", 65_536),
        max_actions=data.pop("planner_max_actions", 8),
    )
    data["agent"] = AgentConfig(
        max_iterations=data.pop("agent_max_iterations", 12),
        max_total_actions=data.pop("agent_max_total_actions", 32),
        max_runtime_seconds=data.pop("agent_max_runtime_seconds", 900.0),
    )
    return RuntimeConfig(**data)
