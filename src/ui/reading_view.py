"""Reading view container — toolbar + page canvas."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QAction, QCursor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QMenu,
)

from core.book import Bookmark
from core.library import Library
from .reading_toolbar import ReadingToolbar
from .widgets.page_canvas import PageCanvas


class ReadingView(QWidget):
    """Central reading area combining toolbar, canvas, and bookmarks."""

    page_changed = pyqtSignal(int, int)  # current (0-based), total
    zoom_changed = pyqtSignal(float)
    text_selected = pyqtSignal(str, int)  # selected_text, page_number
    selection_cleared = pyqtSignal()
    book_opened = pyqtSignal(str)  # book_id
    book_closed = pyqtSignal()
    ask_claude = pyqtSignal(str, int)    # selected_text, page — 用户点击"问 Claude"
    create_note = pyqtSignal(str, int, object)   # selected_text, page, pdf_rects

    def __init__(self, library: Library, parent=None) -> None:
        super().__init__(parent)
        self._library = library
        self._book_id: str = ""
        self._selected_text: str = ""
        self._selected_page: int = 0
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        self._toolbar = ReadingToolbar()
        self._toolbar.mode_changed.connect(self._on_mode_changed)
        self._toolbar.zoom_in.connect(self._on_zoom_in)
        self._toolbar.zoom_out.connect(self._on_zoom_out)
        self._toolbar.fit_width.connect(self._on_fit_width)
        self._toolbar.fit_page.connect(self._on_fit_page)
        self._toolbar.zoom_original.connect(self._on_zoom_original)
        self._toolbar.go_to_page.connect(self._on_go_to_page)
        self._toolbar.add_bookmark.connect(self._on_add_bookmark)
        layout.addWidget(self._toolbar)

        # Selection status bar (with floating action buttons)
        self._sel_label = QLabel("")
        self._sel_label.setStyleSheet(
            "QLabel { background: #313244; color: #89b4fa; padding: 3px 12px; font-size: 12px; }"
        )
        self._sel_label.hide()
        self._sel_label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        layout.addWidget(self._sel_label)

        # Canvas
        self._canvas = PageCanvas()
        self._canvas.page_changed.connect(self._on_page_changed)
        self._canvas.zoom_changed.connect(self._on_zoom_changed)
        self._canvas.text_selected.connect(self._on_text_selected)
        self._canvas.selection_cleared.connect(self._on_selection_cleared)
        layout.addWidget(self._canvas, stretch=1)

    # ═══════════════════════════════
    # Public API
    # ═══════════════════════════════

    def open_book(self, book_id: str, file_path: str) -> None:
        self._book_id = book_id
        self._canvas.open_book(file_path)
        self._toolbar.set_page(0, self._canvas.total_pages)
        self._toolbar.set_zoom(self._canvas.display_zoom)
        self._update_bookmark_btn()
        self.book_opened.emit(book_id)

    def close_book(self) -> None:
        self._book_id = ""
        self._canvas.close_book()
        self._sel_label.hide()
        self.selection_cleared.emit()
        self.book_closed.emit()

    @property
    def has_book(self) -> bool:
        return self._canvas.has_book

    @property
    def canvas(self) -> PageCanvas:
        return self._canvas

    # ═══════════════════════════════
    # Slots — toolbar
    # ═══════════════════════════════

    def _on_mode_changed(self, mode: str) -> None:
        self._canvas.set_mode(mode)

    def _on_zoom_in(self) -> None:
        self._canvas.zoom_in()

    def _on_zoom_out(self) -> None:
        self._canvas.zoom_out()

    def _on_fit_width(self) -> None:
        self._canvas.fit_width()

    def _on_fit_page(self) -> None:
        self._canvas.fit_page()

    def _on_zoom_original(self) -> None:
        self._canvas.zoom_original()

    def _on_go_to_page(self, page: int) -> None:
        self._canvas.go_to_page(page)

    def _on_add_bookmark(self) -> None:
        if not self._book_id:
            return
        bm = Bookmark(
            book_id=self._book_id,
            page_number=self._canvas.current_page,
        )
        self._library.add_bookmark(bm)

    # ═══════════════════════════════
    # Slots — canvas
    # ═══════════════════════════════

    def _on_page_changed(self, page: int, total: int) -> None:
        self._toolbar.set_page(page, total)
        self.page_changed.emit(page, total)
        # Persist reading progress
        if self._book_id:
            self._library.update_reading_progress(self._book_id, page)

    def _on_zoom_changed(self, zoom: float) -> None:
        self._toolbar.set_zoom(zoom)
        self.zoom_changed.emit(zoom)

    def _on_text_selected(self, text: str, page: int) -> None:
        self._selected_text = text
        self._selected_page = page
        preview = text[:80].replace("\n", " ")
        if len(text) > 80:
            preview += "..."
        self._sel_label.setText(f"  已选中 (P{page + 1}): {preview}")
        self._sel_label.show()
        self.text_selected.emit(text, page)
        # Show menu at current cursor position (where mouse was released)
        self._show_selection_menu(QCursor.pos())

    def _show_selection_menu(self, pos: "QPoint") -> None:
        """在指定位置弹出选中文字操作菜单"""
        if not self._selected_text:
            return
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 6px; }"
            "QMenu::item { padding: 6px 16px; }"
            "QMenu::item:selected { background: #45475a; }"
        )
        act_claude = QAction("🤖  问 Claude", self)
        act_claude.triggered.connect(self._on_ask_claude)
        menu.addAction(act_claude)

        act_copy = QAction("📋  复制", self)
        act_copy.triggered.connect(self._on_copy_selection)
        menu.addAction(act_copy)

        act_translate = QAction("🌐  翻译（Claude）", self)
        act_translate.triggered.connect(self._on_translate)
        menu.addAction(act_translate)

        act_note = QAction("📝  笔记", self)
        act_note.triggered.connect(self._on_create_note)
        menu.addAction(act_note)

        menu.exec(pos)

    def _on_ask_claude(self) -> None:
        if self._selected_text:
            self.ask_claude.emit(self._selected_text, self._selected_page)

    def _on_create_note(self) -> None:
        if self._selected_text:
            pdf_rects = self.canvas.selected_pdf_rects
            self.create_note.emit(self._selected_text, self._selected_page, pdf_rects)

    def _on_copy_selection(self) -> None:
        from PyQt6.QtWidgets import QApplication
        if self._selected_text:
            QApplication.clipboard().setText(self._selected_text)

    def _on_translate(self) -> None:
        # 翻译也走 ask_claude 信号，面板自动加前缀
        if self._selected_text:
            self.ask_claude.emit(f"[翻译] {self._selected_text}", self._selected_page)

    def _on_selection_cleared(self) -> None:
        self._sel_label.hide()
        self.selection_cleared.emit()

    def _update_bookmark_btn(self) -> None:
        pass
