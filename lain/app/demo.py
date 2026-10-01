"""Deterministic offline demonstration, explicitly not a language model."""
from pathlib import Path

from lain.planning.models import AgentPlannerDecision, AgentPlannerStatus, ProposedAction


COMMANDS = ("Create demo file", "Show battery", "Show demo toast", "Vibrate briefly",
            "Copy demo text", "Share demo text")


class DemoPlanner:
    def __init__(self, workspace: Path):
        self.workspace = workspace

    def decide(self, goal, context, capabilities):
        if context["history"]:
            return AgentPlannerDecision(AgentPlannerStatus.COMPLETE,
                                        "Offline demo finished; inspect execution and verification results.", ())
        demos = {
            "create demo file": ProposedAction("file.write_text", {
                "path": str(self.workspace / "demo.txt"), "content": "Hello from LAIN_OS.\n",
            }),
            "show battery": ProposedAction("android.battery_status", {}),
            "show demo toast": ProposedAction("android.toast", {"content": "Hello from LAIN_OS."}),
            "vibrate briefly": ProposedAction("android.vibrate", {"duration_ms": 200}),
            "copy demo text": ProposedAction("android.clipboard_set", {"content": "Hello from LAIN_OS."}),
            "share demo text": ProposedAction("android.share_text", {"content": "Hello from LAIN_OS."}),
        }
        action = demos.get(goal.strip().lower())
        if action is None:
            return AgentPlannerDecision(AgentPlannerStatus.BLOCKED,
                                        "No language-model planner configured. Choose a listed offline demo.", ())
        return AgentPlannerDecision(AgentPlannerStatus.CONTINUE, "Run the owner-selected offline demo.", (action,))
