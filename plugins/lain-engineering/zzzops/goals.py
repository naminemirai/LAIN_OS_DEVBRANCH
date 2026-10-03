#!/usr/bin/env python3
"""Managed-goal parsing, validation, rendering, and record projection."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from pathlib import Path
from typing import Any, Callable

GOAL_SCHEMA_VERSION = 1
GOAL_BLOCK_START = "<!-- zzzops-goal"
GOAL_BLOCK_END = "zzzops-goal -->"
GOAL_HISTORY_BLOCK_START = "<!-- zzzops-history"
GOAL_HISTORY_BLOCK_END = "zzzops-history -->"
GOAL_HISTORY_SCHEMA_VERSION = 1
GOAL_SCHEMA_LABEL_PREFIX = "zzzops:schema:v"
GOAL_FIELDS = {
    "schema_version", "status", "priority", "value", "difficulty", "confidence",
    "parent", "depends_on", "claim", "blockers", "evidence", "next_action",
    "revision", "implementation", "resources", "engineering_rigor",
}
GOAL_STATUSES = {"new", "triaged", "ready", "in_progress", "blocked", "done", "cancelled"}
GOAL_PRIORITIES = {"P0", "P1", "P2", "P3"}
GOAL_VALUES = {"critical", "high", "medium", "low"}
GOAL_DIFFICULTIES = {"unknown", "XS", "S", "M", "L", "XL"}
GOAL_CONFIDENCES = {"low", "medium", "high"}
ENGINEERING_RIGOR_LEVELS = {"vibe", "structured", "agentic"}
ENGINEERING_RIGOR_OVERRIDE_AUTHORITIES = {"explicit_user", "goal_requirement"}
GOAL_TRANSITION_SCHEMA_VERSION = 1
GOAL_TRANSITION_FIELDS = {"schema_version", "expected_revision", "expected_digest", "goal"}
GOAL_CREATE_SCHEMA_VERSION = 1
GOAL_CREATE_FIELDS = {"schema_version", "title", "body", "labels", "goal"}
BLOCKER_CATEGORIES = {"specification", "decision", "access-approval", "human-action", "external-dependency", "technical-unknown", "safety-compliance"}
REDUNDANT_GOAL_TITLE_PREFIX = re.compile(r"^\[G-\d{8}-\d{3}-[^\]]+\]\s*")
HISTORICAL_HUMAN_SECTIONS = {
    "completed evidence", "evidence", "history", "implementation history",
    "prior checkpoints", "resolved blockers", "superseded requirements",
}
_normalize_resources: Callable[[Any], list[str]] | None = None
_text_present: Callable[[Any], bool] | None = None


class GoalTransitionProviderError(ValueError):
    """The provider did not produce a safe, confirmed goal-operation result."""

def configure_entrypoint(*, normalize_resources: Callable[[Any], list[str]], text_present: Callable[[Any], bool]) -> None:
    global _normalize_resources, _text_present
    _normalize_resources, _text_present = normalize_resources, text_present

def _require_configured() -> tuple[Callable[[Any], list[str]], Callable[[Any], bool]]:
    if _normalize_resources is None or _text_present is None:
        raise RuntimeError("Managed-goal module was not configured by the ZzzOps entry point")
    return _normalize_resources, _text_present

def parse_managed_goal(text: str, issue_number: int | None = None) -> dict[str, Any] | None:
    pattern = re.compile(
        re.escape(GOAL_BLOCK_START) + r"\s*\n(.*?)\n" + re.escape(GOAL_BLOCK_END),
        re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        return None
    try:
        goal = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid managed goal JSON: {exc}") from exc
    errors = validate_managed_goal(goal, issue_number)
    if errors:
        raise ValueError("Invalid managed goal: " + "; ".join(errors))
    return goal


def validate_managed_goal(goal: Any, issue_number: int | None = None) -> list[str]:
    if not isinstance(goal, dict):
        return ["managed goal must be an object"]
    errors = []
    unknown = sorted(set(goal) - GOAL_FIELDS)
    if unknown:
        errors.append("unknown fields: " + ", ".join(unknown))
    if goal.get("schema_version") != GOAL_SCHEMA_VERSION:
        errors.append(f"schema_version must be {GOAL_SCHEMA_VERSION}")
    required_text = ("status", "priority", "value", "difficulty", "confidence", "next_action")
    for field in required_text:
        if not _text_present(goal.get(field)):
            errors.append(f"{field} is required")
    for field, allowed in (
        ("status", GOAL_STATUSES), ("priority", GOAL_PRIORITIES), ("value", GOAL_VALUES),
        ("difficulty", GOAL_DIFFICULTIES), ("confidence", GOAL_CONFIDENCES),
    ):
        if _text_present(goal.get(field)) and goal[field] not in allowed:
            errors.append(f"{field} is invalid")
    for field in ("depends_on", "blockers", "evidence"):
        if not isinstance(goal.get(field), list):
            errors.append(f"{field} must be a list")
    parent = goal.get("parent")
    if parent is not None and (not isinstance(parent, int) or isinstance(parent, bool) or parent < 1):
        errors.append("parent must be null or a positive issue number")
    dependencies = goal.get("depends_on")
    if isinstance(dependencies, list):
        if any(not isinstance(item, int) or isinstance(item, bool) or item < 1 for item in dependencies):
            errors.append("depends_on entries must be positive issue numbers")
        if len(set(dependencies)) != len(dependencies):
            errors.append("depends_on entries must be unique")
        if issue_number is not None and issue_number in dependencies:
            errors.append("depends_on cannot contain the current issue")
    if issue_number is not None and parent == issue_number:
        errors.append("parent cannot be the current issue")
    normalize_resources, _ = _require_configured()
    try:
        normalize_resources(goal.get("resources", []))
    except ValueError as exc:
        errors.append(str(exc))
    blockers = goal.get("blockers")
    if isinstance(blockers, list):
        for index, blocker in enumerate(blockers):
            if not isinstance(blocker, dict):
                errors.append(f"blockers[{index}] must be an object")
            elif blocker.get("status") == "open" and blocker.get("category") not in BLOCKER_CATEGORIES:
                errors.append(f"blockers[{index}].category is invalid or missing")
    rigor = goal.get("engineering_rigor")
    if rigor is not None:
        if not isinstance(rigor, dict):
            errors.append("engineering_rigor must be an object or null")
        else:
            unknown_rigor = sorted(set(rigor) - {"risk_categories", "override"})
            if unknown_rigor:
                errors.append("unknown engineering_rigor fields: " + ", ".join(unknown_rigor))
            categories = rigor.get("risk_categories")
            if not isinstance(categories, list):
                errors.append("engineering_rigor.risk_categories must be a list")
            else:
                if any(
                    not isinstance(item, str) or not item or item.casefold() != item
                    or not item.replace("_", "").isalnum()
                    for item in categories
                ):
                    errors.append("engineering_rigor.risk_categories entries must be lowercase identifiers")
                if len(categories) != len(set(categories)):
                    errors.append("engineering_rigor.risk_categories must be unique")
            override = rigor.get("override")
            if override is not None:
                if not isinstance(override, dict) or set(override) != {"level", "authority", "evidence"}:
                    errors.append("engineering_rigor.override must contain level, authority, and evidence")
                else:
                    if override.get("level") not in ENGINEERING_RIGOR_LEVELS:
                        errors.append("engineering_rigor.override.level is invalid")
                    if override.get("authority") not in ENGINEERING_RIGOR_OVERRIDE_AUTHORITIES:
                        errors.append("engineering_rigor.override.authority is invalid")
                    if not _text_present(override.get("evidence")):
                        errors.append("engineering_rigor.override.evidence is required")
    if not isinstance(goal.get("revision"), int) or isinstance(goal.get("revision"), bool) or goal.get("revision", 0) < 1:
        errors.append("revision must be a positive integer")
    implementation = goal.get("implementation")
    if implementation is not None:
        if not isinstance(implementation, dict):
            errors.append("implementation must be an object")
        else:
            for field in ("branch", "base", "target", "pr"):
                if field not in implementation or (implementation[field] is not None and not _text_present(implementation[field])):
                    errors.append(f"implementation.{field} must be null or non-empty text")
            review = implementation.get("review")
            if not isinstance(review, dict) or review.get("status") not in {"not_started", "pending", "approved", "changes_requested"}:
                errors.append("implementation.review.status is invalid")
            elif "checkpoint" not in review or (review["checkpoint"] is not None and not _text_present(review["checkpoint"])):
                errors.append("implementation.review.checkpoint must be null or non-empty text")
    return errors


def render_managed_goal(goal: dict[str, Any], body: str = "", issue_number: int | None = None) -> str:
    errors = validate_managed_goal(goal, issue_number)
    if errors:
        raise ValueError("Invalid managed goal: " + "; ".join(errors))
    block = f"{GOAL_BLOCK_START}\n{json.dumps(goal, ensure_ascii=False, sort_keys=True, separators=(',', ':'))}\n{GOAL_BLOCK_END}"
    pattern = re.compile(
        re.escape(GOAL_BLOCK_START) + r"\s*\n.*?\n" + re.escape(GOAL_BLOCK_END),
        re.DOTALL,
    )
    if pattern.search(body):
        return pattern.sub(lambda _match: block, body, count=1)
    separator = "\n\n" if body and not body.endswith("\n\n") else ""
    return f"{body}{separator}{block}\n"


def compact_human_goal_text(body: str) -> str:
    """Retain current human sections while removing explicitly historical sections."""
    human = body.split(GOAL_BLOCK_START, 1)[0].strip("\ufeff\r\n ")
    sections: list[list[str]] = []
    fence: tuple[str, int] | None = None
    for line in human.splitlines():
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = (token[0], len(token))
            elif token[0] == fence[0] and len(token) >= fence[1]:
                fence = None
        if fence is None and re.match(r"^##\s+", line) and sections and sections[-1]:
            sections.append([])
        if not sections:
            sections.append([])
        sections[-1].append(line)
    kept = []
    for section in sections:
        text = "\n".join(section).strip()
        if not text:
            continue
        heading = section[0]
        normalized = re.sub(r"\s+", " ", heading.removeprefix("##").strip()).casefold()
        if normalized in HISTORICAL_HUMAN_SECTIONS:
            continue
        kept.append(text)
    return "\n\n".join(kept) + "\n"


def compact_managed_goal(goal: dict[str, Any]) -> dict[str, Any]:
    """Project requested transition state into the current-state-only body schema."""
    compact = json.loads(json.dumps(goal))
    compact["evidence"] = []
    compact["blockers"] = [
        blocker for blocker in compact.get("blockers", [])
        if isinstance(blocker, dict) and blocker.get("status") == "open"
    ]
    return compact


def validate_compact_goal_body(body: Any, issue_number: int | None = None) -> list[str]:
    if not isinstance(body, str):
        return ["compact goal body must be text"]
    errors = []
    try:
        goal = parse_managed_goal(body, issue_number)
    except ValueError as exc:
        return [str(exc)]
    if goal is None:
        return ["managed goal block is required"]
    if goal.get("evidence"):
        errors.append("current managed state must not retain transition evidence")
    if any(not isinstance(blocker, dict) or blocker.get("status") != "open" for blocker in goal.get("blockers", [])):
        errors.append("current managed state may contain only open blockers")
    human = body.split(GOAL_BLOCK_START, 1)[0].strip("\ufeff\r\n ") + "\n"
    if compact_human_goal_text(body) != human:
        errors.append("current human text contains an explicitly historical section")
    return errors


def goal_history_id(issue_number: int, expected_digest: str, desired: dict[str, Any]) -> str:
    source = json.dumps(
        {"issue": issue_number, "expected_digest": expected_digest, "desired": compact_managed_goal(desired)},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    )
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def render_goal_history(
    issue_number: int, expected_digest: str, prior_body: str, desired: dict[str, Any],
) -> tuple[str, str]:
    """Render one lossless, deterministic append-only transition record."""
    history_id = goal_history_id(issue_number, expected_digest, desired)
    payload = {
        "schema_version": GOAL_HISTORY_SCHEMA_VERSION,
        "id": history_id,
        "issue": issue_number,
        "expected_digest": expected_digest,
        "from_revision": desired["revision"] - 1,
        "to_revision": desired["revision"],
        "prior_body": prior_body,
        "requested_goal": desired,
    }
    payload["payload_digest"] = hashlib.sha256(json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()
    block = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return history_id, (
        f"## ZzzOps transition history\n\n"
        f"Archived canonical state before revision {desired['revision']}.\n\n"
        f"{GOAL_HISTORY_BLOCK_START}\n{block}\n{GOAL_HISTORY_BLOCK_END}\n"
    )


def parse_goal_history(body: Any) -> dict[str, Any] | None:
    if not isinstance(body, str):
        return None
    pattern = re.compile(
        re.escape(GOAL_HISTORY_BLOCK_START) + r"\s*\n(.*?)\n" + re.escape(GOAL_HISTORY_BLOCK_END),
        re.DOTALL,
    )
    match = pattern.search(body)
    if not match:
        return None
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid goal history JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Invalid goal history payload")
    digest = payload.get("payload_digest")
    digest_payload = {key: value for key, value in payload.items() if key != "payload_digest"}
    calculated_digest = hashlib.sha256(json.dumps(
        digest_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()
    if (
        payload.get("schema_version") != GOAL_HISTORY_SCHEMA_VERSION
        or not isinstance(payload.get("id"), str)
        or not re.fullmatch(r"[0-9a-f]{64}", payload["id"])
        or not isinstance(payload.get("issue"), int)
        or isinstance(payload.get("issue"), bool)
        or payload["issue"] < 1
        or not isinstance(payload.get("expected_digest"), str)
        or not re.fullmatch(r"[0-9a-f]{64}", payload["expected_digest"])
        or not isinstance(payload.get("prior_body"), str)
        or not isinstance(payload.get("requested_goal"), dict)
        or not isinstance(digest, str)
        or not hmac.compare_digest(digest, calculated_digest)
        or not hmac.compare_digest(
            payload["id"], goal_history_id(payload["issue"], payload["expected_digest"], payload["requested_goal"])
        )
    ):
        raise ValueError("Invalid goal history payload")
    return payload


def goal_needs_human(goal: dict[str, Any]) -> bool:
    return any(
        isinstance(blocker, dict)
        and blocker.get("status") == "open"
        and blocker.get("category") in BLOCKER_CATEGORIES
        for blocker in goal.get("blockers", [])
    )


def validate_github_issue_goal(issue_number: Any, title: Any, body: Any) -> list[str]:
    errors = []
    if not isinstance(issue_number, int) or isinstance(issue_number, bool) or issue_number < 1:
        errors.append("issue_number must be a positive integer")
    if not _text_present(title):
        errors.append("title is required")
    elif REDUNDANT_GOAL_TITLE_PREFIX.match(title):
        errors.append("title must not contain a redundant ZzzOps goal ID")
    if not isinstance(body, str):
        return errors + ["body must be text"]
    human = body.split(GOAL_BLOCK_START, 1)[0].lstrip("\ufeff\r\n ")
    if not human:
        errors.append("human-readable content must precede managed state")
    elif human.startswith("---"):
        errors.append("human-readable content must not start with rendered frontmatter")
    elif not human.startswith("## "):
        errors.append("human-readable content must start with a section heading")
    try:
        goal = parse_managed_goal(body, issue_number if isinstance(issue_number, int) else None)
    except ValueError as exc:
        errors.append(str(exc))
    else:
        if goal is None:
            errors.append("managed goal block is required")
    return errors


def github_goal_record(issue: dict[str, Any]) -> dict[str, Any]:
    number = issue.get("number")
    body = issue.get("body") or ""
    goal = parse_managed_goal(body, number)
    if goal is None:
        raise ValueError("managed goal block is required")
    errors = validate_github_issue_goal(number, issue.get("title"), body)
    if errors:
        raise ValueError("; ".join(errors))
    label_names = sorted(
        label["name"] for label in issue.get("labels", [])
        if isinstance(label, dict) and _text_present(label.get("name"))
    )
    schema_versions = [
        int(label.removeprefix(GOAL_SCHEMA_LABEL_PREFIX))
        for label in label_names
        if label.startswith(GOAL_SCHEMA_LABEL_PREFIX) and label.removeprefix(GOAL_SCHEMA_LABEL_PREFIX).isdigit()
    ]
    digest_source = "\0".join((issue.get("title") or "", body))
    return {
        "key": number, "title": issue["title"], "status": goal["status"],
        "priority": goal["priority"], "value": goal["value"], "difficulty": goal["difficulty"],
        "confidence": goal["confidence"], "parent": goal["parent"],
        "depends_on": goal["depends_on"], "claim": goal["claim"], "resources": goal.get("resources", []),
        "needs_human": goal_needs_human(goal),
        "blocker_categories": sorted({blocker["category"] for blocker in goal["blockers"] if blocker.get("status") == "open"}),
        "next_action": goal["next_action"], "revision": goal["revision"],
        "digest": hashlib.sha256(digest_source.encode("utf-8")).hexdigest(),
        "updated_at": issue.get("updated_at"), "implementation": goal.get("implementation"),
        "engineering_rigor": goal.get("engineering_rigor"),
        "labels": label_names, "schema_version": schema_versions[0] if len(schema_versions) == 1 else None,
        "state": issue.get("state"), "url": issue.get("html_url"),
    }


def current_goal_schema_label() -> str:
    return f"{GOAL_SCHEMA_LABEL_PREFIX}{GOAL_SCHEMA_VERSION}"


def github_archived_goal_record(issue: dict[str, Any]) -> dict[str, Any]:
    """Project one closed goal from discovery labels without hydrating its body."""
    labels = sorted(
        label["name"] for label in issue.get("labels", [])
        if isinstance(label, dict) and isinstance(label.get("name"), str)
    )
    statuses = [label.removeprefix("zzzops:status:") for label in labels if label.startswith("zzzops:status:")]
    priorities = [label.removeprefix("zzzops:priority:") for label in labels if label.startswith("zzzops:priority:")]
    if len(statuses) != 1 or statuses[0] not in {"done", "cancelled"}:
        raise ValueError("closed goal requires exactly one terminal status label")
    if len(priorities) != 1 or priorities[0] not in GOAL_PRIORITIES:
        raise ValueError("closed goal requires exactly one valid priority label")
    if str(issue.get("state", "")).casefold() != "closed":
        raise ValueError("archived goal projection requires a closed issue")
    digest_source = json.dumps(
        {
            "number": issue.get("number"), "title": issue.get("title"), "state": "closed",
            "labels": labels, "schema_version": issue.get("schema_version"),
        },
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    )
    return {
        "key": issue.get("number"), "title": issue.get("title"), "status": statuses[0],
        "priority": priorities[0], "value": None, "difficulty": None, "confidence": None,
        "parent": None, "depends_on": [], "claim": None, "resources": [], "needs_human": False,
        "blocker_categories": [], "next_action": None,
        "revision": None, "digest": hashlib.sha256(digest_source.encode("utf-8")).hexdigest(),
        "updated_at": None, "implementation": None, "labels": labels, "state": "closed",
        "url": issue.get("html_url"), "schema_version": issue.get("schema_version"),
        "engineering_rigor": None,
    }


def validate_goal_create(request: Any) -> list[str]:
    if not isinstance(request, dict):
        return ["goal create request must be an object"]
    errors = []
    unknown = sorted(set(request) - GOAL_CREATE_FIELDS)
    missing = sorted(GOAL_CREATE_FIELDS - set(request))
    if unknown:
        errors.append("unknown goal create fields: " + ", ".join(unknown))
    if missing:
        errors.append("missing goal create fields: " + ", ".join(missing))
    if request.get("schema_version") != GOAL_CREATE_SCHEMA_VERSION:
        errors.append(f"goal create schema_version must be {GOAL_CREATE_SCHEMA_VERSION}")
    title = request.get("title")
    if not isinstance(title, str) or not title.strip():
        errors.append("title is required")
    elif title != title.strip():
        errors.append("title must be trimmed")
    elif len(title) > 256:
        errors.append("title must be at most 256 characters")
    elif REDUNDANT_GOAL_TITLE_PREFIX.match(title):
        errors.append("title must not include a generated goal identifier")
    body = request.get("body")
    if not isinstance(body, str) or not body.strip():
        errors.append("body is required")
    elif GOAL_BLOCK_START in body or GOAL_BLOCK_END in body:
        errors.append("body must not contain a managed goal block")
    labels = request.get("labels")
    if not isinstance(labels, list):
        errors.append("labels must be a list")
    else:
        invalid_labels = [
            label for label in labels
            if not isinstance(label, str) or not label.strip() or label != label.strip() or len(label) > 50
            or label == "zzzops" or label.startswith("zzzops:")
        ]
        if invalid_labels:
            errors.append("labels must be trimmed non-ZzzOps label names")
        if len({label.casefold() for label in labels if isinstance(label, str)}) != len(labels):
            errors.append("labels must be unique")
    goal = request.get("goal")
    errors.extend(validate_managed_goal(goal))
    if isinstance(goal, dict):
        if goal.get("status") != "new":
            errors.append("newly created goals must have status new")
        if goal.get("revision") != 1:
            errors.append("newly created goals must have revision 1")
        if goal.get("claim") is not None:
            errors.append("newly created goals must not have a claim")
        if goal.get("implementation") is not None:
            errors.append("newly created goals must not have implementation state")
    return errors


def load_goal_create(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.resolve().read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read goal create request: {type(exc).__name__}") from exc


def apply_goal_create(adapter: Any, repository: str, request: dict[str, Any]) -> dict[str, Any]:
    errors = validate_goal_create(request)
    if errors:
        raise ValueError("Invalid goal create request: " + "; ".join(errors))
    if adapter.repository.casefold() != repository.casefold():
        raise GoalTransitionProviderError("Repository identity changed; no goal was created.")
    goal = request["goal"]
    body = render_managed_goal(goal, request["body"])
    if len(body) > 65536:
        raise ValueError("Rendered goal body exceeds GitHub's issue limit")
    labels = [
        "zzzops", *request["labels"], current_goal_schema_label(),
        f"zzzops:status:{goal['status']}", f"zzzops:priority:{goal['priority']}",
    ]
    created = adapter.create_issue({"title": request["title"], "body": body, "labels": labels})
    if not isinstance(created, dict):
        raise GoalTransitionProviderError(
            "GitHub returned an unexpected goal-create response; success was not assumed."
        )
    number = created.get("number")
    expected_url = f"https://github.com/{repository}/issues/{number}"
    returned_label_items = created.get("labels")
    returned_labels = None if not isinstance(returned_label_items, list) else {
        label["name"] for label in returned_label_items
        if isinstance(label, dict) and isinstance(label.get("name"), str)
    }
    try:
        returned_goal = parse_managed_goal(created.get("body"), number)
    except (TypeError, ValueError) as exc:
        raise GoalTransitionProviderError(
            "GitHub returned an unexpected goal-create response; success was not assumed."
        ) from exc
    if (
        not isinstance(number, int) or isinstance(number, bool) or number < 1
        or created.get("title") != request["title"]
        or created.get("body") != body
        or str(created.get("state", "")).casefold() != "open"
        or returned_labels != set(labels)
        or created.get("html_url") != expected_url
        or returned_goal != goal
    ):
        raise GoalTransitionProviderError(
            "GitHub returned an unexpected goal-create response; success was not assumed."
        )
    return {
        "number": number, "revision": 1, "state": "open", "status": "new", "url": expected_url,
    }


def validate_goal_transition(transition: Any, issue_number: int) -> list[str]:
    if not isinstance(transition, dict):
        return ["transition must be an object"]
    errors = []
    unknown = sorted(set(transition) - GOAL_TRANSITION_FIELDS)
    missing = sorted(GOAL_TRANSITION_FIELDS - set(transition))
    if unknown:
        errors.append("unknown transition fields: " + ", ".join(unknown))
    if missing:
        errors.append("missing transition fields: " + ", ".join(missing))
    if transition.get("schema_version") != GOAL_TRANSITION_SCHEMA_VERSION:
        errors.append(f"transition schema_version must be {GOAL_TRANSITION_SCHEMA_VERSION}")
    expected_revision = transition.get("expected_revision")
    if not isinstance(expected_revision, int) or isinstance(expected_revision, bool) or expected_revision < 1:
        errors.append("expected_revision must be a positive integer")
    digest = transition.get("expected_digest")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        errors.append("expected_digest must be the 64-character checkpoint goal digest")
    goal = transition.get("goal")
    errors.extend(validate_managed_goal(goal, issue_number))
    if (
        isinstance(goal, dict) and isinstance(expected_revision, int)
        and not isinstance(expected_revision, bool) and goal.get("revision") != expected_revision + 1
    ):
        errors.append("goal revision must increment expected_revision by exactly one")
    return errors


def load_goal_transition(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.resolve().read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read goal transition: {type(exc).__name__}") from exc


def apply_goal_transition(
    adapter: Any, repository: str, issue_number: int, transition: dict[str, Any],
) -> dict[str, Any]:
    errors = validate_goal_transition(transition, issue_number)
    if errors:
        raise ValueError("Invalid goal transition: " + "; ".join(errors))
    if adapter.repository.casefold() != repository.casefold():
        raise GoalTransitionProviderError("Repository identity changed; no goal update was made.")
    issue = adapter.get_issue(issue_number)
    try:
        record = github_goal_record(issue)
    except ValueError as exc:
        raise GoalTransitionProviderError("The current goal could not be validated; no goal update was made.") from exc
    requested = transition["goal"]
    desired = compact_managed_goal(requested)
    history_id = goal_history_id(issue_number, transition["expected_digest"], requested)
    comments = adapter.get_issue_comments(issue_number)
    histories = []
    for comment in comments:
        try:
            history = parse_goal_history(comment.get("body") if isinstance(comment, dict) else None)
        except ValueError as exc:
            raise GoalTransitionProviderError("The selected goal has malformed transition history; no update was made.") from exc
        if history is not None and history.get("id") == history_id:
            histories.append((comment, history))
    if len(histories) > 1:
        raise GoalTransitionProviderError("The selected goal has duplicate transition history; no update was made.")

    state = "closed" if desired["status"] in {"done", "cancelled"} else "open"
    if record["revision"] == desired["revision"]:
        compact_body = render_managed_goal(desired, compact_human_goal_text(issue["body"]), issue_number)
        returned_labels = {
            label["name"] for label in issue.get("labels", [])
            if isinstance(label, dict) and isinstance(label.get("name"), str)
        }
        if (
            issue.get("body") == compact_body
            and str(issue.get("state", "")).casefold() == state
            and current_goal_schema_label() in returned_labels
            and f"zzzops:status:{desired['status']}" in returned_labels
            and f"zzzops:priority:{desired['priority']}" in returned_labels
            and len(histories) == 1
            and histories[0][1].get("issue") == issue_number
            and histories[0][1].get("to_revision") == desired["revision"]
            and histories[0][1].get("requested_goal") == requested
        ):
            return {
                "number": issue_number, "revision": desired["revision"], "state": state,
                "status": desired["status"], "url": f"https://github.com/{repository}/issues/{issue_number}",
            }
        raise ValueError(f"Goal #{issue_number} changed; the requested transition was not confirmed.")

    if record["revision"] != transition["expected_revision"]:
        raise ValueError(
            f"Goal #{issue_number} changed from revision {transition['expected_revision']} to {record['revision']}; no update was made."
        )
    if not hmac.compare_digest(record["digest"], transition["expected_digest"]):
        raise ValueError(f"Goal #{issue_number} digest changed; no update was made.")

    body = render_managed_goal(desired, compact_human_goal_text(issue["body"]), issue_number)
    compact_errors = validate_compact_goal_body(body, issue_number)
    if compact_errors:
        raise ValueError("Invalid compact goal body: " + "; ".join(compact_errors))
    _, history_body = render_goal_history(
        issue_number, transition["expected_digest"], issue["body"], requested,
    )
    if len(history_body) > 65536:
        raise GoalTransitionProviderError("Transition history exceeds GitHub's comment limit; no update was made.")
    if histories:
        if histories[0][0].get("body") != history_body:
            raise GoalTransitionProviderError("Existing transition history does not match the requested update.")
    else:
        created = adapter.create_issue_comment(issue_number, history_body)
        if created.get("body") != history_body or not isinstance(created.get("html_url"), str):
            raise GoalTransitionProviderError(
                "GitHub did not confirm exact transition history; body replacement was not attempted."
            )
    _, text_present = _require_configured()
    retained_labels = sorted({
        label["name"] for label in issue.get("labels", [])
        if isinstance(label, dict) and text_present(label.get("name"))
        and label["name"] != "zzzops"
        and not label["name"].startswith("zzzops:status:")
        and not label["name"].startswith("zzzops:priority:")
        and not label["name"].startswith(GOAL_SCHEMA_LABEL_PREFIX)
    })
    labels = [
       #�4��$z{-���jםlable[[Path | None], dict[str, str]] | None = None


def configure_entrypoint(*, package_provenance: Callable[[Path | None], dict[str, str]]) -> None:
    global _package_provenance
    _package_provenance = package_provenance


def policy_default_content(section: dict[str, Any]) -> dict[str, Any]:
    return {
        field: json.loads(json.dumps(section.get(field), ensure_ascii=False))
        for field in POLICY_DEFAULT_CONTENT_FIELDS
    }


def policy_content_digest(content: Any) -> str:
    canonical = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def policy_section_review_content(section: dict[str, Any], evidence: list[dict[str, Any]]) -> dict[str, Any]:
    content = {key: value for key, value in section.items() if key != "review"}
    sources = set(section.get("source_ids", []))
    content["source_evidence"] = sorted(
        (item for item in evidence if item.get("id") in sources), key=lambda item: item["id"],
    )
    return json.loads(json.dumps(content, ensure_ascii=False, sort_keys=True))


def policy_default_catalog() -> dict[str, dict[str, Any]]:
    template = Path(__file__).parent / "templates" / "project-goals" / "INIT_PLAN.json"
    data = json.loads(template.read_text(encoding="utf-8-sig"))
    catalog: dict[str, dict[str, Any]] = {}
    for section in data["policy"]["sections"]:
        default_id = section["default_id"]
        if default_id in catalog:
            raise ValueError(f"duplicate policy default id: {default_id}")
        content = policy_default_content(section)
        catalog[default_id] = {
            "id": default_id,
            "schema_version": POLICY_DEFAULT_SCHEMA_VERSION,
            "section_id": section["id"],
            "content": content,
            "digest": policy_content_digest(content),
        }
    return dict(sorted(catalog.items()))


def machinery_provenance(repo: Path) -> dict[str, str]:
    if _package_provenance is None:
        raise RuntimeError("Policy module was not configured with Agent Plugin provenance")
    return _package_provenance(repo)


def _adopted_provenance(entry: dict[str, Any], source: dict[str, str]) -> dict[str, Any]:
    return {
        "status": "adopted", "default_id": entry["id"],
        "schema_version": entry["schema_version"], "source": source,
        "digest": entry["digest"], "snapshot": json.loads(json.dumps(entry["content"])),
    }


def prepare_policy_defaults(
    repo: Path, policy: dict[str, Any], previous_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    prepared = json.loads(json.dumps(policy))
    catalog = policy_default_catalog()
    previous = {
        section["id"]: section for section in (previous_policy or {}).get("sections", [])
        if isinstance(section, dict) and text_present(section.get("id"))
    }
    source: dict[str, str] | None = None
    for section in prepared.get("sections", []):
        if not isinstance(section, dict):
            continue
        section_id = section.get("id")
        default_id = section.pop("default_id", None)
        resolution = section.pop("default_resolution", None)
        prior = previous.get(section_id)
        provenance = section.get("default_provenance")
        if prior is not None:
            provenance = json.loads(json.dumps(prior["default_provenance"])) if "default_provenance" in prior else None
        if provenance is not None and not isinstance(provenance, dict):
            raise ValueError(f"policy section {section_id} default provenance must be an object")
        if prior is None and default_id is None and not (isinstance(provenance, dict) and provenance.get("default_id")):
            raise ValueError(f"policy section {section_id} lacks a stable default identity")
        entry = catalog.get(default_id or (provenance or {}).get("default_id"))
        if entry is not None and entry["section_id"] != section_id:
            raise ValueError(f"policy section {section_id} uses a default for {entry['section_id']}")
        if resolution is not None:
            if not isinstance(resolution, dict) or resolution.get("action") not in {"accept", "decline"} or entry is None:
                raise ValueError(f"policy section {section_id} has an invalid default resolution")
            if resolution.get("digest") != entry["digest"]:
                raise ValueError(f"policy section {section_id} default resolution is stale")
            if resolution["action"] == "accept":
                for field, value in entry["content"].items():
                    section[field] = json.loads(json.dumps(value))
                source = source or machinery_provenance(repo)
                provenance = _adopted_provenance(entry, source)
                section["default_disposition"] = "accepted"
            else:
                if not isinstance(provenance, dict) or provenance.get("status") != "adopted":
                    raise ValueError(f"policy section {section_id} cannot decline a default without adopted provenance")
                provenance["declined_digest"] = entry["digest"]
        elif provenance is None:
            if prior is not None:
                provenance = None
            elif default_id is None or section.get("default_disposition") == "unknown":
                provenance = {"status": "unknown"}
            elif entry is None:
                raise ValueError(f"policy section {section_id} references an unknown default")
            elif section.get("default_disposition") == "accepted":
                if policy_default_content(section) != entry["content"]:
                    raise ValueError(f"policy section {section_id} accepted default content is inconsistent")
                source = source or machinery_provenance(repo)
                provenance = _adopted_provenance(entry, source)
            else:
                source = source or machinery_provenance(repo)
                provenance = {
                    "status": "customized", "default_id": entry["id"],
                    "schema_version": entry["schema_version"], "source": source,
                    "catalog_digest": entry["digest"],
                }
        elif prior is None and provenance.get("status") in {"adopted", "customized"}:
            if entry is None:
                raise ValueError(f"policy section {section_id} references an unknown default")
            source = source or machinery_provenance(repo)
            expected_digest = provenance.get("digest") if provenance.get("status") == "adopted" else provenance.get("catalog_digest")
            if expected_digest != entry["digest"] or provenance.get("source") != source:
                raise ValueError(f"policy section {section_id} default provenance does not match installed machinery")
        elif provenance.get("status") == "adopted" and policy_default_content(section) != provenance.get("snapshot"):
            provenance = {
                "status": "customized", "default_id": provenance.get("default_id"),
                "schema_version": provenance.get("schema_version"), "source": provenance.get("source"),
                "catalog_digest": provenance.get("digest"),
            }
            section["default_disposition"] = "changed"
        if provenance is None:
            section.pop("default_provenance", None)
        else:
            section["default_provenance"] = provenance
    return prepared


def compare_policy_defaults(
    policy: dict[str, Any], catalog: dict[str, dict[str, Any]] | None = None,
    selected_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    catalog = catalog or policy_default_catalog()
    selected_ids = selected_ids or set()
    result = []
    for section in policy.get("sections", []):
        section_id = section.get("id")
        provenance = section.get("default_provenance")
        item: dict[str, Any] = {"section_id": section_id}
        if not isinstance(provenance, dict) or provenance.get("status") == "unknown":
            item["status"] = "unknown_origin"
        elif provenance.get("status") == "customized" or policy_default_content(section) != provenance.get("snapshot"):
            item.update({"status": "customized", "default_id": provenance.get("default_id")})
        else:
            entry = catalog.get(provenance.get("default_id"))
            if entry is None:
                item.update({"status": "unknown_default", "default_id": provenance.get("default_id")})
            elif provenance.get("digest") == entry["digest"]:
                item.update({"status": "current", "default_id": entry["id"], "digest": entry["digest"]})
            elif provenance.get("declined_digest") == entry["digest"]:
                item.update({"status": "declined", "default_id": entry["id"], "old_digest": provenance.get("digest"), "new_digest": entry["digest"]})
            else:
                item.update({"status": "update_available", "default_id": entry["id"], "old_digest": provenance.get("digest"), "new_digest": entry["digest"]})
                if section_id in selected_ids:
                    item["old_snapshot"] = provenance.get("snapshot")
                    item["new_snapshot"] = entry["content"]
        result.append(item)
    return result


def _digest_text(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 71 and value.startswith("sha256:") and all(
        character in "0123456789abcdef" for character in value[7:]
    )


def validate_default_provenance(section: dict[str, Any], prefix: str) -> list[str]:
    provenance = section.get("default_provenance")
    if provenance is None:
        return []  # Legacy reviewed policy: never infer provenance from value equality.
    if not isinstance(provenance, dict):
        return [f"{prefix}.default_provenance must be an object"]
    status = provenance.get("status")
    if status == "unknown":
        return [] if set(provenance) == {"status"} else [f"{prefix}.default_provenance unknown origin must contain only status"]
    if status not in {"adopted", "customized"}:
        return [f"{prefix}.default_provenance.status is invalid"]
    errors = []
    expected_fields = {
        "adopted": {"status", "default_id", "schema_version", "source", "digest", "snapshot"},
        "customized": {"status", "default_id", "schema_version", "source", "catalog_digest"},
    }[status]
    if status == "adopted" and "declined_digest" in provenance:
        expected_fields.add("declined_digest")
    if set(provenance) != expected_fields:
        errors.append(f"{prefix}.default_provenance contains non-canonical fields")
    default_id = provenance.get("default_id")
    if default_id != f"zzzops.policy.{section.get('id')}":
        errors.append(f"{prefix}.default_provenance.default_id is inconsistent")
    if provenance.get("schema_version") != POLICY_DEFAULT_SCHEMA_VERSION:
        errors.append(f"{prefix}.default_provenance.schema_version must be {POLICY_DEFAULT_SCHEMA_VERSION}")
    source = provenance.get("source")
    revision = source.get("revision") if isinstance(source, dict) else None
    if (
        not isinstance(source, dict) or set(source) != {"revision", "version"}
        or not text_present(source.get("version"))
        or not isinstance(revision, str) or len(revision) not in {40, 64}
        or any(character not in "0123456789abcdef" for character in revision)
    ):
        errors.append(f"{prefix}.default_provenance.source requires revision and version")
    digest_field = "digest" if status == "adopted" else "catalog_digest"
    if not _digest_text(provenance.get(digest_field)):
        errors.append(f"{prefix}.default_provenance.{digest_field} is invalid")
    if status == "adopted":
        snapshot = provenance.get("snapshot")
        if not isinstance(snapshot, dict) or set(snapshot) != set(POLICY_DEFAULT_CONTENT_FIELDS):
            errors.append(f"{prefix}.default_provenance.snapshot must contain the complete canonical default")
        elif policy_content_digest(snapshot) != provenance.get("digest"):
            errors.append(f"{prefix}.default_provenance.digest does not match snapshot")
        elif policy_default_content(section) != snapshot:
            errors.append(f"{prefix}.default_provenance snapshot differs from effective policy")
        if "declined_digest" in provenance and not _digest_text(provenance["declined_digest"]):
            errors.append(f"{prefix}.default_provenance.declined_digest is invalid")
    return errors


def default_provenance_label(section: dict[str, Any]) -> str:
    status = (section.get("default_provenance") or {}).get("status")
    return {
        "adopted": "adopted from the recorded ZzzOps default",
        "customized": "customized from a ZzzOps default",
    }.get(status, "default origin unknown")


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value.strip().casefold() != "unknown"


def text_present(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def nonempty_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(nonempty(item) for item in value)


def normalize_resources(resources: Any) -> list[str]:
    if not isinstance(resources, list):
        raise ValueError("resources must be a list")
    normalized = []
    for resource in resources:
        if not isinstance(resource, str):
            raise ValueError("resource entries must be text")
        value = resource.strip().replace("\\", "/")
        prefix, separator, target = value.partition(":")
        prefix = prefix.casefold()
        if prefix not in {"path", "branch", "integration", "generated", "external"} or not separator or not target:
            raise ValueError("resources must use path, branch, integration, generated, or external prefixes")
        if len(value) > 200 or any(ord(character) < 32 for character in value):
            raise ValueError("resource entries must be at most 200 printable characters")
        normalized.append(value.casefold())
    if len(normalized) != len(set(normalized)):
        raise ValueError("resource entries must be unique")
    return sorted(normalized)


def normalize_resource_policy(policy: Any = None) -> dict[str, Any]:
    if policy is None:
        raise ValueError("reviewed resource_reservations policy is required")
    if not isinstance(policy, dict):
        raise ValueError("resource_reservations must be an object")
    unknown = sorted(set(policy) - {"mode", "exclusive_prefixes", "exclusive_resources"})
    if unknown:
        raise ValueError("resource_reservations has unknown fields: " + ", ".join(unknown))
    mode = policy.get("mode")
    if mode not in {"conflict_tolerant", "strict"}:
        raise ValueError("resource_reservations.mode must be conflict_tolerant or strict")
    prefixes = policy.get("exclusive_prefixes")
    supported = {"path", "integration", "generated", "external"}
    if (
        not isinstance(prefixes, list)
        or any(not isinstance(prefix, str) or prefix not in supported for prefix in prefixes)
        or len(prefixes) != len(set(prefixes))
    ):
        raise ValueError("resource_reservations.exclusive_prefixes must contain unique supported prefixes")
    if "exclusive_resources" not in policy:
        raise ValueError("resource_reservations.exclusive_resources is required")
    resources = normalize_resources(policy["exclusive_resources"])
    return {"mode": mode, "exclusive_prefixes": sorted(prefixes), "exclusive_resources": resources}


def exclusive_resources(resources: Any, policy: Any = None) -> list[str]:
    resources = normalize_resources(resources)
    if not resources:
        return []
    if policy is None and all(resource.startswith("branch:") for resource in resources):
        return resources  # Branch identity is invariant, not a project-policy selection.
    policy = normalize_resource_policy(policy)
    if policy["mode"] == "strict":
        return resources
    exact = set(policy["exclusive_resources"])
    prefixes = set(policy["exclusive_prefixes"])
    return [
        resource for resource in resources
        if resource.startswith("branch:") or resource in exact or resource.partition(":")[0] in prefixes
    ]


def _missing_setting_paths(current: Any, expected: Any, prefix: str = "settings") -> list[str]:
    if not isinstance(expected, dict):
        return []
    if not isinstance(current, dict):
        return [prefix]
    missing = []
    for key, value in expected.items():
        path = f"{prefix}.{key}"
        if key not in current:
            missing.append(path)
        else:
            missing.extend(_missing_setting_paths(current[key], value, path))
    return missing


def missing_policy_settings(
    policy: dict[str, Any], catalog: dict[str, dict[str, Any]] | None = None,
) -> dict[str, list[str]]:
    """Return absent operational settings without filling them from shipped defaults."""
    catalog = policy_default_catalog() if catalog is None else catalog
    by_section = {
        entry["section_id"]: entry for entry in catalog.values()
        if isinstance(entry, dict) and entry.get("section_id") in POLICY_SECTION_IDS
    }
    result = {}
    for section in policy.get("sections", []):
        if not isinstance(section, dict) or section.get("id") not in by_section:
            continue
        section_id = section["id"]
        expected = by_section[section_id].get("content", {}).get("settings", {})
        missing = _missing_setting_paths(section.get("settings"), expected)
        if missing:
            result[section_id] = missing
    return result


def project_digest(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def project_path(repo: Path) -> Path:
    return repo / ".zzzops" / "PROJECT.md"


def project_audit_path(repo: Path) -> Path:
    return repo / PROJECT_AUDIT_RELATIVE


def project_policy_path(repo: Path) -> Path:
    return repo / PROJECT_POLICY_RELATIVE


def read_project(repo: Path) -> tuple[Path, str]:
    path = project_path(repo)
    try:
        return path, path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        return path, ""
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"Cannot read project charter from {path}: {exc}") from exc


def parse_policy_state(text: str) -> dict[str, Any]:
    try:
        state = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid canonical policy JSON: {exc}") from exc
    if not isinstance(state, dict):
        raise ValueError("Canonical policy state must be a JSON object")
    return state


def read_policy_text(repo: Path) -> tuple[Path, str]:
    path = project_policy_path(repo)
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        return path, ""
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"Cannot read canonical policy from {path}: {exc}") from exc
    return path, text


def read_project_state(repo: Path) -> tuple[Path, str, dict[str, Any] | None]:
    path, text = read_policy_text(repo)
    if not text:
        return path, text, None
    return path, text, parse_policy_state(text)


def initialization_base_digest(repo: Path) -> str:
    _project_path, project_text = read_project(repo)
    _policy_path, policy_text = read_policy_text(repo)
    return project_digest(project_text + "\0" + policy_text)


def policy_review_digest(state: dict[str, Any]) -> str:
    reviewable = {key: value for key, value in state.items() if key != "approval"}
    payload = json.dumps(reviewable, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return project_digest(payload)


def validate_project_state(state: Any) -> list[str]:
    if not isinstance(state, dict):
        return ["project state must be an object"]
    allowed = {"schema_version", "initialized", "backend", "repository", "revision", "charter", "policy", "history", "bindings", "approval"}
    errors = []
    unknown = sorted(set(state) - allowed)
    if unknown:
        errors.append("unknown fields: " + ", ".join(unknown))
    if state.get("schema_version") != PROJECT_SCHEMA_VERSION:
        errors.append(f"schema_version must be {PROJECT_SCHEMA_VERSION}")
    if not isinstance(state.get("initialized"), bool):
        errors.append("initialized must be boolean")
    if not isinstance(state.get("revision"), int) or isinstance(state.get("revision"), bool) or state.get("revision", -1) < 0:
        errors.append("revision must be a non-negative integer")
    policy_errors = validate_policy(state.get("policy"), require_pending=False) if state.get("policy") is not None else []
    errors.extend(f"policy.{error}" for error in policy_errors)
    pending_policy = policy_blockers(state.get("policy")) if not policy_errors else []
    if state.get("initialized") is True:
        if state.get("backend") not in BACKENDS:
            errors.append("initialized backend must be github_issues")
        repository = state.get("repository")
        if not isinstance(repository, dict) or not nonempty(repository.get("identity")):
            errors.append("initialized repository.identity is required")
        if pending_policy:
            errors.append("initialized state cannot have unreviewed required policy: " + ", ".join(pending_policy))
        approval = state.get("approval")
        if not isinstance(approval, dict) or not text_present(approval.get("reviewer")) or not text_present(approval.get("date")):
            errors.append("initialized state requires explicit approval metadata")
        elif approval.get("digest") != policy_review_digest(state):
            errors.append("policy approval digest changed")
    elif state.get("backend") is not None or state.get("repository") is not None or state.get("policy") is not None:
        if state.get("backend") not in BACKENDS or not isinstance(state.get("repository"), dict) or not state.get("policy"):
            errors.append("uninitialized state may select a backend only as a complete pending policy draft")
    bindings = state.get("bindings")
    if not isinstance(bindings, dict):
        errors.append("bindings must be an object")
    else:
        for name, expected_path in (("project", ".zzzops/PROJECT.md"), ("audit", PROJECT_AUDIT_RELATIVE)):
            binding = bindings.get(name)
            if not isinstance(binding, dict) or binding.get("path") != expected_path or not text_present(binding.get("digest")):
                errors.append(f"bindings.{name} must contain the canonical path and digest")
    history = state.get("history")
    if not isinstance(history, list) or not history:
        errors.append("history must be a non-empty list")
    else:
        for index, entry in enumerate(history):
            if not isinstance(entry, dict) or any(not text_present(entry.get(key)) for key in ("date", "actor", "change", "reason")):
                errors.append(f"history[{index}] requires date, actor, change, and reason")
    return errors


def validate_project_artifacts(repo: Path, state: dict[str, Any] | None) -> list[str]:
    if not isinstance(state, dict):
        return []
    bindings = state.get("bindings")
    if not isinstance(bindings, dict):
        return []
    errors = []
    for name, path in (("project", project_path(repo)), ("audit", project_audit_path(repo))):
        binding = bindings.get(name)
        if not isinstance(binding, dict) or not text_present(binding.get("digest")):
            continue
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError):
            errors.append(f"{name} policy artifact is unavailable")
            continue
        if project_digest(text) != binding["digest"]:
            errors.append(f"{name} policy artifact digest changed")
    return errors


def validate_policy(policy: Any, require_pending: bool) -> list[str]:
    if not isinstance(policy, dict):
        return ["must be an object"]
    errors = []
    if policy.get("schema_version") != POLICY_SCHEMA_VERSION:
        errors.append(f"schema_version must be {POLICY_SCHEMA_VERSION}")
    sections = policy.get("sections")
    if not isinstance(sections, list):
        return errors + ["sections must be a list"]
    evidence_ids = set()
    if not require_pending:
        evidence = policy.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append("evidence must be a non-empty list")
        else:
            for index, item in enumerate(evidence):
                if not isinstance(item, dict) or not text_present(item.get("id")) or not text_present(item.get("source")) or not text_present(item.get("finding")):
                    errors.append(f"evidence[{index}] requires id, source, and finding")
                elif item["id"] in evidence_ids:
                    errors.append(f"evidence[{index}].id must be unique")
                else:
                    evidence_ids.add(item["id"])
    seen = set()
    for index, section in enumerate(sections):
        prefix = f"sections[{index}]"
        if not isinstance(section, dict):
            errors.append(f"{prefix} must be an object")
            continue
        section_id = section.get("id")
        if section_id not in POLICY_SECTION_IDS or section_id in seen:
            errors.append(f"{prefix}.id must be unique and from the current taxonomy")
        else:
            seen.add(section_id)
        if section.get("default_id") is not None and section.get("default_id") != f"zzzops.policy.{section_id}":
            errors.append(f"{prefix}.default_id is inconsistent")
        for field in ("title", "decision", "rationale", "confidence", "default_origin", "default_disposition"):
            if not text_present(section.get(field)):
                errors.append(f"{prefix}.{field} is required")
        if section.get("confidence") not in {"low", "medium", "high"}:
            errors.append(f"{prefix}.confidence must be low, medium, or high")
        if section.get("default_disposition") not in {"accepted", "changed", "rejected", "unknown"}:
            errors.append(f"{prefix}.default_disposition must be accepted, changed, rejected, or unknown")
        if not isinstance(section.get("required"), bool) or not isinstance(section.get("applicable"), bool):
            errors.append(f"{prefix}.required and applicable must be booleans")
        for field in ("source_ids", "exceptions", "unresolved"):
            if not isinstance(section.get(field), list):
                errors.append(f"{prefix}.{field} must be a list")
        if not require_pending and isinstance(section.get("source_ids"), list):
            missing_sources = sorted(set(section["source_ids"]) - evidence_ids)
            if missing_sources:
                errors.append(f"{prefix}.source_ids missing citations: {', '.join(missing_sources)}")
        if not isinstance(section.get("settings"), dict):
            errors.append(f"{prefix}.settings must be an object")
        elif section_id == "git_review_release":
            settings = section["settings"]
            for field, allowed in GIT_REVIEW_SETTING_VALUES.items():
                if settings.get(field) not in allowed:
                    errors.append(f"{prefix}.git_review_release.settings.{field} is invalid")
            if settings.get("review_gate") == "human_at_exhaustion" and (
                settings.get("review_pending_dependency") != "stack_from_reviewed_checkpoint"
                or settings.get("conversational_approval") != "never_for_goal_progress"
            ):
                errors.append(
                    f"{prefix}.git_review_release exhaustion review requires checkpoint stacking "
                    "and no conversational goal approval"
                )
        elif section_id == "engineering_rigor":
            settings = section["settings"]
            if section.get("decision") not in ENGINEERING_RIGOR_LEVELS:
                errors.append(f"{prefix}.engineering_rigor.decision must be vibe, structured, or agentic")
            if set(settings) != {"escalation", "minimums", "overrides", "requirements_interview"}:
                errors.append(f"{prefix}.engineering_rigor.settings must contain the bounded rigor contract")
            escalation = settings.get("escalation")
            if not isinstance(escalation, dict) or set(escalation) != {
                "enabled", "allow_automatic_escalation", "allow_automatic_deescalation",
            }:
                errors.append(f"{prefix}.engineering_rigor.escalation is invalid")
            else:
                for field in ("enabled", "allow_automatic_escalation"):
                    if not isinstance(escalation.get(field), bool):
                        errors.append(f"{prefix}.engineering_rigor.escalation.{field} must be boolean")
                if escalation.get("allow_automatic_escalation") is True and escalation.get("enabled") is not True:
                    errors.append(f"{prefix}.engineering_rigor.escalation enabled conflicts with automatic escalation")
                if escalation.get("allow_automatic_deescalation") is not False:
                    errors.append(f"{prefix}.engineering_rigor.allow_automatic_deescalation must remain false")
            minimums = settings.get("minimums")
            if not isinstance(minimums, dict):
                errors.append(f"{prefix}.engineering_rigor.minimums must be an object")
            else:
                for category, level in minimums.items():
                    if (
                        not isinstance(category, str) or not text_present(category)
                        or category.casefold() != category or not category.replace("_", "").isalnum()
                    ):
                        errors.append(f"{prefix}.engineering_rigor.minimums category is invalid")
                    if level not in ENGINEERING_RIGOR_LEVELS:
                        errors.append(f"{prefix}.engineering_rigor.minimums {category!r} level is invalid")
            overrides = settings.get("overrides")
            if not isinstance(overrides, dict) or set(overrides) != {
                "per_goal", "raising", "lowering", "may_undercut_risk_minimum",
            }:
                errors.append(f"{prefix}.engineering_rigor.overrides is invalid")
            else:
                if not isinstance(overrides.get("per_goal"), bool):
                    errors.append(f"{prefix}.engineering_rigor.overrides.per_goal must be boolean")
                if overrides.get("raising") != "allowed":
                    errors.append(f"{prefix}.engineering_rigor.overrides.raising must be allowed")
                if overrides.get("lowering") != "explicit_user_authority":
                    errors.append(f"{prefix}.engineering_rigor.overrides.lowering requires explicit user authority")
                if overrides.get("may_undercut_risk_minimum") is not False:
                    errors.append(f"{prefix}.engineering_rigor.may_undercut_risk_minimum must remain false")
            interview = settings.get("requirements_interview")
            if not isinstance(interview, dict) or set(interview) != {"source", "level_mapping"}:
                errors.append(f"{prefix}.engineering_rigor.requirements_interview is invalid")
            else:
                if interview.get("source") != "effective_engineering_rigor":
                    errors.append(f"{prefix}.engineering_rigor.requirements_interview.source is invalid")
                if interview.get("level_mapping") != ENGINEERING_RIGOR_INTERVIEW_DEPTH:
                    errors.append(f"{prefix}.engineering_rigor.requirements_interview.level_mapping is invalid")
        elif section_id == "workflow_adherence":
            settings = section["settings"]
            if section.get("decision") not in WORKFLOW_ADHERENCE_SETTINGS["levels"]:
                errors.append(f"{prefix}.workflow_adherence.decision must be optional, tracked, or managed")
            if settings != WORKFLOW_ADHERENCE_SETTINGS:
                errors.append(f"{prefix}.workflow_adherence.settings must preserve the bounded routing contract")
        elif section_id == "automated_design":
            settings = section["settings"]
            if section.get("decision") not in {"enabled", "disabled"}:
                errors.append(f"{prefix}.decision must be enabled or disabled")
            for field, expected in AUTOMATED_DESIGN_SETTINGS.items():
                if settings.get(field) != expected:
                    errors.append(f"{prefix}.automated_design.settings.{field} must preserve the bounded contract")
        elif section_id == "autonomy_approval_parallelism":
            settings = section["settings"]
            if settings.get("dependency_implementation_gate") not in DEPENDENCY_IMPLEMENTATION_GATES:
                errors.append(f"{prefix}.settings.dependency_implementation_gate is invalid")
            if "execution_reports" in settings:
                reporting = settings["execution_reports"]
                if not isinstance(reporting, dict):
                    errors.append(f"{prefix}.settings.execution_reports must be an object")
                elif not isinstance(reporting.get("enabled"), bool):
                    errors.append(f"{prefix}.settings.execution_reports.enabled must be boolean")
            if "requirements_interview" in settings:
                interview = settings["requirements_interview"]
                expected = {
                    "capture_depth": {"light", "standard", "thorough"},
                    "mode": {"adaptive"},
                    "stakeholder_model": {"requesting_user_only"},
                    "execution_questions": {"durable_blockers_only"},
                }
                if not isinstance(interview, dict):
                    errors.append(f"{prefix}.settings.requirements_interview must be an object")
                else:
                    for field, allowed in expected.items():
                        if interview.get(field) not in allowed:
                            errors.append(f"{prefix}.settings.requirements_interview.{field} is invalid")
            if "resource_reservations" in settings:
                try:
                    normalize_resource_policy(settings["resource_reservations"])
                except ValueError as exc:
                    errors.append(f"{prefix}.settings.{exc}")
        review = section.get("review")
        if not isinstance(review, dict) or not isinstance(review.get("approved"), bool):
            errors.append(f"{prefix}.review.approved must be boolean")
        elif require_pending and review.get("approved") is not False:
            errors.append(f"{prefix}.review must be pending in an agent-generated plan")
        elif review.get("approved") is True and any(not text_present(review.get(field)) for field in ("reviewer", "date", "reviewed_digest")):
            errors.append(f"{prefix}.review approval requires reviewer, date, and reviewed_digest")
        elif review.get("approved") is True and section.get("unresolved"):
            errors.append(f"{prefix}.review cannot approve unresolved choices")
        if section.get("applicable") is False and not text_present(section.get("rationale")):
            errors.append(f"{prefix}.rationale is required for not applicable")
        errors.extend(validate_default_provenance(section, prefix))
    required_sections = set(POLICY_SECTION_IDS)
    missing = sorted(required_sections - seen)
    if missing:
        errors.append("missing sections: " + ", ".join(missing))
    for section_id, paths in missing_policy_settings(policy).items():
        errors.append(f"section {section_id} is missing operational policy settings: {', '.join(paths)}")
    rigor = next((item for item in sections if isinstance(item, dict) and item.get("id") == "engineering_rigor"), None)
    autonomy = next((item for item in sections if isinstance(item, dict) and item.get("id") == "autonomy_approval_parallelism"), None)
    if isinstance(rigor, dict) and isinstance(autonomy, dict):
        rigor_settings = rigor.get("settings") if isinstance(rigor.get("settings"), dict) else {}
        rigor_interview = rigor_settings.get("requirements_interview")
        rigor_interview = rigor_interview if isinstance(rigor_interview, dict) else {}
        mapping = rigor_interview.get("level_mapping", {})
        expected_depth = mapping.get(rigor.get("decision")) if isinstance(mapping, dict) else None
        autonomy_settings = autonomy.get("settings") if isinstance(autonomy.get("settings"), dict) else {}
        autonomy_interview = autonomy_settings.get("requirements_interview")
        autonomy_interview = autonomy_interview if isinstance(autonomy_interview, dict) else {}
        actual_depth = autonomy_interview.get("capture_depth")
        if expected_depth is not None and actual_depth != expected_depth:
            errors.append("engineering_rigor capture_depth conflicts with the reviewed default level")
    return errors


def policy_blockers(policy: Any) -> list[str]:
    if not isinstance(policy, dict) or not isinstance(policy.get("sections"), list):
        return ["policy:missing"]
    return [
        f"policy:{section.get('id')}"
        for section in policy["sections"]
        if isinstance(section, dict)
        and section.get("required") is True
        and bool(section.get("unresolved"))
    ]


def reviewed_project_state(repo: Path) -> dict[str, Any]:
    _path, _policy_text, project = read_project_state(repo)
    errors = validate_project_state(project) if project is not None else ["canonical policy is missing"]
    errors.extend(validate_project_artifacts(repo, project))
    if errors or project.get("initialized") is not True or policy_blockers(project.get("policy")):
        raise ValueError("Project policy is not ready")
    return project


def cell(value: str) -> str:
    return " ".join(str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ").split())


def _plain_policy_choice(section: dict[str, Any], limit: int = 140) -> str:
    decision = " ".join(str(section.get("decision") or "Not configured").split())
    if decision and " " not in decision:
        decision = decision.replace("_", " ").capitalize()
        if decision == "Github issues":
            decision = "GitHub Issues"
    if len(decision) <= limit:
        return decision
    boundary = decision.rfind(" ", 0, limit - 20)
    boundary = boundary if boundary >= 50 else limit - 20
    return decision[:boundary].rstrip(" ,;:") + "… (details in audit)"


def policy_review_rows(
    policy: dict[str, Any], catalog: dict[str, dict[str, Any]] | None = None,
    stale_reasons: dict[str, str] | None = None, *, proposal: bool = False,
) -> list[dict[str, str]]:
    """Build the complete plain-language policy-review view without changing audit truth."""
    comparisons = {
        item["section_id"]: item
        for item in compare_policy_defaults(policy, catalog)
        if item.get("section_id") in POLICY_SECTION_IDS
    }
    sections = {
        section.get("id"): section for section in policy.get("sections", [])
        if isinstance(section, dict) and section.get("id") in POLICY_SECTION_IDS
    }
    missing_settings = missing_policy_settings(policy, catalog)
    derived_stale_reasons = {
        section_id: "reviewed policy is missing " + ", ".join(paths)
        for section_id, paths in missing_settings.items()
    }
    derived_stale_reasons.update(stale_reasons or {})
    stale_reasons = derived_stale_reasons
    rows = []
    relationship = {
        "current": "Yes — current ZzzOps default",
        "customized": "No — customized for this project",
        "declined": "No — newer ZzzOps default was declined",
        "unknown_origin": "Unknown — origin was not recorded",
        "unknown_default": "Unknown — recorded default is unavailable",
        "update_available": "Yes — an older ZzzOps default",
    }
    for section_id in POLICY_SECTION_IDS:
        section = sections.get(section_id)
        if section is None:
            rows.append({
                "policy": POLICY_SECTION_TITLES[section_id], "current_choice": "Not configured",
                "default_relationship": "Unknown — policy is missing",
                "stale": "Yes — this policy is missing", "approved": "Not yet",
                "applies": "Unknown", "needs_attention": "Add and review this policy",
            })
            continue
        comparison = comparisons.get(section_id, {"status": "unknown_origin"})
        status = comparison["status"]
        if proposal and section.get("default_id"):
            default_relationship = {
                "accepted": "Proposed ZzzOps default",
                "changed": "Proposed project customization",
                "rejected": "Proposed rejection of the ZzzOps default",
            }.get(section.get("default_disposition"), "Proposed choice — origin needs review")
            stale = "No — new proposal"
        else:
            default_relationship = relationship.get(status, "Unknown — review needed")
            stale = {
                "current": "No",
                "customized": "No",
                "declined": "No — latest default was reviewed and declined",
                "unknown_origin": "Unknown — earlier policy did not record its origin",
                "unknown_default": "Yes — recorded default is no longer available",
                "update_available": "Yes — ZzzOps changed its recommended choice",
            }.get(status, "Unknown — review needed")
        if section_id in stale_reasons:
            stale = "Yes — " + " ".join(stale_reasons[section_id].split())
        approved = section.get("review", {}).get("approved") is True
        unresolved = section.get("unresolved") or []
        if section_id in stale_reasons:
            attention = "Review the affected choice"
        elif status == "update_available":
            attention = "Review the changed ZzzOps recommendation"
        elif status in {"unknown_origin", "unknown_default"} and not proposal:
            attention = "Confirm whether to keep this choice"
        elif unresolved:
            attention = "Resolve: " + str(unresolved[0])
        elif not approved:
            attention = "Approve this policy"
        else:
            attention = "—"
        rows.append({
            "policy": POLICY_SECTION_TITLES[section_id],
            "current_choice": _plain_policy_choice(section),
            "default_relationship": default_relationship, "stale": stale,
            "approved": "✅ Yes" if approved else "Not yet",
            "applies": "Yes" if section.get("applicable") is True else "No",
            "needs_attention": attention,
        })
    return rows


def render_policy_review_table(
    policy: dict[str, Any], catalog: dict[str, dict[str, Any]] | None = None,
    stale_reasons: dict[str, str] | None = None, *, proposal: bool = False,
) -> str:
    rows = policy_review_rows(policy, catalog, stale_reasons, proposal=proposal)
    header = (
        "| Policy | Current choice | ZzzOps default? | Stale? | Approved | Applies? | Needs attention |\n"
        "| --- | --- | --- | --- | --- | --- | --- |"
    )
    body = "\n".join(
        "| {policy} | {current_choice} | {default_relationship} | {stale} | {approved} | {applies} | {needs_attention} |".format(
            **{key: cell(value) for key, value in row.items()}
        )
        for row in rows
    )
    return header + "\n" + body


def render_project(state: dict[str, Any]) -> str:
    charter = state["charter"]
    status = "complete" if state["initialized"] else "incomplete — policy review required"
    reviewed = (state.get("approval") or {}).get("date", "not yet")
    kpis = "\n".join(f"| {cell(k['name'])} | {cell(k['why'])} | {cell(k['baseline'])} | {cell(k['target'])} | {cell(k['evidence'])} | {cell(k['cadence'])} |" for k in charter["kpis"])
    bullets = lambda values: "\n".join(f"- {value}" for value in values)
    checks = "\n".join(f"- [x] {value}" for value in charter["acceptance_criteria"])
    policy = "\n".join(
        f"- `[policy:{section['id']}]` **{section['title']}**: {section['decision']} ({default_provenance_label(section)})"
        for section in state["policy"]["sections"]
    )
    return f"""# Project success charter

**Status:** {status}
**Last reviewed:** {reviewed}

## Overall goal
- Outcome: {charter['outcome']}
- Primary beneficiaries: {', '.join(charter['beneficiaries'])}
- Why it matters: {charter['why_it_matters']}
- Time horizon: {charter['time_horizon']}

## Success metrics
| KPI | Why it matters | Baseline | Target / threshold | Evidence source | Review cadence |
| --- | --- | --- | --- | --- | --- |
{kpis}

## Project acceptance criteria
{checks}

## Value rubric
- `critical`: required for project acceptance, safety, or a binding deadline.
- `high`: materially moves a priority KPI or unlocks critical/high-value work.
- `medium`: useful measurable contribution with limited leverage.
- `low`: weak, speculative, cosmetic, or currently unmeasured contribution.

When KPIs conflict, prefer: {charter['precedence']}

## Constraints and non-goals
### Constraints
{bullets(charter['constraints'])}

### Non-goals
{bullets(charter['non_goals'])}

### Unacceptable tradeoffs
{bullets(charter['unacceptable_tradeoffs'])}

## Assumptions and open questions
- None recorded at initialization; add evidence-backed changes with history.

## Operating policy

{policy}

Detailed rationale and review history: [PROJECT_AUDIT.md](PROJECT_AUDIT.md). Canonical policy state: [POLICY.json](POLICY.json).
"""


def render_policy_sections(policy: dict[str, Any]) -> str:
    rendered = []
    evidence = {item["id"]: f"{item['source']} — {item['finding']}" for item in policy.get("evidence", []) if isinstance(item, dict) and text_present(item.get("id"))}
    for section in policy["sections"]:
        approved = section["review"]["approved"] is True
        applicable = "applicable" if section["applicable"] else "not applicable"
        settings = json.dumps(section["settings"], ensure_ascii=False, sort_keys=True)
        sources = "; ".join(
            "{}: {}".format(source_id, evidence.get(source_id, "missing citation"))
            for source_id in section["source_ids"]
        )
        rendered.append(
            f"- [{'x' if approved else ' '}] `[policy:{section['id']}]` **{section['title']}** ({applicable})\n"
            f"  - Decision: {section['decision']}\n"
            f"  - Rationale: {section['rationale']}\n"
            f"  - Sources: {sources}\n"
            f"  - Confidence/default: {section['confidence']}; {section['default_origin']} → {section['default_disposition']}\n"
            f"  - Provenance: {default_provenance_label(section)}\n"
            f"  - Settings: `{settings}`\n"
            f"  - Exceptions: {', '.join(section['exceptions']) or 'none'}\n"
            f"  - Unresolved: {', '.join(section['unresolved']) or 'none'}"
        )
    return "\n".join(rendered)


def render_project_audit(state: dict[str, Any]) -> str:
    status = "complete" if state["initialized"] else "pending explicit review"
    reviewer = (state.get("approval") or {}).get("reviewer", "not yet approved")
    history = "\n".join(f"| {cell(entry['date'])} | {cell(entry['actor'])} | {cell(entry['change'])} | {cell(entry['reason'])} |" for entry in state["history"])
    return (
        "# ZzzOps project policy audit\n\n"
        f"Status: {status}. Reviewer: {reviewer}. Revision: {state['revision']}.\n\n"
        "## Evidence and decisions\n\n"
        f"{render_policy_sections(state['policy'])}\n\n"
        "## Review record\n\n"
        "| Date | Actor/run | Change | Reason/evidence |\n"
        "| --- | --- | --- | --- |\n"
        f"{history}\n\n"
        "The machine-readable authority is [POLICY.json](POLICY.json); this file is its human audit view.\n"
    )
