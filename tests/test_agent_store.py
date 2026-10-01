import json
import os
import stat
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from lain.agent import AgentBudget, AgentSession, AgentSessionStatus
from lain.agent.store import AgentSessionStore
from lain.errors import ErrorCode, LainError


def session(*, updated_at="2026-09-29T20:00:00+00:00"):
    session_id = str(uuid4())
    return AgentSession(
        version="1",
        session_id=session_id,
        goal="test goal",
        status=AgentSessionStatus.CREATED,
        created_at="2026-09-29T19:59:00+00:00",
        updated_at=updated_at,
        iterations=(),
        total_attempted_actions=0,
        budget=AgentBudget(12, 8, 32, 900.0),
        cumulative_runtime_seconds=0.0,
        terminal_reason=None,
    )


class AgentSessionStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "sessions"
        self.store = AgentSessionStore(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_save_load_and_list_newest_first(self):
        older = session(updated_at="2026-09-29T20:00:00+00:00")
        newer = session(updated_at="2026-09-29T20:01:00+00:00")
        self.store.save(older)
        self.store.save(newer)

        self.assertEqual(self.store.path_for(older.session_id), self.root / older.session_id / "state.json")
        self.assertEqual(self.store.load(older.session_id), older)
        self.assertEqual(self.store.list_sessions(), (newer, older))

    def test_save_is_atomic_and_preserves_old_state_when_replace_fails(self):
        original = session()
        self.store.save(original)
        updated = replace(
            original,
            updated_at="2026-09-29T20:02:00+00:00",
            status=AgentSessionStatus.PLANNING,
        )
        with patch("lain.agent.store.os.replace", side_effect=OSError("boom")):
            with self.assertRaises(OSError):
                self.store.save(updated)
        self.assertEqual(self.store.load(original.session_id), original)

    def test_state_and_directory_permissions_are_private(self):
        item = session()
        self.store.save(item)
        session_dir = self.root / item.session_id
        state_path = session_dir / "state.json"
        self.assertEqual(stat.S_IMODE(state_path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(session_dir.stat().st_mode) & 0o077, 0)

    def test_invalid_or_missing_session_ids_fail_closed(self):
        for invalid in ("../../escape", "not-a-uuid", ""):
            with self.subTest(invalid=invalid), self.assertRaises(LainError) as ctx:
                self.store.load(invalid)
            self.assertEqual(ctx.exception.code, ErrorCode.AGENT_SESSION_INVALID)

        missing = str(uuid4())
        with self.assertRaises(LainError) as ctx:
            self.store.load(missing)
        self.assertEqual(ctx.exception.code, ErrorCode.AGENT_SESSION_NOT_FOUND)

    def test_corrupt_wrong_shape_and_unsupported_version_fail_closed(self):
        item = session()
        session_dir = self.root / item.session_id
        session_dir.mkdir(parents=True, mode=0o700)

        cases = (
            "{not json",
            json.dumps({"version": "1"}),
            json.dumps({**item.to_dict(), "version": "999"}),
        )
        for payload in cases:
            with self.subTest(payload=payload):
                (session_dir / "state.json").write_text(payload, encoding="utf-8")
                with self.assertRaises(LainError) as ctx:
                    self.store.load(item.session_id)
                self.assertEqual(ctx.exception.code, ErrorCode.AGENT_SESSION_INVALID)

    def test_non_finite_persisted_budget_fails_closed(self):
        item = session()
        session_dir = self.root / item.session_id
        session_dir.mkdir(parents=True, mode=0o700)
        raw = item.to_dict()
        raw["budget"]["max_iterations"] = float("inf")
        (session_dir / "state.json").write_text(
            json.dumps(raw),
            encoding="utf-8",
        )

        with self.assertRaises(LainError) as ctx:
            self.store.load(item.session_id)

        self.assertEqual(ctx.exception.code, ErrorCode.AGENT_SESSION_INVALID)

    def test_lease_is_exclusive_and_released_on_context_exit(self):
        item = session()
        self.store.save(item)
        with self.store.lease(item.session_id):
            with self.assertRaises(LainError) as ctx:
                with self.store.lease(item.session_id):
                    pass
            self.assertEqual(ctx.exception.code, ErrorCode.AGENT_SESSION_BUSY)

        with self.store.lease(item.session_id):
            pass


if __name__ == "__main__":
    unittest.main()
