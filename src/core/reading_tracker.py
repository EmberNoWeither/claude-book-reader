"""阅读会话追踪 — 生命周期管理 + 统计查询"""

from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

if TYPE_CHECKING:
    from core.config import Config
    from core.storage import Storage


@dataclass
class ReadingSession:
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    book_id: str = ""
    start_time: str = ""
    end_time: str = ""
    start_page: int = 0
    end_page: int = 0

    @property
    def duration_sec(self) -> int:
        if not self.start_time:
            return 0
        start = datetime.fromisoformat(self.start_time)
        if self.end_time:
            end = datetime.fromisoformat(self.end_time)
        else:
            end = datetime.now()
        return max(0, int((end - start).total_seconds()))

    @property
    def pages_read(self) -> int:
        return max(0, self.end_page - self.start_page)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> ReadingSession:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class ReadingTracker(QObject):
    """会话生命周期管理 + 统计查询"""

    session_started = pyqtSignal(str)
    session_ended = pyqtSignal(str)
    streak_changed = pyqtSignal(int)

    def __init__(self, storage: Storage, config: Config, parent=None) -> None:
        super().__init__(parent)
        self._storage = storage
        self._config = config
        self._active: ReadingSession | None = None
        self._last_activity_ts: float = 0.0
        self._sessions: list[ReadingSession] = []

        idle_minutes = self._config.get("reading", "idle_timeout_minutes", default=5)
        self._idle_threshold = idle_minutes * 60
        flush_sec = self._config.get("reading", "flush_interval_seconds", default=30)

        self._idle_timer = QTimer(self)
        self._idle_timer.setInterval(60_000)
        self._idle_timer.timeout.connect(self._check_idle)

        self._flush_timer = QTimer(self)
        self._flush_timer.setInterval(flush_sec * 1000)
        self._flush_timer.timeout.connect(self._flush)

        self._load()
        self._recover_crash()

    # ── 生命周期 ──

    def start_session(self, book_id: str, page: int) -> str:
        if self._active:
            self.end_session()
        session = ReadingSession(
            book_id=book_id,
            start_time=datetime.now().isoformat(timespec="seconds"),
            start_page=page,
            end_page=page,
        )
        self._active = session
        self._last_activity_ts = time.time()
        self._idle_timer.start()
        self._flush_timer.start()
        self.session_started.emit(book_id)
        return session.session_id

    def update_progress(self, page: int) -> None:
        if not self._active:
            return
        self._active.end_page = page
        self._last_activity_ts = time.time()

    def end_session(self) -> ReadingSession | None:
        if not self._active:
            return None
        self._idle_timer.stop()
        self._flush_timer.stop()
        self._active.end_time = datetime.now().isoformat(timespec="seconds")
        session = self._active
        self._sessions.append(session)
        self._active = None
        self._save()
        self.session_ended.emit(session.session_id)
        old_streak = self.streak_days()
        self.streak_changed.emit(old_streak)
        return session

    def get_active(self) -> ReadingSession | None:
        return self._active

    # ── 查询 ──

    def sessions_for_day(self, day: date) -> list[ReadingSession]:
        return [s for s in self._sessions if self._session_date(s) == day]

    def sessions_for_range(self, start: date, end: date) -> list[ReadingSession]:
        return [s for s in self._sessions if start <= self._session_date(s) <= end]

    def total_today_sec(self) -> int:
        today = date.today()
        total = sum(s.duration_sec for s in self.sessions_for_day(today))
        if self._active and self._session_date(self._active) == today:
            total += self._active.duration_sec
        return total

    def pages_today(self) -> int:
        today = date.today()
        total = sum(s.pages_read for s in self.sessions_for_day(today))
        if self._active and self._session_date(self._active) == today:
            total += self._active.pages_read
        return total

    def streak_days(self) -> int:
        if not self._sessions:
            return 0
        days_with_sessions: set[date] = set()
        for s in self._sessions:
            days_with_sessions.add(self._session_date(s))
        if self._active:
            days_with_sessions.add(self._session_date(self._active))

        today = date.today()
        if today not in days_with_sessions:
            today = today - timedelta(days=1)
            if today not in days_with_sessions:
                return 0

        streak = 0
        check = today
        while check in days_with_sessions:
            streak += 1
            check -= timedelta(days=1)
        return streak

    def speed_pages_per_hour(self, days: int = 7) -> float:
        end = date.today()
        start = end - timedelta(days=days)
        sessions = self.sessions_for_range(start, end)
        total_pages = sum(s.pages_read for s in sessions)
        total_sec = sum(s.duration_sec for s in sessions)
        if total_sec < 60:
            return 0.0
        return total_pages / (total_sec / 3600)

    # ── 内部 ──

    def _check_idle(self) -> None:
        if not self._active:
            return
        if time.time() - self._last_activity_ts > self._idle_threshold:
            self.end_session()

    def _flush(self) -> None:
        if not self._active:
            return
        all_data = [s.to_dict() for s in self._sessions]
        all_data.append(self._active.to_dict())
        self._storage.write_json("reading_sessions.json", all_data)

    def _load(self) -> None:
        data = self._storage.read_json("reading_sessions.json")
        if isinstance(data, list):
            self._sessions = [ReadingSession.from_dict(d) for d in data if isinstance(d, dict)]

    def _save(self) -> None:
        all_data = [s.to_dict() for s in self._sessions]
        self._storage.write_json("reading_sessions.json", all_data)

    def _recover_crash(self) -> None:
        if not self._sessions:
            return
        last = self._sessions[-1]
        if not last.end_time and last.start_time:
            start = datetime.fromisoformat(last.start_time)
            if datetime.now() - start > timedelta(hours=1):
                last.end_time = (start + timedelta(minutes=30)).isoformat(timespec="seconds")
                self._save()

    @staticmethod
    def _session_date(s: ReadingSession) -> date:
        if s.start_time:
            return datetime.fromisoformat(s.start_time).date()
        return date.today()




