"""阅读仪表盘 — 统计卡片 + 热力图 + 最近阅读"""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from core.library import Library
    from core.reading_tracker import ReadingTracker


class StatCard(QFrame):
    """单个统计卡片"""

    def __init__(self, icon: str, label: str, value: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("stat_card")
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._value_label = QLabel(value)
        self._value_label.setObjectName("stat_value")
        font = self._value_label.font()
        font.setPointSize(18)
        font.setBold(True)
        self._value_label.setFont(font)
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._desc_label = QLabel(f"{icon} {label}")
        self._desc_label.setObjectName("stat_desc")
        self._desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self._value_label)
        layout.addWidget(self._desc_label)

    def set_value(self, value: str) -> None:
        self._value_label.setText(value)


class DashboardDialog(QDialog):
    """阅读仪表盘对话框"""

    book_selected = pyqtSignal(str)

    def __init__(self, tracker: ReadingTracker, library: Library, parent=None) -> None:
        super().__init__(parent)
        self._tracker = tracker
        self._library = library
        self.setWindowTitle("阅读仪表盘")
        self.setMinimumSize(560, 520)
        self.resize(600, 580)
        self._setup_ui()
        self._refresh_data()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Stat cards row
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        today_min = self._tracker.total_today_sec() // 60
        self._card_time = StatCard("⏱", "今日", f"{today_min} 分钟")
        self._card_pages = StatCard("📖", "今日", f"{self._tracker.pages_today()} 页")
        self._card_streak = StatCard("🔥", "连续", f"{self._tracker.streak_days()} 天")
        speed = self._tracker.speed_pages_per_hour()
        self._card_speed = StatCard("⚡", "速度", f"{speed:.0f} 页/h")

        for card in (self._card_time, self._card_pages, self._card_streak, self._card_speed):
            cards_layout.addWidget(card)
        layout.addLayout(cards_layout)

        # Weekly heatmap
        heatmap_label = QLabel("📅 本周阅读热力图")
        heatmap_label.setObjectName("section_header")
        layout.addWidget(heatmap_label)
        self._heatmap_widget = self._build_heatmap()
        layout.addWidget(self._heatmap_widget)

        # Library overview
        books = self._library.list_books()
        reading = sum(1 for b in books if b.reading_status == "reading")
        finished = sum(1 for b in books if b.reading_status == "finished")
        overview = QLabel(f"📚 书库概览: {len(books)} 本 │ {reading} 本在读 │ {finished} 本已读")
        overview.setObjectName("section_header")
        layout.addWidget(overview)

        # Recent reading table
        recent_label = QLabel("📝 最近阅读")
        recent_label.setObjectName("section_header")
        layout.addWidget(recent_label)
        self._table = self._build_recent_table()
        layout.addWidget(self._table)

    def _build_heatmap(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)

        today = date.today()
        weekday = today.weekday()
        monday = today - timedelta(days=weekday)
        day_names = ["一", "二", "三", "四", "五", "六", "日"]

        max_sec = 1
        daily_sec: list[int] = []
        for i in range(7):
            d = monday + timedelta(days=i)
            sessions = self._tracker.sessions_for_day(d)
            sec = sum(s.duration_sec for s in sessions)
            daily_sec.append(sec)
            if sec > max_sec:
                max_sec = sec

        for i in range(7):
            row = QHBoxLayout()
            row.setSpacing(8)
            lbl = QLabel(day_names[i])
            lbl.setFixedWidth(20)
            row.addWidget(lbl)

            bar = QProgressBar()
            bar.setObjectName("heatmap_bar")
            bar.setMaximum(max_sec)
            bar.setValue(daily_sec[i])
            bar.setTextVisible(False)
            bar.setFixedHeight(16)
            row.addWidget(bar, 1)

            hours = daily_sec[i] / 3600
            time_lbl = QLabel(f"{hours:.1f}h")
            time_lbl.setFixedWidth(40)
            row.addWidget(time_lbl)

            layout.addLayout(row)
        return widget

    def _build_recent_table(self) -> QTableWidget:
        sessions = self._tracker._sessions[-20:]
        book_last: dict[str, tuple[str, int, int]] = {}
        for s in reversed(sessions):
            if s.book_id not in book_last:
                book_last[s.book_id] = (s.start_time, s.end_page, s.duration_sec)

        table = QTableWidget(min(len(book_last), 10), 3)
        table.setHorizontalHeaderLabels(["书名", "进度", "时长"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.verticalHeader().setVisible(False)

        for row, (book_id, (_start_time, page, dur)) in enumerate(list(book_last.items())[:10]):
            book = self._library.get_book(book_id)
            title = book.title if book else book_id[:8]
            table.setItem(row, 0, QTableWidgetItem(title))
            table.setItem(row, 1, QTableWidgetItem(f"P{page}"))
            minutes = dur // 60
            table.setItem(row, 2, QTableWidgetItem(f"{minutes} 分钟"))

        table.cellDoubleClicked.connect(self._on_row_clicked)
        self._book_ids = list(book_last.keys())[:10]
        return table

    def _on_row_clicked(self, row: int, _col: int) -> None:
        if row < len(self._book_ids):
            self.book_selected.emit(self._book_ids[row])

    def _refresh_data(self) -> None:
        today_min = self._tracker.total_today_sec() // 60
        self._card_time.set_value(f"{today_min} 分钟")
        self._card_pages.set_value(f"{self._tracker.pages_today()} 页")
        self._card_streak.set_value(f"{self._tracker.streak_days()} 天")
        speed = self._tracker.speed_pages_per_hour()
        self._card_speed.set_value(f"{speed:.0f} 页/h")


