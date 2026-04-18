import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any

from app.config import settings


class SessionData:
    def __init__(self):
        self.graph_state: dict[str, Any] = {}
        self.graph_config: dict[str, Any] = {}
        self.match_report: dict | None = None
        self.suggestions: list[dict] = []
        self.optimized_resume: str | None = None
        self.created_at: datetime = datetime.utcnow()


sessions: dict[str, SessionData] = {}


def create_session() -> str:
    sid = str(uuid.uuid4())
    sessions[sid] = SessionData()
    return sid


def get_session(sid: str) -> SessionData | None:
    s = sessions.get(sid)
    if s is None:
        return None
    ttl = timedelta(minutes=settings.session_ttl_minutes)
    if datetime.utcnow() - s.created_at > ttl:
        del sessions[sid]
        return None
    return s


def delete_session(sid: str) -> None:
    sessions.pop(sid, None)


async def _cleanup_loop() -> None:
    while True:
        await asyncio.sleep(300)
        ttl = timedelta(minutes=settings.session_ttl_minutes)
        now = datetime.utcnow()
        expired = [sid for sid, s in sessions.items() if now - s.created_at > ttl]
        for sid in expired:
            del sessions[sid]


cleanup_task: asyncio.Task | None = None


def start_cleanup() -> None:
    global cleanup_task
    cleanup_task = asyncio.create_task(_cleanup_loop())


def stop_cleanup() -> None:
    if cleanup_task:
        cleanup_task.cancel()
