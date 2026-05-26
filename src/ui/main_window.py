"""主窗口 — 面板布局编排"""

from __future__ import annotations

from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QMainWindow,
    QMenu,
    QMessageBox,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from claude.claude_agent import ClaudeAgentManager
from claude.claude_client import TitleGenerator
from claude.context_builder import BookContext
from core.config import Config
from core.library import Library
from core.reading_tracker import ReadingTracker
from core.storage import Storage

from .claude_panel import ClaudePanel
from .library_panel import LibraryPanel
from .notes_panel import NotesPanel
from .reading_view import ReadingView
from .status_bar import ReaderStatusBar
from .widgets.bookmark_widget import BookmarkWidget
from .widgets.page_canvas import (
    MODE_DOUBLE_CONTINUOUS,
    MODE_DOUBLE_FLIP,
    MODE_SINGLE_CONTINUOUS,
    MODE_SINGLE_FLIP,
)
from .widgets.screenshot_tool import ScreenshotTool


class MainWindow(QMainWindow):
    """应用主窗口"""

    def __init__(self, library: Library, config: Config, storage: Storage | None = None, theme_manager=None) -> None:
        super().__init__()
        self._library = library
        self._config = config
        self._storage = storage
        self._theme_manager = theme_manager
        self._agent_manager = ClaudeAgentManager(self)
        self._title_generator = TitleGenerator(parent=self)
        self._title_generator.title_generated.connect(self._on_title_generated)
        self._screenshot_tool = ScreenshotTool()
        self._screenshot_tool.screenshot_taken.connect(self._on_screenshot_taken)

        self._tracker = ReadingTracker(
            storage or Storage(self._config.data_dir), self._config, self
        )

        self.setWindowTitle("Claude Book Reader")
        self.setMinimumSize(1200, 750)
        self.resize(1400, 900)

        self._setup_menu()
        self._setup_ui()
        self._setup_shortcuts()
        self._setup_statusbar()
        self._restore_geometry()

    # ── 菜单栏 ────────────────────────────────────────

    def _setup_menu(self) -> None:
        mb = self.menuBar()

        # 文件
        file_menu = mb.addMenu("文件 (&F)")
        act_import = QAction("导入图书 (&O)", self)
        act_import.setShortcut(QKeySequence("Ctrl+O"))
        act_import.triggered.connect(self._on_import)
        file_menu.addAction(act_import)
        act_close = QAction("关闭书籍", self)
        act_close.setShortcut(QKeySequence("Ctrl+W"))
        act_close.triggered.connect(self._on_close_book)
        file_menu.addAction(act_close)
        file_menu.addSeparator()
        act_quit = QAction("退出 (&Q)", self)
        act_quit.setShortcut(QKeySequence("Ctrl+Q"))
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        # 视图
        view_menu = mb.addMenu("视图 (&V)")
        act_toggle_lib = QAction("切换书库面板", self)
        act_toggle_lib.setShortcut(QKeySequence("Ctrl+Shift+L"))
        act_toggle_lib.triggered.connect(self._toggle_library)
        view_menu.addAction(act_toggle_lib)
        act_toggle_notes = QAction("切换书签面板", self)
        act_toggle_notes.setShortcut(QKeySequence("Ctrl+Shift+N"))
        act_toggle_notes.triggered.connect(self._toggle_bookmarks)
        view_menu.addAction(act_toggle_notes)
        act_toggle_claude = QAction("切换 Claude 面板", self)
        act_toggle_claude.setShortcut(QKeySequence("Ctrl+Shift+A"))
        act_toggle_claude.triggered.connect(self._toggle_claude_panel)
        view_menu.addAction(act_toggle_claude)
        view_menu.addSeparator()

        act_mode1 = QAction("单页连续滚动", self)
        act_mode1.setShortcut(QKeySequence("Ctrl+1"))
        act_mode1.triggered.connect(lambda: self._set_reading_mode(MODE_SINGLE_CONTINUOUS))
        view_menu.addAction(act_mode1)

        act_mode2 = QAction("双页连续滚动", self)
        act_mode2.setShortcut(QKeySequence("Ctrl+2"))
        act_mode2.triggered.connect(lambda: self._set_reading_mode(MODE_DOUBLE_CONTINUOUS))
        view_menu.addAction(act_mode2)

        act_mode3 = QAction("单页翻页", self)
        act_mode3.setShortcut(QKeySequence("Ctrl+3"))
        act_mode3.triggered.connect(lambda: self._set_reading_mode(MODE_SINGLE_FLIP))
        view_menu.addAction(act_mode3)

        act_mode4 = QAction("双页翻页", self)
        act_mode4.setShortcut(QKeySequence("Ctrl+4"))
        act_mode4.triggered.connect(lambda: self._set_reading_mode(MODE_DOUBLE_FLIP))
        view_menu.addAction(act_mode4)

        view_menu.addSeparator()
        act_fullscreen = QAction("全屏阅读", self)
        act_fullscreen.setShortcut(QKeySequence("F11"))
        act_fullscreen.triggered.connect(self._toggle_fullscreen)
        view_menu.addAction(act_fullscreen)

        # 工具
        tools_menu = mb.addMenu("工具 (&T)")
        act_export_obsidian = QAction("导出到 Obsidian", self)
        act_export_obsidian.setShortcut(QKeySequence("Ctrl+E"))
        act_export_obsidian.triggered.connect(self._on_export_obsidian)
        tools_menu.addAction(act_export_obsidian)
        act_graph = QAction("知识图谱", self)
        act_graph.setShortcut(QKeySequence("Ctrl+Shift+K"))
        act_graph.triggered.connect(self._on_show_graph)
        tools_menu.addAction(act_graph)
        act_dashboard = QAction("阅读仪表盘", self)
        act_dashboard.setShortcut(QKeySequence("Ctrl+D"))
        act_dashboard.triggered.connect(self._on_show_dashboard)
        tools_menu.addAction(act_dashboard)
        tools_menu.addSeparator()
        act_settings = QAction("设置...", self)
        act_settings.setShortcut(QKeySequence("Ctrl+,"))
        act_settings.triggered.connect(self._on_show_settings)
        tools_menu.addAction(act_settings)

        # 帮助
        help_menu = mb.addMenu("帮助 (&H)")
        act_about = QAction("关于", self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

    # ── 快捷键 ────────────────────────────────────────

    def _setup_shortcuts(self) -> None:
        # Zoom shortcuts handled globally on the window
        act_zoomin = QAction("放大", self)
        act_zoomin.setShortcut(QKeySequence("Ctrl+="))
        act_zoomin.triggered.connect(self._on_zoom_in)
        self.addAction(act_zoomin)

        act_zoomout = QAction("缩小", self)
        act_zoomout.setShortcut(QKeySequence("Ctrl+-"))
        act_zoomout.triggered.connect(self._on_zoom_out)
        self.addAction(act_zoomout)

        act_zoom0 = QAction("原始大小", self)
        act_zoom0.setShortcut(QKeySequence("Ctrl+0"))
        act_zoom0.triggered.connect(self._on_zoom_original)
        self.addAction(act_zoom0)

        act_fitw = QAction("适应宽度", self)
        act_fitw.setShortcut(QKeySequence("Ctrl+Shift+W"))
        act_fitw.triggered.connect(self._on_fit_width)
        self.addAction(act_fitw)

        act_jump = QAction("跳转页码", self)
        act_jump.setShortcut(QKeySequence("Ctrl+G"))
        act_jump.triggered.connect(self._on_goto_page)
        self.addAction(act_jump)

        act_bm = QAction("添加书签", self)
        act_bm.setShortcut(QKeySequence("Ctrl+B"))
        act_bm.triggered.connect(self._on_add_bookmark)
        self.addAction(act_bm)

        act_screenshot = QAction("截图选区", self)
        act_screenshot.setShortcut(QKeySequence("Ctrl+Shift+S"))
        act_screenshot.triggered.connect(self._on_screenshot)
        self.addAction(act_screenshot)

    # ── 面板布局 ──────────────────────────────────────

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout_root = QVBoxLayout(central)
        layout_root.setContentsMargins(0, 0, 0, 0)
        layout_root.setSpacing(0)

        # 垂直分割器：上方主区域 | 下方 Claude 面板
        self._splitter_vert = QSplitter(Qt.Orientation.Vertical)
        layout_root.addWidget(self._splitter_vert)

        # ── 上方：主水平分割器 ──
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)

        self._splitter_main = QSplitter(Qt.Orientation.Horizontal)
        top_layout.addWidget(self._splitter_main)

        # 左侧 — 图书库
        self._library_panel = LibraryPanel(self._library)
        self._library_panel.book_selected.connect(self._on_book_selected)
        self._splitter_main.addWidget(self._library_panel)

        # 中央 — 阅读区
        self._reading_view = ReadingView(self._library)
        self._reading_view.page_changed.connect(self._on_page_changed)
        self._reading_view.zoom_changed.connect(self._on_zoom_changed)
        self._reading_view.text_selected.connect(self._on_text_selected)
        self._reading_view.selection_cleared.connect(self._on_selection_cleared)
        self._reading_view.book_opened.connect(self._on_book_opened)
        self._reading_view.book_closed.connect(self._on_book_closed)
        self._reading_view.ask_claude.connect(self._on_ask_claude)
        self._reading_view.create_note.connect(self._on_create_note)
        self._reading_view.canvas.note_highlight_right_clicked.connect(self._on_note_highlight_menu)
        self._splitter_main.addWidget(self._reading_view)

        # 右侧 — 书签 + 笔记 Tab
        self._right_tabs = QTabWidget()
        self._right_tabs.setObjectName("right_tabs")
        self._bookmark_widget = BookmarkWidget(self._library)
        self._bookmark_widget.jump_to_page.connect(self._on_bookmark_jump)
        self._right_tabs.addTab(self._bookmark_widget, "🔖 书签")

        self._notes_panel = NotesPanel(self._storage) if self._storage else NotesPanel(Storage(self._config.data_dir))
        self._notes_panel.jump_to_page.connect(self._on_bookmark_jump)
        self._notes_panel.optimize_requested.connect(self._on_optimize_note)
        self._notes_panel.extract_concepts_requested.connect(self._on_extract_concepts)
        self._notes_panel.optimize_title_requested.connect(self._on_optimize_title)
        self._notes_panel.set_live_page_getter(lambda: self._reading_view.canvas.current_page)
        self._right_tabs.addTab(self._notes_panel, "📝 笔记")

        self._right_tabs.setMinimumWidth(220)
        self._splitter_main.addWidget(self._right_tabs)

        # 比例：书库 260, 阅读区 stretch, 书签 220
        self._splitter_main.setSizes([260, 920, 220])
        self._splitter_main.setStretchFactor(0, 0)
        self._splitter_main.setStretchFactor(1, 1)
        self._splitter_main.setStretchFactor(2, 0)

        self._splitter_vert.addWidget(top_widget)

        # ── 下方：Claude 面板 ──
        self._claude_panel = ClaudePanel(self._agent_manager)
        self._claude_panel.screenshot_requested.connect(self._on_screenshot)
        self._claude_panel.save_to_notes_requested.connect(self._on_save_claude_to_notes)
        self._claude_panel.setMinimumHeight(60)
        self._splitter_vert.addWidget(self._claude_panel)

        # 垂直比例：上方占主要空间，Claude 面板 220px
        self._splitter_vert.setSizes([680, 220])
        self._splitter_vert.setStretchFactor(0, 1)
        self._splitter_vert.setStretchFactor(1, 0)

    # ── 状态栏 ────────────────────────────────────────

    def _setup_statusbar(self) -> None:
        self._statusbar = ReaderStatusBar()
        self.setStatusBar(self._statusbar)

    # ── 窗口状态持久化 ────────────────────────────────

    def _restore_geometry(self) -> None:
        s = QSettings("ClaudeBookReader", "MainWindow")
        geo = s.value("geometry")
        if geo:
            self.restoreGeometry(geo)
        state = s.value("windowState")
        if state:
            self.restoreState(state)

    def _save_book_view_state(self) -> None:
        """Persist current book's zoom level and reading mode."""
        book_id = getattr(self._reading_view, "_book_id", "")
        if not book_id:
            return
        book = self._library.get_book(book_id)
        if not book:
            return
        book.zoom_level = self._reading_view.canvas.display_zoom
        book.reading_mode = self._reading_view.canvas.mode
        self._library.update_book(book)

    def closeEvent(self, event) -> None:
        self._tracker.end_session()
        self._save_book_view_state()
        s = QSettings("ClaudeBookReader", "MainWindow")
        s.setValue("geometry", self.saveGeometry())
        s.setValue("windowState", self.saveState())
        super().closeEvent(event)

    # ── 槽：文件操作 ─────────────────────────────────

    def _on_import(self) -> None:
        self._library_panel.import_book()

    def _on_close_book(self) -> None:
        self._reading_view.close_book()

    # ── 槽：书库选择 ─────────────────────────────────

    def _on_book_selected(self, book_id: str) -> None:
        book = self._library.get_book(book_id)
        if book is None:
            return
        self._reading_view.open_book(book_id, book.file_path)
        self._bookmark_widget.set_book(book_id)

    def _on_book_opened(self, book_id: str) -> None:
        book = self._library.get_book(book_id)
        if book:
            self._statusbar.set_book(book.title)
            self.setWindowTitle(f"{book.title} — Claude Book Reader")

            # Restore reading mode (per-book > config default)
            mode = book.reading_mode or self._config.get("app", "default_reading_mode", default="single_continuous")
            self._reading_view.canvas.set_mode(mode)
            mode_names = {
                MODE_SINGLE_CONTINUOUS: "单页连续",
                MODE_DOUBLE_CONTINUOUS: "双页连续",
                MODE_SINGLE_FLIP: "单页翻页",
                MODE_DOUBLE_FLIP: "双页翻页",
            }
            self._statusbar.set_mode(mode_names.get(mode, "单页连续"))

            # Restore zoom level
            if book.zoom_level > 0:
                self._reading_view.canvas.set_zoom(book.zoom_level)

            # Restore reading position
            if book.current_page > 0:
                self._reading_view.canvas.go_to_page(book.current_page)

            # Start reading session
            self._tracker.start_session(book_id, book.current_page)
            self._statusbar.set_streak(self._tracker.streak_days())
            # 初始化 Claude Agent
            book_ctx = BookContext(
                title=book.title,
                author=book.author or "",
                current_page=book.current_page,
                total_pages=book.pages,
            )
            self._claude_panel.set_book(book_id, book_ctx)
            self._notes_panel.set_book(book_id)
            self._sync_note_highlights(book_id)
        self._library_panel.refresh()

    def _on_book_closed(self) -> None:
        self._tracker.end_session()
        self._save_book_view_state()
        book_id = getattr(self._reading_view, "_book_id", "")
        self._statusbar.clear_book()
        self._bookmark_widget.set_book("")
        self._notes_panel.close_book()
        self._claude_panel.close_book(book_id)
        self.setWindowTitle("Claude Book Reader")
        self._library_panel.refresh()

    # ── 槽：阅读状态 ─────────────────────────────────

    def _on_page_changed(self, page: int, total: int) -> None:
        self._statusbar.set_page(page + 1, total)
        self._claude_panel.update_page(page, "")
        self._notes_panel.set_current_page(page)
        self._tracker.update_progress(page)

    def _on_zoom_changed(self, zoom: float) -> None:
        self._statusbar.set_zoom(int(zoom * 100))

    def _on_text_selected(self, text: str, page: int) -> None:
        self._statusbar.showMessage(f"已选中 {len(text)} 个字符 (P{page + 1})", 5000)

    def _on_selection_cleared(self) -> None:
        self._statusbar.clearMessage()

    def _on_ask_claude(self, text: str, page: int) -> None:
        """用户点击"问 Claude"，将选中文字发送到 Claude 面板"""
        pdf_rects = self._reading_view.canvas.selected_pdf_rects
        self._claude_panel.set_text_selection(text, page, pdf_rects)
        # 确保 Claude 面板可见
        if self._claude_panel.height() < 80:
            self._splitter_vert.setSizes([580, 320])

    # ── 槽：阅读模式 ─────────────────────────────────

    def _set_reading_mode(self, mode: str) -> None:
        self._reading_view.canvas.set_mode(mode)
        mode_names = {
            MODE_SINGLE_CONTINUOUS: "单页连续",
            MODE_DOUBLE_CONTINUOUS: "双页连续",
            MODE_SINGLE_FLIP: "单页翻页",
            MODE_DOUBLE_FLIP: "双页翻页",
        }
        self._statusbar.set_mode(mode_names.get(mode, mode))

    # ── 槽：缩放快捷键 ───────────────────────────────

    def _on_zoom_in(self) -> None:
        self._reading_view.canvas.zoom_in()

    def _on_zoom_out(self) -> None:
        self._reading_view.canvas.zoom_out()

    def _on_zoom_original(self) -> None:
        self._reading_view.canvas.zoom_original()

    def _on_fit_width(self) -> None:
        self._reading_view.canvas.fit_width()

    # ── 槽：跳转 ─────────────────────────────────────

    def _on_goto_page(self) -> None:
        from PyQt6.QtWidgets import QInputDialog
        current = self._reading_view.canvas.current_page + 1
        total = self._reading_view.canvas.total_pages
        page, ok = QInputDialog.getInt(
            self, "跳转页码", f"输入页码 (1-{total}):",
            value=current, min=1, max=total,
        )
        if ok:
            self._reading_view.canvas.go_to_page(page - 1)

    # ── 槽：书签 ─────────────────────────────────────

    def _on_add_bookmark(self) -> None:
        self._reading_view._on_add_bookmark()
        self._bookmark_widget.refresh()

    def _on_bookmark_jump(self, page: int) -> None:
        self._reading_view.canvas.go_to_page(page)

    # ── 槽：面板切换 ────────────────────────────────

    def _toggle_library(self) -> None:
        self._library_panel.setVisible(not self._library_panel.isVisible())

    def _toggle_bookmarks(self) -> None:
        self._right_tabs.setVisible(not self._right_tabs.isVisible())

    def _toggle_claude_panel(self) -> None:
        if self._claude_panel.height() < 40:
            self._splitter_vert.setSizes([580, 320])
        else:
            sizes = self._splitter_vert.sizes()
            total = sum(sizes)
            self._splitter_vert.setSizes([total, 0])

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    # ── 槽：截图 ─────────────────────────────────────

    def _on_screenshot(self) -> None:
        self._screenshot_tool.activate()

    def _on_screenshot_taken(self, path: str) -> None:
        self._claude_panel.set_screenshot(path)
        if self._claude_panel.height() < 80:
            self._splitter_vert.setSizes([580, 320])

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "关于 Claude Book Reader",
            "Claude Book Reader v0.1.0\n\n"
            "PDF 图书管理与阅读器\n"
            "深度集成 Claude Code 实现智能阅读辅助",
        )

    # ── 槽：笔记优化 & 概念提取 ─────────────────────

    def _on_optimize_note(self, note_id: str, style: str) -> None:
        book_id = getattr(self._reading_view, "_book_id", "")
        if not book_id:
            return
        agent = self._agent_manager.get(book_id)
        if not agent:
            return
        from notes.note_manager import NoteManager
        nm = NoteManager(self._storage or Storage(self._config.data_dir))
        note = nm.get_note(book_id, note_id)
        if not note:
            return
        agent.send_note_optimization(note.content, style)

    def _on_extract_concepts(self, book_id: str) -> None:
        agent = self._agent_manager.get(book_id)
        if not agent:
            QMessageBox.information(self, "提取概念", "请先打开书籍并与 Claude 建立连接")
            return
        if agent.is_busy:
            QMessageBox.information(self, "提取概念", "Claude 正在处理中，请稍后再试")
            return
        from notes.note_manager import NoteManager
        nm = NoteManager(self._storage or Storage(self._config.data_dir))
        notes = nm.list_notes(book_id)
        if not notes:
            QMessageBox.information(self, "提取概念", "当前书籍暂无笔记，请先创建笔记再提取概念")
            return
        all_content = "\n\n".join(n.content for n in notes if n.content)
        self._statusbar.showMessage("正在提取概念...", 0)
        agent.response_finished.connect(self._on_concept_extraction_done)
        agent.error_occurred.connect(self._on_concept_extraction_error)
        agent.send_concept_extraction(all_content)

    def _on_concept_extraction_done(self, response: str) -> None:
        agent = self.sender()
        if agent:
            try:
                agent.response_finished.disconnect(self._on_concept_extraction_done)
                agent.error_occurred.disconnect(self._on_concept_extraction_error)
            except RuntimeError:
                pass
        from knowledge.concept_extractor import ConceptExtractor
        from knowledge.graph_engine import GraphEngine
        storage = self._storage or Storage(self._config.data_dir)
        graph = GraphEngine(storage)
        extractor = ConceptExtractor(graph)
        book_id = getattr(self._reading_view, "_book_id", "")
        concepts = extractor.process_response(response, book_id)
        if concepts:
            self._statusbar.showMessage(f"已提取 {len(concepts)} 个概念", 5000)
            QMessageBox.information(
                self, "概念提取完成",
                f"成功提取 {len(concepts)} 个概念:\n\n"
                + "\n".join(f"• {c.name}" for c in concepts[:10])
            )
        else:
            self._statusbar.showMessage("未能提取到概念", 3000)

    def _on_concept_extraction_error(self, err: str) -> None:
        agent = self.sender()
        if agent:
            try:
                agent.response_finished.disconnect(self._on_concept_extraction_done)
                agent.error_occurred.disconnect(self._on_concept_extraction_error)
            except RuntimeError:
                pass
        self._statusbar.showMessage("概念提取失败", 3000)
        QMessageBox.warning(self, "概念提取失败", f"错误: {err}")

    def _on_create_note(self, text: str, page: int, pdf_rects=None) -> None:
        self._notes_panel.create_note_from_selection(text, page, pdf_rects or [])
        self._right_tabs.setCurrentWidget(self._notes_panel)
        self._sync_note_highlights()

    def _on_export_obsidian(self) -> None:
        from notes.obsidian_exporter import ObsidianExporter
        storage = self._storage or Storage(self._config.data_dir)
        exporter = ObsidianExporter(storage, self._config, self._library)
        book_id = getattr(self._reading_view, "_book_id", "")
        try:
            if book_id:
                result = exporter.export_book(book_id)
            else:
                result = exporter.export_all()
            msg = f"导出完成: {result.files_created} 新建, {result.files_updated} 更新"
            if result.errors:
                msg += f"\n错误: {'; '.join(result.errors[:3])}"
            self._statusbar.showMessage(msg, 5000)
            QMessageBox.information(self, "Obsidian 导出", msg)
        except Exception as e:
            QMessageBox.warning(self, "导出失败", f"Obsidian 导出出错:\n{e}")

    def _on_show_graph(self) -> None:
        from .widgets.graph_canvas import GraphDialog
        book_id = getattr(self._reading_view, "_book_id", "")
        storage = self._storage or Storage(self._config.data_dir)
        dlg = GraphDialog(storage, book_id, self)
        dlg.exec()

    def _on_show_dashboard(self) -> None:
        from .dialogs.dashboard import DashboardDialog
        dlg = DashboardDialog(self._tracker, self._library, self)
        dlg.book_selected.connect(self._on_book_selected)
        dlg.exec()

    def _on_show_settings(self) -> None:
        from .dialogs.settings import SettingsDialog
        dlg = SettingsDialog(self._config, self._theme_manager, self)
        dlg.exec()

    def _on_save_claude_to_notes(self, text: str, page: int = -1, pdf_rects=None) -> None:
        book_id = getattr(self._reading_view, "_book_id", "")
        if not book_id or not text:
            self._statusbar.showMessage("无法保存：请先打开书籍", 3000)
            return
        from notes.models import Note
        current_page = page if page >= 0 else self._reading_view.canvas.current_page
        note = Note(
            book_id=book_id,
            note_type="page_anchor",
            page=current_page,
            content=text,
            highlight_rects=pdf_rects or [],
            highlighted_text=self._claude_panel._pending_text if pdf_rects else "",
        )
        self._notes_panel._note_manager.add_note(note)
        self._notes_panel.refresh()
        self._right_tabs.setCurrentWidget(self._notes_panel)
        self._statusbar.showMessage(f"已保存到笔记 (P{current_page + 1})，正在生成标题...", 5000)
        # Sync highlights if rects were saved
        if pdf_rects:
            self._sync_note_highlights()
        # Trigger title generation
        model = self._claude_panel.current_model
        self._title_generator.set_model(model)
        self._title_generator.generate(note.id, text)

    def _on_title_generated(self, note_id: str, title: str) -> None:
        book_id = getattr(self._reading_view, "_book_id", "")
        if not book_id:
            return
        note = self._notes_panel._note_manager.get_note(book_id, note_id)
        if note:
            note.title = title
            self._notes_panel._note_manager.update_note(note)
            self._notes_panel.refresh()
            self._statusbar.showMessage(f"笔记标题已更新：{title}", 3000)

    def _sync_note_highlights(self, book_id: str = "") -> None:
        """Sync note highlight_rects to canvas as persistent highlights."""
        if not book_id:
            book_id = getattr(self._reading_view, "_book_id", "")
        if not book_id:
            self._reading_view.canvas.clear_note_highlights()
            return
        notes = self._notes_panel._note_manager.list_notes(book_id)
        highlights: dict[int, list[tuple[list[list[float]], str]]] = {}
        for n in notes:
            if n.highlight_rects and n.page >= 0:
                if n.page not in highlights:
                    highlights[n.page] = []
                highlights[n.page].append((n.highlight_rects, "#a6e3a1"))
        self._reading_view.canvas.set_note_highlights(highlights)

    def _on_optimize_title(self, note_id: str) -> None:
        """AI优化笔记标题"""
        book_id = getattr(self._reading_view, "_book_id", "")
        if not book_id:
            return
        note = self._notes_panel._note_manager.get_note(book_id, note_id)
        if not note:
            return
        model = self._claude_panel.current_model
        self._title_generator.set_model(model)
        self._title_generator.generate(note.id, note.content)
        self._statusbar.showMessage("正在AI优化标题...", 5000)

    def _on_note_highlight_menu(self, page: int, global_pos) -> None:
        """Right-click on a note highlight — show context menu."""
        book_id = getattr(self._reading_view, "_book_id", "")
        if not book_id:
            return
        notes = self._notes_panel._note_manager.list_notes(book_id)
        page_notes = [n for n in notes if n.page == page and n.highlight_rects]
        if not page_notes:
            return

        menu = QMenu(self)

        for note in page_notes:
            display = note.title or note.content[:30].replace("\n", " ")
            sub = menu.addMenu(f"📌 {display}")
            act_view = sub.addAction("阅览")
            act_view.setData(("preview", note.id))
            act_edit = sub.addAction("编辑")
            act_edit.setData(("edit", note.id))
            act_del = sub.addAction("删除")
            act_del.setData(("delete", note.id))

        action = menu.exec(global_pos)
        if action and action.data():
            cmd, note_id = action.data()
            if cmd == "preview":
                note = self._notes_panel._note_manager.get_note(book_id, note_id)
                if note:
                    self._notes_panel._show_note_preview(note)
            elif cmd == "edit":
                note = self._notes_panel._note_manager.get_note(book_id, note_id)
                if note:
                    self._right_tabs.setCurrentWidget(self._notes_panel)
                    self._notes_panel._show_editor(note.content, note.id, note.title)
            elif cmd == "delete":
                self._notes_panel._note_manager.delete_note(book_id, note_id)
                self._notes_panel.refresh()
                self._sync_note_highlights()
