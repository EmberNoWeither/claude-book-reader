"""Bookmark list panel — add, delete, jump to bookmarks."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.book import Bookmark
from core.library import Library


class BookmarkWidget(QWidget):
    """Panel showing bookmarks for the current book."""

    jump_to_page = pyqtSignal(int)  # page_number

    def __init__(self, library: Library, parent=None) -> None:
        super().__init__(parent)
        self._library = library
        self._book_id: str = ""
        self._bookmarks: list[Bookmark] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        header = QHBoxLayout()
        title = QLabel("🔖 书签")
        title.setStyleSheet("font-weight: bold; color: #aaa; font-size: 11px;")
        header.addWidget(title)
        header.addStretch()

        btn_add = QPushButton("+")
        btn_add.setFixedSize(24, 24)
        btn_add.setStyleSheet(
            "QPushButton { background: #333; color: #aaa; border-radius: 12px; font-size: 14px; }"
            "QPushButton:hover { background: #555; }"
        )
        btn_add.clicked.connect(self._on_add)
        header.addWidget(btn_add)

        layout.addLayout(header)

        self._list = QListWidget()
        self._list.setStyleSheet(
            "QListWidget { background: #1e1e2e; border: 1px solid #313244; border-radius: 6px; }"
            "QListWidget::item { padding: 6px; }"
            "QListWidget::item:hover { background: #313244; }"
            "QListWidget::item:selected { background: #45475a; }"
        )
        self._list.itemDoubleClicked.connect(self._on_jump)
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._on_context_menu)
        layout.addWidget(self._list)

    # ═══════════════════════════════
    # Public API
    # ═══════════════════════════════

    def set_book(self, book_id: str) -> None:
        self._book_id = book_id
        self.refresh()

    def refresh(self) -> None:
        self._list.clear()
        if not self._book_id:
            return
        self._bookmarks = self._library.list_bookmarks(self._book_id)
        for bm in self._bookmarks:
            label = bm.title or f"第 {bm.page_number + 1} 页"
            chapter = f"  — {bm.chapter_title}" if bm.chapter_title else ""
            item = QListWidgetItem(f"📍 P{bm.page_number + 1} {label}{chapter}")
            item.setData(Qt.ItemDataRole.UserRole, bm.id)
            self._list.addItem(item)

    # ═══════════════════════════════
    # Slots
    # ═══════════════════════════════

    def _on_add(self) -> None:
        pass  # Handled via ReadingView toolbar instead

    def _on_jump(self, item: QListWidgetItem) -> None:
        bm_id = item.data(Qt.ItemDataRole.UserRole)
        for bm in self._bookmarks:
            if bm.id == bm_id:
                self.jump_to_page.emit(bm.page_number)
                return

    def _on_context_menu(self, pos) -> None:
        item = self._list.itemAt(pos)
        if item is None:
            return
        from PyQt6.QtWidgets import QMenu

        bm_id = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        act_del = menu.addAction("删除书签")
        action = menu.exec(self._list.mapToGlobal(pos))
        if action == act_del:
            self._library.remove_bookmark(self._book_id, bm_id)
            self.refresh()
