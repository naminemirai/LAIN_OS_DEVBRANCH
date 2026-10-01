import tempfile
import unittest
from pathlib import Path

from lain.config import RuntimeConfig


class ConfigTests(unittest.TestCase):
    def test_defaults_are_secure_and_bounded(self):
        config = RuntimeConfig.default()
        self.assertGreater(config.max_actions, 0)
        self.assertGreater(config.max_text_write_bytes, 0)
        self.assertFalse(config.overwrite_default)
        self.assertTrue(config.allowed_roots)
        self.assertTrue(all(isinstance(root, Path) for root in config.allowed_roots))

    def test_with_workspace_normalizes_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = RuntimeConfig.for_workspace(Path(tmp) / "workspace")
            self.assertEqual(config.allowed_roots[0], (Path(tmp) / "workspace").resolve())
            self.assertEqual(config.audit_path, (Path(tmp) / "workspace" / ".lain" / "audit.jsonl").resolve())


if __name__ == "__main__":
    unittest.main()

class ConfigFileTests(unittest.TestCase):
    def test_loads_toml_configuration(self):
        from lain.config import load_config
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp, "workspace")
            cfg = Path(tmp, "lain.toml")
            cfg.write_text(
                'allowed_roots = ["' + str(root).replace('\\', '\\\\') + '"]\n'
                'audit_path = "' + str(Path(tmp, "audit.jsonl")).replace('\\', '\\\\') + '"\n'
                'max_actions = 7\n'
                'max_text_write_bytes = 2048\n'
                'overwrite_default = false\n'
                'confirmation_risk_threshold = 2\n'
                'deny_risk_threshold = 3\n'
                'android_adapter = "disabled"\n'
                'android_timeout_seconds = 3.5\n'
            )
            config = load_config(cfg)
            self.assertEqual(config.allowed_roots, (root.resolve(),))
            self.assertEqual(config.max_actions, 7)
            self.assertEqual(config.android_adapter, "disabled")
            self.assertEqual(config.android_timeout_seconds, 3.5)

    def test_rejects_non_array_planner_command(self):
        from lain.config import load_config
        for value in ('"python"', "42", '["python", 42]'):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as tmp:
                cfg = Path(tmp, "lain.toml")
                cfg.write_text(
                    'allowed_roots = ["."]\n'
                    'audit_path = "audit.jsonl"\n'
                    f"planner_command = {value}\n"
                )
                with self.assertRaisesRegex(ValueError, "planner_command must be an array of strings"):
                    load_config(cfg)


class AgentConfigTests(unittest.TestCase):
    def test_agent_defaults_are_finite(self):
        config = RuntimeConfig.default()
        self.assertEqual(config.agent.max_iterations, 12)
        self.assertEqual(config.agent.max_total_actions, 32)
        self.assertEqual(config.agent.max_runtime_seconds, 900.0)

    def test_loads_agent_budget_overrides(self):
        from lain.config import load_config
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp, "lain.toml")
            cfg.write_text(
                'allowed_roots = ["."]\n'
                'audit_path = "audit.jsonl"\n'
                'agent_max_iterations = 5\n'
                'agent_max_total_actions = 9\n'
                'agent_max_runtime_seconds = 12.5\n'
            )
            config = load_config(cfg)
            self.assertEqual(config.agent.max_iterations, 5)
            self.assertEqual(config.agent.max_total_actions, 9)
            self.assertEqual(config.agent.max_runtime_seconds, 12.5)

    def test_agent_budget_rejects_nonpositive_values(self):
        from lain.config import AgentConfig
        for kwargs in (
            {"max_iterations": 0},
            {"max_total_actions": -1},
            {"max_runtime_seconds": 0},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                AgentConfig(**kwargs)


class AgentConfigFiniteBudgetRegressionTests(unittest.TestCase):
    def test_agent_config_rejects_non_finite_runtime_limit(self):
        from lain.config import AgentConfig
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                AgentConfig(max_runtime_seconds=value)
