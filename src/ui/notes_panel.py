"""笔记面板 — 显示/编辑/管理当前书籍的笔记"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.storage import Storage
from notes.models import Note
from notes.note_manager import NoteManager


class NotesPanel(QWidget):
    """右侧笔记面板：当前页笔记 / 本章笔记 / 全局笔记"""

    jump_to_page = pyqtSignal(int)
    optimize_requested = pyqtSignal(str, str)  # note_id, style
    extract_concepts_requested = pyqtSignal(str)  # book_id
    optimize_title_requested = pyqtSignal(str)  # note_id
    followup_requested = pyqtSignal(str, str)  # note_id, question
    html_explanation_requested = pyqtSignal(str)  # note_id (or selected content)

    def __init__(self, storage: Storage, parent=None) -> None:
        super().__init__(parent)
        self._note_manager = NoteManager(storage)
        self._book_id: str = ""
        self._current_page: int = 0
        self._current_chapter: str = ""
        self._editing_note_id: str = ""
        self._get_live_page = None  # callable to get actual current page
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setMinimumWidth(200)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Header
        header = QHBoxLayout()
        title = QLabel("📝 笔记")
        title.setObjectName("section_header")
        header.addWidget(title)
        header.addStretch()

        btn_add = QPushButton("+ 新建")
        btn_add.setFixedHeight(24)
        btn_add.setProperty("variant", "toolbar")
        btn_add.clicked.connect(self._on_add_note)
        header.addWidget(btn_add)

        layout.addLayout(header)

        # Note list
        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._list.itemClicked.connect(self._on_item_clicked)
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._on_context_menu)
        layout.addWidget(self._list)

        # Action bar below list
        action_bar = QHBoxLayout()
        action_bar.setContentsMargins(0, 0, 0, 0)
        btn_extract = QPushButton("🧠 提取概念")
        btn_extract.setFixedHeight(28)
        btn_extract.setProperty("variant", "toolbar")
        btn_extract.setToolTip("从当前书籍笔记中提取关键概念到知识图谱")
        btn_extract.clicked.connect(self._on_extract_concepts)
        action_bar.addWidget(btn_extract)
        action_bar.addStretch()
        layout.addLayout(action_bar)

        # Title input (hidden by default)
        self._title_input = QLineEdit()
        self._title_input.setPlaceholderText("笔记标题（可选）")
        self._title_input.hide()
        layout.addWidget(self._title_input)

        # Inline editor (hidden by default)
        self._editor = QTextEdit()
        self._editor.setMaximumHeight(100)
        self._editor.setPlaceholderText("输入笔记内容...")
        self._editor.hide()
        layout.addWidget(self._editor)

        # Editor buttons
        self._editor_btns = QHBoxLayout()
        self._editor_btns.setContentsMargins(0, 0, 0, 0)
        btn_save = QPushButton("保存")
        btn_save.setFixedHeight(26)
        btn_save.setProperty("variant", "primary")
        btn_save.clicked.connect(self._on_save_note)
        btn_cancel = QPushButton("取消")
        btn_cancel.setFixedHeight(26)
        btn_cancel.clicked.connect(self._on_cancel_edit)
        self._editor_btns.addStretch()
        self._editor_btns.addWidget(btn_save)
        self._editor_btns.addWidget(btn_cancel)
        self._editor_widget = QWidget()
        self._editor_widget.setFixedHeight(30)
        self._editor_widget.setLayout(self._editor_btns)
        self._editor_widget.hide()
        layout.addWidget(self._editor_widget)

    # ═══════════════════════════════
    # Public API
    # ═══════════════════════════════

    def set_book(self, book_id: str) -> None:
        self._book_id = book_id
        self._current_page = 0
        self._current_chapter = ""
        self._hide_editor()
        self.refresh()

    def set_live_page_getter(self, getter) -> None:
        """设置获取实时页码的回调函数"""
        self._get_live_page = getter

    def _actual_page(self) -> int:
        """获取当前实际页码"""
        if self._get_live_page:
            return self._get_live_page()
        return self._current_page

    def close_book(self) -> None:
        self._book_id = ""
        self._hide_editor()
        self._list.clear()

    def set_current_page(self, page: int, chapter: str = "") -> None:
        self._current_page = page
        if chapter:
            self._current_chapter = chapter
        self.refresh()

    def create_note_from_selection(self, text: str, page: int, pdf_rects: list | None = None) -> None:
        if not self._book_id:
            return
        note = Note(
            book_id=self._book_id,
            note_type="highlight",
            page=page,
            chapter=self._current_chapter,
            highlighted_text=text,
            highlight_rects=pdf_rects or [],
            content=text,
        )
        self._note_manager.add_note(note)
        self.refresh()

    def refresh(self) -> None:
        self._list.clear()
        if not self._book_id:
            item = QListWidgetItem("请先打开一本书")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            item.setForeground(Qt.GlobalColor.gray)
            self._list.addItem(item)
            return

        all_notes = self._note_manager.list_notes(self._book_id)
        if not all_notes:
            item = QListWidgetItem("暂无笔记，点击 + 新建 或选中文字创建")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            item.setForeground(Qt.GlobalColor.gray)
            self._list.addItem(item)
            return

        page_notes = [n for n in all_notes if n.page == self._current_page
                      and n.note_type in ("page_anchor", "highlight")]
        other_notes = [n for n in all_notes if n not in page_notes]

        if page_notes:
            self._add_section_header(f"当前页 (P{self._current_page + 1})")
            for n in page_notes:
                self._add_note_item(n)

        if other_notes:
            self._add_section_header("全部笔记")
            for n in sorted(other_notes, key=lambda x: x.page):
                self._add_note_item(n)

    # ═══════════════════════════════
    # Internal helpers
    # ═══════════════════════════════

    def _add_section_header(self, text: str) -> None:
        item = QListWidgetItem(text)
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        item.setForeground(Qt.GlobalColor.gray)
        self._list.addItem(item)

    def _add_note_item(self, note: Note) -> None:
        display = note.title if note.title else note.content[:35].replace("\n", " ")
        page_tag = f"P{note.page + 1}" if note.page >= 0 else ""
        if note.note_type == "highlight":
            label = f"🖍️ [{page_tag}] {display}"
        else:
            label = f"📌 [{page_tag}] {display}"
        if note.optimized_content:
            label += " ✨"
        item = QListWidgetItem(label)
        item.setData(Qt.ItemDataRole.UserRole, note.id)
        tooltip = f"点击跳转到 P{note.page + 1}\n双击编辑\n"
        if note.title:
            tooltip += f"\n标题：{note.title}"
        tooltip += f"\n\n{note.content[:200]}"
        item.setToolTip(tooltip)
        self._list.addItem(item)

    def _show_editor(self, content: str = "", note_id: str = "", title: str = "") -> None:
        self._editing_note_id = note_id
        self._title_input.setText(title)
        self._title_input.show()
        self._editor.setPlainText(content)
        self._editor.show()
        self._editor_widget.show()
        self._title_input.setFocus()

    def _hide_editor(self) -> None:
        self._editing_note_id = ""
        self._title_input.clear()
        self._title_input.hide()
        self._editor.clear()
        self._editor.hide()
        self._editor_widget.hide()

    # ═══════════════════════════════
    # Slots
    # ═══════════════════════════════

    def _on_add_note(self) -> None:
        self._show_editor()

    def _on_save_note(self) -> None:
        content = self._editor.toPlainText().strip()
        title = self._title_input.text().strip()
        if not content or not self._book_id:
            self._hide_editor()
            return
        if self._editing_note_id:
            note = self._note_manager.get_note(self._book_id, self._editing_note_id)
            if note:
                note.content = content
                note.title = title
                self._note_manager.update_note(note)
        else:
            note = Note(
                book_id=self._book_id,
                note_type="page_anchor",
                page=self._actual_page(),
                chapter=self._current_chapter,
                title=title,
                content=content,
            )
            self._note_manager.add_note(note)
        self._hide_editor()
        self.refresh()

    def _on_cancel_edit(self) -> None:
        self._hide_editor()

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        note_id = item.data(Qt.ItemDataRole.UserRole)
        if not note_id:
            return
        note = self._note_manager.get_note(self._book_id, note_id)
        if note:
            self._show_editor(note.content, note.id, note.title)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        note_id = item.data(Qt.ItemDataRole.UserRole)
        if not note_id:
            return
        note = self._note_manager.get_note(self._book_id, note_id)
        if note and note.page >= 0:
            self.jump_to_page.emit(note.page)

    def _on_context_menu(self, pos) -> None:
        item = self._list.itemAt(pos)
        if item is None:
            return
        note_id = item.data(Qt.ItemDataRole.UserRole)
        if not note_id:
            return

        menu = QMenu(self)
        act_preview = menu.addAction("阅览")
        act_followup = menu.addAction("追问")
        act_html = menu.addAction("🎬 生成交互讲解")
        menu.addSeparator()
        act_edit_title = menu.addAction("编辑标题")
        act_ai_title = menu.addAction("AI优化标题")
        act_edit = menu.addAction("编辑内容")
        act_optimize = menu.addMenu("优化内容")
        act_refine = act_optimize.addAction("精炼")
        act_restructure = act_optimize.addAction("结构化")
        act_expand = act_optimize.addAction("扩展")
        act_critique = act_optimize.addAction("批判性")
        menu.addSeparator()
        act_delete = menu.addAction("删除")

        action = menu.exec(self._list.mapToGlobal(pos))
        if action == act_preview:
            note = self._note_manager.get_note(self._book_id, note_id)
            if note:
                self._show_note_preview(note)
        elif action == act_followup:
            note = self._note_manager.get_note(self._book_id, note_id)
            if note:
                question, ok = QInputDialog.getText(
                    self, "追问笔记内容", "输入你的问题：",
                )
                if ok and question.strip():
                    self.followup_requested.emit(note_id, question.strip())
        elif action == act_html:
            self.html_explanation_requested.emit(note_id)
        elif action == act_edit_title:
            note = self._note_manager.get_note(self._book_id, note_id)
            if note:
                title, ok = QInputDialog.getText(
                    self, "编辑标题", "笔记标题：",
                    QLineEdit.EchoMode.Normal, note.title,
                )
                if ok:
                    note.title = title.strip()
                    self._note_manager.update_note(note)
                    self.refresh()
        elif action == act_ai_title:
            self.optimize_title_requested.emit(note_id)
        elif action == act_edit:
            note = self._note_manager.get_note(self._book_id, note_id)
            if note:
                self._show_editor(note.content, note.id, note.title)
        elif action == act_delete:
            self._note_manager.delete_note(self._book_id, note_id)
            self.refresh()
        elif action in (act_refine, act_restructure, act_expand, act_critique):
            style_map = {
                act_refine: "refine",
                act_restructure: "restructure",
                act_expand: "expand",
                act_critique: "critique",
            }
            self.optimize_requested.emit(note_id, style_map[action])

    def _on_extract_concepts(self) -> None:
        if self._book_id:
            self.extract_concepts_requested.emit(self._book_id)

    def _show_note_preview(self, note) -> None:
        """Show note content rendered as Markdown with math support."""
        import re

        content = note.content
        # Extract math blocks before markdown processing to protect underscores
        math_blocks = {}
        counter = [0]

        def _replace_math(m):
            key = f"\x00MATH{counter[0]}\x00"
            math_blocks[key] = m.group(0)
            counter[0] += 1
            return key

        # Protect $$...$$ (display) and $...$ (inline) from markdown
        content = re.sub(r'\$\$[\s\S]+?\$\$', _replace_math, content)
        content = re.sub(r'\$[^\n$]+?\$', _replace_math, content)

        try:
            import markdown2
            html_body = markdown2.markdown(
                content,
                extras=["fenced-code-blocks", "tables", "strike"],
            )
        except ImportError:
            import html as html_mod
            html_body = "<pre>" + html_mod.escape(content) + "</pre>"

        # Restore math blocks
        for key, val in math_blocks.items():
            html_body = html_body.replace(key, val)

        title_text = note.title or "笔记预览"
        page_info = f"P{note.page + 1}" if note.page >= 0 else ""

        html_content = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"></script>
<style>
body {{ font-family: 'Segoe UI', sans-serif; font-size: 14px;
       color: #cdd6f4; background: #1e1e2e; padding: 20px; }}
h1, h2, h3 {{ color: #89b4fa; }}
code {{ background: #313244; padding: 2px 5px; border-radius: 3px; font-family: monospace; }}
pre {{ background: #313244; padding: 12px; border-radius: 6px; overflow-x: auto; }}
pre code {{ background: none; padding: 0; }}
blockquote {{ border-left: 3px solid #cba6f7; padding-left: 12px; color: #a6adc8; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #45475a; padding: 6px 10px; }}
th {{ background: #313244; }}
a {{ color: #89b4fa; }}
.katex {{ font-size: 1.1em; }}
</style>
</head><body>
<h2>{title_text} <small style="color:#6c7086">{page_info}</small></h2>
<hr style="border-color:#313244">
{html_body}
<script>
document.addEventListener("DOMContentLoaded", function() {{
  renderMathInElement(document.body, {{
    delimiters: [
      {{left: "$$", right: "$$", display: true}},
      {{left: "$", right: "$", display: false}},
      {{left: "\\\\(", right: "\\\\)", display: false}},
      {{left: "\\\\[", right: "\\\\]", display: true}}
    ]
  }});
}});
</script>
</body></html>"""

        dlg = QDialog(self)
        dlg.setWindowTitle(f"笔记阅览 — {title_text}")
        dlg.resize(650, 500)
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(0, 0, 0, 0)

        try:
            from PyQt6.QtWebEngineWidgets import QWebEngineView
            browser = QWebEngineView()
            browser.setHtml(html_content)
        except ImportError:
            browser = QTextBrowser()
            browser.setOpenExternalLinks(True)
            browser.setStyleSheet("QTextBrowser { border: none; }")
            browser.setHtml(html_content)
        layout.addWidget(browser)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btn_box.rejected.connect(dlg.close)
        layout.addWidget(btn_box)

        dlg.exec()
