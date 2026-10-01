from __future__ import annotations

import fcntl
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from uuid import UUID

from lain.agent.models import AgentSession
from lain.errors import ErrorCode, LainError


class AgentSessionStore:
    def __init__(self, root: Path):
        self.root = Path(root).expanduser().resolve()

    def _validated_id(self, session_id: str) -> str:
        try:
            parsed = UUID(session_id)
        except (TypeError, ValueError, AttributeError) as exc:
            raise LainError(
                ErrorCode.AGENT_SESSION_INVALID,
                "session_id must be a UUID",
                details={"session_id": str(session_id)},
            ) from exc
        canonical = str(parsed)
        if session_id != canonical:
            raise LainError(
                ErrorCode.AGENT_SESSION_INVALID,
                "session_id must use canonical UUID form",
                details={"session_id": session_id},
            )
        return canonical

    def _session_dir(self, session_id: str) -> Path:
        return self.root / self._validated_id(session_id)

    def path_for(self, session_id: str) -> Path:
        return self._session_dir(session_id) / "state.json"

    def save(self, session: AgentSession) -> None:
        session_dir = self._session_dir(session.session_id)
        session_dir.mkdir(parents=True, mode=0o700, exist_ok=True)
        os.chmod(session_dir, 0o700)

        payload = (
            json.dumps(
                session.to_dict(),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )
            + "\n"
        ).encode("utf-8")

        fd, temporary_name = tempfile.mkstemp(prefix=".state.", suffix=".tmp", dir=session_dir)
        temporary_path = Path(temporary_name)
        try:
            os.fchmod(fd, 0o600)
            offset = 0
            while offset < len(payload):
                offset += os.write(fd, payload[offset:])
            os.fsync(fd)
            os.close(fd)
            fd = -1
            os.replace(temporary_path, session_dir / "state.json")
            os.chmod(session_dir / "state.json", 0o600)
            self._fsync_directory(session_dir)
        finally:
            if fd >= 0:
                os.close(fd)
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass

    def load(self, session_id: str) -> AgentSession:
        path = self.path_for(session_id)
        try:
            data = path.read_bytes()
        except FileNotFoundError as exc:
            raise LainError(
                ErrorCode.AGENT_SESSION_NOT_FOUND,
                "agent session was not found",
                details={"session_id": self._validated_id(session_id)},
            ) from exc
        try:
            raw = json.loads(data)
            if not isinstance(raw, dict):
                raise ValueError("session root must be an object")
            session = AgentSession.from_dict(raw)
        except LainError:
            raise
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError, ValueError) as exc:
            raise LainError(
                ErrorCode.AGENT_SESSION_INVALID,
                "agent session state is invalid",
                details={"session_id": self._validated_id(session_id)},
            ) from exc
        if session.session_id != self._validated_id(session_id):
            raise LainError(
                ErrorCode.AGENT_SESSION_INVALID,
                "agent session id does not match its storage path",
                details={"session_id": session_id},
            )
        return session

    def list_sessions(self) -> tuple[AgentSession, ...]:
        if not self.root.exists():
            return ()
        sessions: list[AgentSession] = []
        for child in self.root.iterdir():
            if not child.is_dir():
                continue
            try:
                session_id = self._validated_id(child.name)
            except LainError:
                continue
            sessions.append(self.load(session_id))
        sessions.sort(key=lambda item: item.updated_at, reverse=True)
        return tuple(sessions)

    @contextmanager
    def lease(self, session_id: str) -> Iterator[None]:
        session_id = self._validated_id(session_id)
        self.load(session_id)
        session_dir = self._session_dir(session_id)
        lock_path = session_dir / ".lock"
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            os.fchmod(fd, 0o600)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise LainError(
                    ErrorCode.AGENT_SESSION_BUSY,
                    "agent session is already in use",
                    details={"session_id": session_id},
                ) from exc
            try:
                yield
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        try:
            fd = os.open(path, flags)
        except OSError:
            return
        try:
            os.fsync(fd)
        except OSError:
            pass
        finally:
            os.close(fd)
