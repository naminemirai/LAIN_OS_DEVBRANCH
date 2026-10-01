from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from lain.errors import ErrorCode, LainError
from lain.protocol.models import Action, ActionEnvelope

_REQUEST_KEYS = {"version", "request_id", "intent", "actions"}
_ACTION_KEYS = {"id", "type", "arguments"}


def _invalid(message: str, **details: Any) -> LainError:
    return LainError(ErrorCode.PROTOCOL_INVALID, message, details=details)


def parse_envelope(data: str | bytes | dict[str, Any], *, max_actions: int) -> ActionEnvelope:
    if isinstance(data, (str, bytes)):
        try:
            raw = json.loads(data)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise _invalid("request is not valid JSON") from exc
    elif isinstance(data, dict):
        raw = data
    else:
        raise _invalid("request must be a JSON object")

    if not isinstance(raw, dict):
        raise _invalid("request must be a JSON object")
    missing = _REQUEST_KEYS - raw.keys()
    extra = raw.keys() - _REQUEST_KEYS
    if missing or extra:
        raise _invalid("request fields are invalid", missing=sorted(missing), extra=sorted(extra))

    version = raw["version"]
    if version != "0":
        raise LainError(
            ErrorCode.PROTOCOL_VERSION_UNSUPPORTED,
            "unsupported protocol version",
            details={"version": version},
        )

    request_id = raw["request_id"]
    if not isinstance(request_id, str):
        raise _invalid("request_id must be a UUID string")
    try:
        UUID(request_id)
    except (ValueError, AttributeError) as exc:
        raise _invalid("request_id must be a valid UUID") from exc

    intent = raw["intent"]
    if not isinstance(intent, str) or not intent.strip():
        raise _invalid("intent must be a non-empty string")

    actions_raw = raw["actions"]
    if not isinstance(actions_raw, list) or not actions_raw:
        raise _invalid("actions must be a non-empty array")
    if len(actions_raw) > max_actions:
        raise _invalid("too many actions", count=len(actions_raw), max_actions=max_actions)

    seen: set[str] = set()
    actions: list[Action] = []
    for index, item in enumerate(actions_raw):
        if not isinstance(item, dict):
            raise _invalid("action must be an object", index=index)
        missing_action = _ACTION_KEYS - item.keys()
        extra_action = item.keys() - _ACTION_KEYS
        if missing_action or extra_action:
            raise _invalid(
                "action fields are invalid",
                index=index,
                missing=sorted(missing_action),
                extra=sorted(extra_action),
            )
        action_id = item["id"]
        action_type = item["type"]
        arguments = item["arguments"]
        if not isinstance(action_id, str) or not action_id.strip():
            raise _invalid("action id must be a non-empty string", index=index)
        if action_id in seen:
            raise _invalid("duplicate action id", action_id=action_id)
        if not isinstance(action_type, str) or not action_type.strip():
            raise _invalid("action type must be a non-empty string", index=index)
        if not isinstance(arguments, dict):
            raise _invalid("action arguments must be an object", index=index)
        seen.add(action_id)
        actions.append(Action(action_id, action_type, dict(arguments)))

    return ActionEnvelope("0", request_id, intent, tuple(actions))
