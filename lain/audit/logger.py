from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_SECRET_MARKERS = (
    "password",
    "passwd",
    "token",
    "secret",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "recovery",
    "credential",
)


def _is_secret_key(key: str) -> bool:
    lowered = key.lower().replace("-", "_")
    if lowered in {"content", "body"}:
        return True
    return any(marker in lowered for marker in _SECRET_MARKERS)


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if isinstance(key, str) and _is_secret_key(key) else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return [redact(item) for item in value]
    return value


class AuditLogger:
    def __init__(self, path: Path):
        self.path = Path(path).expanduser().resolve()

    def append(self, record: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(redact(record), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        data = (payload + "\n").encode("utf-8")
        fd = os.open(self.path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
        try:
            os.write(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)

    def records(self):
        try:
            handle = self.path.open("r", encoding="utf-8")
        except FileNotFoundError:
            return
        with handle:
            for line in handle:
                try:
                    value = json.loads(line)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
                if isinstance(value, dict):
                    yield value

    def has_executed_request(self, request_id: str) -> bool:
        return any(
            record.get("request_id") == request_id and record.get("execution_attempted") is True
            for record in self.records()
        )

    def has_executed_action(self, request_id: str, action_id: str) -> bool:
        return any(
            record.get("request_id") == request_id
            and record.get("action_id") == action_id
            and record.get("execution_attempted") is True
            for record in self.records()
        )
