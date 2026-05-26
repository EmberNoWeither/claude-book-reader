"""ReadingTracker 单元测试"""

import time
from datetime import date, datetime, timedelta

import pytest

from core.reading_tracker import ReadingSession, ReadingTracker


@pytest.fixture
def tracker(tmp_data_dir, monkeypatch):
    from core.config import Config
    from core.storage import Storage

    monkeypatch.setattr(Config, "_instance", None)
    cfg = Config()
    monkeypatch.setattr(type(cfg), "data_dir", property(lambda self: tmp_data_dir))
    cfg.load()
    storage = Storage(tmp_data_dir)
    return ReadingTracker(storage, cfg)


class TestReadingSession:
    def test_duration_sec(self):
        s = ReadingSession(
            start_time="2025-01-01T10:00:00",
            end_time="2025-01-01T10:30:00",
        )
        assert s.duration_sec == 1800

    def test_pages_read(self):
        s = ReadingSession(start_page=5, end_page=15)
        assert s.pages_read == 10

    def test_roundtrip(self):
        s = ReadingSession(book_id="abc", start_time="2025-01-01T10:00:00")
        d = s.to_dict()
        s2 = ReadingSession.from_dict(d)
        assert s2.book_id == "abc"
        assert s2.session_id == s.session_id


class TestTrackerLifecycle:
    def test_start_end_session(self, tracker):
        sid = tracker.start_session("book1", 0)
        assert tracker.get_active() is not None
        session = tracker.end_session()
        assert session is not None
        assert session.session_id == sid
        assert session.book_id == "book1"
        assert tracker.get_active() is None

    def test_update_progress(self, tracker):
        tracker.start_session("book1", 5)
        tracker.update_progress(10)
        tracker.update_progress(15)
        session = tracker.end_session()
        assert session.end_page == 15

    def test_start_new_ends_previous(self, tracker):
        tracker.start_session("book1", 0)
        tracker.start_session("book2", 0)
        assert tracker.get_active().book_id == "book2"
        assert len(tracker._sessions) == 1


class TestStreak:
    def test_streak_consecutive_days(self, tracker, tmp_data_dir):
        from core.storage import Storage

        storage = Storage(tmp_data_dir)
        today = date.today()
        sessions = []
        for i in range(3):
            d = today - timedelta(days=i)
            dt = datetime(d.year, d.month, d.day, 10, 0, 0)
            sessions.append(ReadingSession(
                book_id="b", start_time=dt.isoformat(timespec="seconds"),
                end_time=(dt + timedelta(minutes=30)).isoformat(timespec="seconds"),
                start_page=0, end_page=10,
            ))
        storage.write_json("reading_sessions.json", [s.to_dict() for s in sessions])
        tracker._sessions = sessions
        assert tracker.streak_days() == 3

    def test_streak_broken_by_gap(self, tracker):
        today = date.today()
        sessions = []
        for i in [0, 1, 3]:  # gap at day 2
            d = today - timedelta(days=i)
            dt = datetime(d.year, d.month, d.day, 10, 0, 0)
            sessions.append(ReadingSession(
                book_id="b", start_time=dt.isoformat(timespec="seconds"),
                end_time=(dt + timedelta(minutes=30)).isoformat(timespec="seconds"),
                start_page=0, end_page=5,
            ))
        tracker._sessions = sessions
        assert tracker.streak_days() == 2


class TestQuery:
    def test_sessions_for_day(self, tracker):
        today = date.today()
        dt = datetime(today.year, today.month, today.day, 9, 0, 0)
        tracker._sessions = [
            ReadingSession(book_id="b", start_time=dt.isoformat(timespec="seconds"),
                           end_time=(dt + timedelta(hours=1)).isoformat(timespec="seconds"),
                           start_page=0, end_page=20),
        ]
        assert len(tracker.sessions_for_day(today)) == 1
        assert len(tracker.sessions_for_day(today - timedelta(days=1))) == 0

    def test_pages_today(self, tracker):
        today = date.today()
        dt = datetime(today.year, today.month, today.day, 8, 0, 0)
        tracker._sessions = [
            ReadingSession(book_id="b", start_time=dt.isoformat(timespec="seconds"),
                           end_time=(dt + timedelta(minutes=30)).isoformat(timespec="seconds"),
                           start_page=0, end_page=10),
            ReadingSession(book_id="b", start_time=(dt + timedelta(hours=1)).isoformat(timespec="seconds"),
                           end_time=(dt + timedelta(hours=1, minutes=30)).isoformat(timespec="seconds"),
                           start_page=10, end_page=25),
        ]
        assert tracker.pages_today() == 25


class TestCrashRecovery:
    def test_crash_recovery(self, tmp_data_dir, monkeypatch):
        from core.config import Config
        from core.storage import Storage

        storage = Storage(tmp_data_dir)
        old_start = (datetime.now() - timedelta(hours=2)).isoformat(timespec="seconds")
        sessions = [ReadingSession(
            book_id="b", start_time=old_start, end_time="",
            start_page=0, end_page=10,
        )]
        storage.write_json("reading_sessions.json", [s.to_dict() for s in sessions])
        storage.invalidate("reading_sessions.json")

        monkeypatch.setattr(Config, "_instance", None)
        cfg = Config()
        monkeypatch.setattr(type(cfg), "data_dir", property(lambda self: tmp_data_dir))
        cfg.load()
        tracker = ReadingTracker(storage, cfg)
        assert tracker._sessions[-1].end_time != ""


class TestIdleDetection:
    def test_pause_on_idle(self, tracker):
        tracker.start_session("book1", 0)
        tracker._last_activity_ts = time.time() - 400
        tracker._check_idle()
        assert tracker.get_active() is None
        assert len(tracker._sessions) == 1


