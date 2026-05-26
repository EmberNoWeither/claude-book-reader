"""交互式 HTML 讲解生成与查看对话框"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

if TYPE_CHECKING:
    from claude.claude_agent import ClaudeAgent
    from core.book import Book
    from core.storage import Storage

HTML_PROMPT_TEMPLATE = """\
请根据以下内容生成一个交互式 HTML 讲解页面。

要求：
1. 使用纯 HTML + CSS + JavaScript（单文件，无外部依赖）
2. 包含动画演示、交互示例（如可点击的步骤、可展开的解释）
3. 视觉风格现代美观，深色主题，适合学习阅读
4. 对核心概念用动画或图示辅助理解
5. 如有代码相关内容，提供可运行的代码示例
6. 页面底部提供"关键要点"总结

待讲解的内容：
---
{content}
---

请直接输出完整的 HTML 代码，不要用 markdown 代码块包裹，不要输出任何其他文字。\
"""

HTML_EDIT_PROMPT_TEMPLATE = """\
以下是一个已有的交互式 HTML 讲解页面，请根据用户的要求对其进行修改和增强。

用户要求：{request}

现有 HTML 内容：
---
{existing_html}
---

请输出修改后的完整 HTML 代码，不要用 markdown 代码块包裹，不要输出任何其他文字。\
"""


class HtmlExplanationDialog(QDialog):
    """生成交互式 HTML 讲解 — 流式输出"""

    finished = pyqtSignal(str)  # html_id

    def __init__(self, book: Book, content: str, storage: Storage,
                 agent: ClaudeAgent, parent=None, edit_request: str = "",
                 existing_html: str = "", html_id: str = "") -> None:
        super().__init__(parent)
        self._book = book
        self._content = content
        self._storage = storage
        self._agent = agent
        self._result_text = ""
        self._edit_request = edit_request
        self._existing_html = existing_html
        self._html_id = html_id

        title = "编辑 HTML 讲解" if edit_request else "生成交互式 HTML 讲解"
        self.setWindowTitle(f"{title} — {book.title}")
        self.setMinimumSize(500, 300)
        self.resize(600, 350)
        self._setup_ui()
        self._start_generation()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        self._status_label = QLabel("正在生成交互式讲解，请耐心等待...")
        self._status_label.setObjectName("section_header")
        layout.addWidget(self._status_label)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        layout.addWidget(self._progress)

        self._preview_label = QLabel("")
        self._preview_label.setWordWrap(True)
        layout.addWidget(self._preview_label, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._btn_close = QPushButton("关闭")
        self._btn_close.clicked.connect(self.close)
        btn_row.addWidget(self._btn_close)
        layout.addLayout(btn_row)

    def _start_generation(self) -> None:
        self._agent.response_chunk.connect(self._on_chunk)
        self._agent.response_finished.connect(self._on_finished)
        self._agent.error_occurred.connect(self._on_error)

        if self._edit_request:
            prompt = HTML_EDIT_PROMPT_TEMPLATE.format(
                request=self._edit_request,
                existing_html=self._existing_html[:50000],
            )
        else:
            prompt = HTML_PROMPT_TEMPLATE.format(content=self._content[:20000])

        from claude.context_builder import BookContext, ClaudeContext, InteractionContext
        ctx = ClaudeContext(
            action="html_explanation",
            book=BookContext(
                title=self._book.title,
                author=self._book.author or "",
                total_pages=self._book.pages,
            ),
            context=InteractionContext(type="general"),
            user_query=prompt,
            history=[],
            no_tools=True,
        )
        self._agent.send(ctx)

    def _on_chunk(self, text: str) -> None:
        self._result_text += text
        char_count = len(self._result_text)
        self._preview_label.setText(f"已生成 {char_count} 字符...")

    def _on_finished(self, full_response: str) -> None:
        self._disconnect()
        self._result_text = self._clean_html(full_response)
        self._progress.setRange(0, 1)
        self._progress.setValue(1)
        self._status_label.setText("生成完成")
        self._save_result()
        self.finished.emit(self._html_id)

    def _on_error(self, err: str) -> None:
        self._disconnect()
        self._progress.setRange(0, 1)
        self._progress.setValue(1)
        self._status_label.setText(f"生成出错: {err}")
        if self._result_text:
            self._result_text = self._clean_html(self._result_text)
            self._save_result()

    def _disconnect(self) -> None:
        try:
            self._agent.response_chunk.disconnect(self._on_chunk)
        except (RuntimeError, TypeError):
            pass
        try:
            self._agent.response_finished.disconnect(self._on_finished)
        except (RuntimeError, TypeError):
            pass
        try:
            self._agent.error_occurred.disconnect(self._on_error)
        except (RuntimeError, TypeError):
            pass

    def _clean_html(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```html"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    def _save_result(self) -> None:
        if not self._result_text:
            return
        import time
        if not self._html_id:
            self._html_id = f"html_{int(time.time())}"

        html_dir = self._storage.book_dir(self._book.id) / "html_explanations"
        html_dir.mkdir(parents=True, exist_ok=True)

        html_path = html_dir / f"{self._html_id}.html"
        html_path.write_text(self._result_text, encoding="utf-8")

        meta_path = html_dir / "index.json"
        import json
        meta: list = []
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))

        existing = next((m for m in meta if m["id"] == self._html_id), None)
        if existing:
            existing["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        else:
            meta.append({
                "id": self._html_id,
                "title": self._content[:50].replace("\n", " "),
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            })
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    def closeEvent(self, event) -> None:
        self._disconnect()
        super().closeEvent(event)
