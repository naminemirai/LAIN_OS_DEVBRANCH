from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "lain-engineering"
SKILLS = PLUGIN / "skills"

EXPECTED_SKILLS = {
    "add-goal",
    "bootstrap-repository",
    "execute",
    "migrate",
    "review-agentic-engineering",
    "review-policy",
    "send-feedback",
    "suggest-work",
    "validate-installation",
}
RETIRED_SKILL_NAMES = {
    "add-zzzops-goal",
    "bootstrap-zzzops-repository",
    "execute-zzzops",
    "migrate-to-zzzops",
    "review-zzzops-policy",
    "send-zzzops-feedback",
    "suggest-zzzops-work",
    "validate-zzzops-installation",
}
PERSONAL_MARKERS = (
    "David Rzepa",
    "david-rzepa/zzzops",
    "github.com/david-rzepa",
)


def _load_policy_module():
    path = PLUGIN / "zzzops" / "policy.py"
    spec = importlib.util.spec_from_file_location("lain_engineering_policy", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_plugin_has_functional_skill_names_only():
    assert PLUGIN.is_dir()
    assert {p.name for p in SKILLS.iterdir() if p.is_dir()} == EXPECTED_SKILLS
    for name in EXPECTED_SKILLS:
        text = (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
        assert f"name: {name}" in text
        assert "name: zzzops-" not in text
        assert "-zzzops-" not in text


def test_retired_skill_invocations_are_gone():
    text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in PLUGIN.rglob("*")
        if path.is_file() and path.suffix.lower() in {".md", ".json", ".yaml", ".yml", ".py"}
    )
    for retired in RETIRED_SKILL_NAMES:
        assert retired not in text


def test_manifests_have_no_person_specific_attribution():
    for rel in ("plugin.json", ".codex-plugin/plugin.json", ".claude-plugin/plugin.json"):
        data = json.loads((PLUGIN / rel).read_text(encoding="utf-8"))
        assert data.get("name") == "lain-engineering"
        assert "author" not in data
        interface = data.get("interface") or data.get("extensions", {}).get("com.openai", {}).get("interface", {})
        assert "developerName" not in interface
        serialized = json.dumps(data)
        for marker in PERSONAL_MARKERS:
            assert marker not in serialized


def test_feedback_target_is_not_hard_coded_to_upstream():
    text = (PLUGIN / "zzzops" / "feedback.py").read_text(encoding="utf-8")
    for marker in PERSONAL_MARKERS:
        assert marker not in text
    assert "def feedback_target(" in text


def test_unapproved_policy_is_not_an_execution_blocker():
    policy = _load_policy_module()
    unapproved = {
        "sections": [
            {
                "id": "example",
                "required": True,
                "unresolved": [],
                "review": {"approved": False},
            }
        ]
    }
    assert policy.policy_blockers(unapproved) == []

    unresolved = {
        "sections": [
            {
                "id": "example",
                "required": True,
                "unresolved": ["choose a destructive migration strategy"],
                "review": {"approved": False},
            }
        ]
    }
    assert policy.policy_blockers(unresolved) == ["policy:example"]
