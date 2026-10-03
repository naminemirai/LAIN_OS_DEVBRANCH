from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
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


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _frontmatter_name(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    frontmatter = text.split("---", 2)[1]
    for line in frontmatter.splitlines():
        key, separator, value = line.partition(":")
        if separator and key.strip() == "name":
            return value.strip().strip("'\"")
    return None


class LainEngineeringPluginContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            PLUGIN.is_dir(),
            "plugins/lain-engineering must exist before the migration contract can pass",
        )

    def test_plugin_has_functional_skill_names_only(self):
        self.assertEqual(
            EXPECTED_SKILLS,
            {path.name for path in SKILLS.iterdir() if path.is_dir()},
        )
        for name in EXPECTED_SKILLS:
            skill = SKILLS / name / "SKILL.md"
            self.assertEqual(name, _frontmatter_name(skill))
            text = skill.read_text(encoding="utf-8")
            self.assertNotIn("name: zzzops-", text)
            self.assertNotIn("-zzzops-", text)

    def test_retired_skill_invocations_are_gone(self):
        text = "\n".join(
            path.read_text(encoding="utf-8", errors="ignore")
            for path in PLUGIN.rglob("*")
            if path.is_file()
            and path.suffix.lower() in {".md", ".json", ".yaml", ".yml", ".py"}
        )
        for retired in RETIRED_SKILL_NAMES:
            self.assertNotIn(retired, text)

    def test_manifests_have_no_person_specific_attribution(self):
        for relative in (
            "plugin.json",
            ".codex-plugin/plugin.json",
            ".claude-plugin/plugin.json",
        ):
            data = json.loads((PLUGIN / relative).read_text(encoding="utf-8"))
            self.assertEqual("lain-engineering", data.get("name"))
            self.assertNotIn("author", data)
            interface = data.get("interface") or data.get("extensions", {}).get(
                "com.openai", {}
            ).get("interface", {})
            self.assertNotIn("developerName", interface)
            serialized = json.dumps(data)
            for marker in PERSONAL_MARKERS:
                self.assertNotIn(marker, serialized)

    def test_feedback_target_is_derived_from_current_repository(self):
        feedback = _load_module(
            "lain_engineering_feedback",
            PLUGIN / "zzzops" / "feedback.py",
        )
        with (
            tempfile.TemporaryDirectory() as first,
            tempfile.TemporaryDirectory() as second,
        ):
            repos = [
                (Path(first), "https://github.com/example/one.git", "example/one"),
                (Path(second), "git@github.com:another/two.git", "another/two"),
            ]
            for repo, remote, expected in repos:
                subprocess.run(
                    ["git", "init", "--quiet", str(repo)],
                    check=True,
                )
                subprocess.run(
                    ["git", "-C", str(repo), "remote", "add", "origin", remote],
                    check=True,
                )
                self.assertEqual(expected, feedback.feedback_target(repo))

    def test_unapproved_policy_is_not_an_execution_blocker(self):
        policy = _load_module(
            "lain_engineering_policy",
            PLUGIN / "zzzops" / "policy.py",
        )
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
        self.assertEqual([], policy.policy_blockers(unapproved))

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
        self.assertEqual(["policy:example"], policy.policy_blockers(unresolved))


if __name__ == "__main__":
    unittest.main()
