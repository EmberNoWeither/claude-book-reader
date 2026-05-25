"""Claude 交互面板 — 底部可折叠面板，包含上下文预览和终端"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core.config import Config
from claude.claude_agent import ClaudeAgent, ClaudeAgentManager
from claude.context_builder import BookContext
from .widgets.terminal_widget import TerminalWidget


class ContextPreview(QWidget):
    """上下文预览条：显示当前选中文字或截图信息"""

    cleared = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._setup_ui()
        self.hide()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        self._icon = QLabel("📎")
        layout.addWidget(self._icon)

        self._label = QLabel("")
        self._label.setStyleSheet("color: #89b4fa; font-size: 12px;")
        self._label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._label.setWordWrap(False)
        layout.addWidget(self._label, stretch=1)

        btn_clear = QToolButton()
        btn_clear.setText("✕")
        btn_clear.setStyleSheet(
            "QToolButton { color: #6c7086; border: none; font-size: 12px; }"
            "QToolButton:hover { color: #f38ba8; }"
        )
        btn_clear.clicked.connect(self._on_clear)
        layout.addWidget(btn_clear)

        self.setStyleSheet("background: #181825; border-bottom: 1px solid #313244;")

    def set_text_selection(self, text: str, page: int) -> None:
        preview = text[:100].replace("\n", " ")
        if len(text) > 100:
            preview += "…"
        self._icon.setText("📝")
        self._label.setText(f"P{page + 1} 选中文字: {preview}")
        self.show()

    def set_screenshot(self, path: str) -> None:
        self._icon.setText("🖼️")
        self._label.setText(f"截图: {path}")
        self.show()

    def clear_context(self) -> None:
        self._label.setText("")
        self.hide()

    def _on_clear(self) -> None:
        self.clear_context()
        self.cleared.emit()


class ClaudePanel(QWidget):
    """底部 Claude 交互面板"""

    screenshot_requested = pyqtSignal()
    save_to_notes_requested = pyqtSignal(str, int, object)  # AI回复文本, page, pdf_rects

    def __init__(self, agent_manager: ClaudeAgentManager, parent=None) -> None:
        super().__init__(parent)
        self._manager = agent_manager
        self._current_book_id = ""
        self._pending_text: str = ""
        self._pending_page: int = 0
        self._pending_pdf_rects: list = []
        self._pending_screenshot: str = ""
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题栏
        header = QWidget()
        header.setFixedHeight(32)
        header.setStyleSheet("background: #181825; border-top: 1px solid #313244;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(8, 0, 8, 0)

        title = QLabel("🤖  Claude")
        title.setStyleSheet("color: #cba6f7; font-weight: bold; font-size: 13px;")
        h_layout.addWidget(title)

        self._book_label = QLabel("")
        self._book_label.setStyleSheet("color: #6c7086; font-size: 12px;")
        h_layout.addWidget(self._book_label, stretch=1)

        # Model selector
        self._model_combo = QComboBox()
        self._model_combo.setFixedWidth(140)
        self._model_combo.setStyleSheet(
            "QComboBox { background: #313244; color: #cdd6f4; border: 1px solid #45475a;"
            " border-radius: 4px; padding: 2px 6px; font-size: 11px; }"
            "QComboBox::drop-down { border: none; }"
            "QComboBox QAbstractItemView { background: #1e1e2e; color: #cdd6f4;"
            " selection-background-color: #45475a; }"
        )
        config = Config()
        models = config.get("claude", "available_models", default=[])
        self._model_combo.addItem("默认模型", "")
        for m in models:
            self._model_combo.addItem(m, m)
        current_model = config.get("claude", "model", default="")
        if current_model:
            idx = self._model_combo.findData(current_model)
            if idx >= 0:
                self._model_combo.setCurrentIndex(idx)
        self._model_combo.currentIndexChanged.connect(self._on_model_changed)
        h_layout.addWidget(self._model_combo)

        btn_screenshot = QPushButton("截图")
        btn_screenshot.setFixedWidth(50)
        btn_screenshot.setStyleSheet(
            "QPushButton { background: #45475a; color: #cdd6f4; border-radius: 4px; padding: 2px 6px; font-size: 12px; }"
            "QPushButton:hover { background: #585b70; }"
        )
        btn_screenshot.clicked.connect(self.screenshot_requested)
        h_layout.addWidget(btn_screenshot)

        btn_chapter = QPushButton("章节分析")
        btn_chapter.setFixedWidth(70)
        btn_chapter.setStyleSheet(
            "QPushButton { background: #45475a; color: #cdd6f4; border-radius: 4px; padding: 2px 6px; font-size: 12px; }"
            "QPushButton:hover { background: #585b70; }"
        )
        btn_chapter.clicked.connect(self._on_chapter_analysis)
        h_layout.addWidget(btn_chapter)

        btn_clear = QPushButton("清空")
        btn_clear.setFixedWidth(44)
        btn_clear.setStyleSheet(
            "QPushButton { background: #45475a; color: #cdd6f4; border-radius: 4px; padding: 2px 6px; font-size: 12px; }"
            "QPushButton:hover { background: #585b70; }"
        )
        btn_clear.clicked.connect(self._on_clear)
        h_layout.addWidget(btn_clear)

        layout.addWidget(header)

        # 上下文预览
        self._ctx_preview = ContextPreview()
        self._ctx_preview.cleared.connect(self._on_context_cleared)
        layout.addWidget(self._ctx_preview)

        # 终端
        self._terminal = TerminalWidget()
        self._terminal.message_submitted.connect(self._on_message_submitted)
        self._terminal.save_to_notes.connect(self._on_save_to_notes)
        layout.addWidget(self._terminal, stretch=1)

    # ── 公共 API ──────────────────────────────────────

    def set_book(self, book_id: str, book: BookContext) -> None:
        self._current_book_id = book_id
        model = self._model_combo.currentData() or ""
        self._manager.get_or_create(book_id, book, model=model)
        self._book_label.setText(f"· {book.title}")
        self._terminal.clear()
        self._ctx_preview.clear_context()

    def close_book(self, book_id: str) -> None:
        if self._current_book_id == book_id:
            self._current_book_id = ""
            self._book_label.setText("")
            self._ctx_preview.clear_context()

    def set_text_selection(self, text: str, page: int, pdf_rects: list | None = None) -> None:
        """从阅读视图接收选中文字"""
        self._pending_text = text
        self._pending_page = page
        self._pending_pdf_rects = pdf_rects or []
        self._pending_screenshot = ""
        self._ctx_preview.set_text_selection(text, page)
        self._terminal.focus_input()

    def set_screenshot(self, path: str) -> None:
        """从截图工具接收截图路径"""
        self._pending_screenshot = path
        self._pending_text = ""
        self._ctx_preview.set_screenshot(path)
        self._terminal.focus_input()

    def update_page(self, page: int, chapter: str) -> None:
        agent = self._agent()
        if agent:
            agent.update_book_context(page, chapter)

    # ── 内部 ─────────────────────────────────────────

    def _agent(self) -> ClaudeAgent | None:
        return self._manager.get(self._current_book_id)

    def _on_message_submitted(self, text: str) -> None:
        agent = self._agent()
        if not agent:
            self._terminal.append_error("请先打开一本书再与 Claude 交互。")
            return
        if agent.is_busy:
            return

        self._terminal.append_user(text)
        self._terminal.begin_assistant_stream()
        self._terminal.set_busy(True)

        agent.response_chunk.connect(self._terminal.append_assistant_chunk)
        agent.response_finished.connect(self._on_response_finished)
        agent.error_occurred.connect(self._on_error)

        if self._pending_screenshot:
            agent.send_screenshot_question(self._pending_screenshot, text)
        elif self._pending_text:
            agent.send_text_question(
                selected_text=self._pending_text,
                surrounding_text="",
                page=self._pending_page,
                user_query=text,
            )
        else:
            agent.send_general_question(text)

    def _on_response_finished(self, full_text: str) -> None:
        agent = self._agent()
        if agent:
            agent.response_chunk.disconnect(self._terminal.append_assistant_chunk)
            agent.response_finished.disconnect(self._on_response_finished)
            agent.error_occurred.disconnect(self._on_error)
        self._terminal.finish_assistant_stream(full_text)
        self._terminal.set_busy(False)

    def _on_error(self, err: str) -> None:
        agent = self._agent()
        if agent:
            try:
                agent.response_chunk.disconnect(self._terminal.append_assistant_chunk)
                agent.response_finished.disconnect(self._on_response_finished)
                agent.error_occurred.disconnect(self._on_error)
            except RuntimeError:
                pass
        self._terminal.finish_assistant_stream("")
        self._terminal.append_error(err)
        self._terminal.set_busy(False)

    def _on_chapter_analysis(self) -> None:
        agent = self._agent()
        if not agent or agent.is_busy:
            return
        self._terminal.append_user("[章节分析请求]")
        self._terminal.begin_assistant_stream()
        self._terminal.set_busy(True)
        agent.response_chunk.connect(self._terminal.append_assistant_chunk)
        agent.response_finished.connect(self._on_response_finished)
        agent.error_occurred.connect(self._on_error)
        agent.send_chapter_analysis(chapter_text="")

    def _on_clear(self) -> None:
        self._terminal.clear()
        agent = self._agent()
        if agent:
            agent.clear_history()

    def _on_context_cleared(self) -> None:
        self._pending_text = ""
        self._pending_pdf_rects = []
        self._pending_screenshot = ""

    def _on_save_to_notes(self, text: str) -> None:
        self.save_to_notes_requested.emit(text, self._pending_page, self._pending_pdf_rects)

    def _on_model_changed(self, index: int) -> None:
        model = self._model_combo.itemData(index) or ""
        config = Config()
        config.set("claude", "model", value=model)
        config.save()
        self._manager.set_model_all(model)

    @property
    def current_model(self) -> str:
        return self._model_combo.currentData() or ""
