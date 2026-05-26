"""状态栏"""

from __future__ import annotations

from PyQt6.QtWidgets import QLabel, QStatusBar


class ReaderStatusBar(QStatusBar):
    """底部状态栏"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._book_label = QLabel("📖 未打开书籍")
        self._page_label = QLabel("")
        self._mode_label = QLabel("")
        self._zoom_label = QLabel("")
        self._streak_label = QLabel("")

        self.addWidget(self._book_label, 1)
        self.addPermanentWidget(self._zoom_label)
        self.addPermanentWidget(self._mode_label)
        self.addPermanentWidget(self._page_label)
        self.addPermanentWidget(self._streak_label)

    def set_book(self, title: str) -> None:
        self._book_label.setText(f"📖 {title}")

    def set_page(self, current: int, total: int) -> None:
        self._page_label.setText(f"P{current}/{total}")

    def set_mode(self, mode: str) -> None:
        self._mode_label.setText(mode)

    def set_zoom(self, pct: int) -> None:
        self._zoom_label.setText(f"🔍 {pct}%")

    def set_streak(self, days: int) -> None:
        self._streak_label.setText(f"🔥 {days}天")

    def clear_book(self) -> None:
        self._book_label.setText("📖 未打开书籍")
        self._page_label.setText("")
        self._mode_label.setText("")
        self._zoom_label.setText("")
