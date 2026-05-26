"""全书预览总结对话框 — 流式输出 Claude 分析结果"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

if TYPE_CHECKING:
    from claude.claude_agent import ClaudeAgent
    from core.book import Book
    from core.storage import Storage


class BookPreviewDialog(QDialog):
    """全书预览总结 — 流式显示 Claude 分析"""

    finished = pyqtSignal(str)  # book_id

    def __init__(self, book: Book, storage: Storage, agent: ClaudeAgent, parent=None) -> None:
        super().__init__(parent)
        self._book = book
        self._storage = storage
        self._agent = agent
        self._result_text = ""
        self._error_occurred = False

        self.setWindowTitle(f"全书预览总结 — {book.title}")
        self.setMinimumSize(700, 500)
        self.resize(800, 600)
        self._setup_ui()
        self._start_analysis()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        self._status_label = QLabel("正在分析全书内容，请耐心等待...")
        self._status_label.setObjectName("section_header")
        layout.addWidget(self._status_label)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        layout.addWidget(self._progress)

        self._browser = QTextBrowser()
        self._browser.setOpenExternalLinks(False)
        layout.addWidget(self._browser, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._btn_close = QPushButton("关闭")
        self._btn_close.clicked.connect(self.close)
        btn_row.addWidget(self._btn_close)
        layout.addLayout(btn_row)

    def _start_analysis(self) -> None:
        self._agent.response_chunk.connect(self._on_chunk)
        self._agent.response_finished.connect(self._on_finished)
        self._agent.error_occurred.connect(self._on_error)
        self._send_preview_request()

    def _send_preview_request(self) -> None:
        import fitz
        try:
            doc = fitz.open(self._book.file_path)
        except Exception as e:
            self._on_error(f"无法打开 PDF: {e}")
            return

        toc = doc.get_toc()
        total_pages = doc.page_count

        # Extract text samples: first 2 pages of each chapter, or evenly spaced
        text_parts: list[str] = []
        if toc:
            for i, entry in enumerate(toc):
                level, title, page_num = entry[0], entry[1], entry[2] - 1
                if level > 2:
                    continue
                end_page = min(page_num + 2, total_pages)
                chapter_text = ""
                for p in range(page_num, end_page):
                    chapter_text += doc[p].get_text()
                text_parts.append(f"## 第{i+1}章: {title} (P{page_num+1})\n{chapter_text[:2000]}")
        else:
            # No TOC: sample every 10% of the book
            step = max(1, total_pages // 10)
            for p in range(0, total_pages, step):
                text = doc[p].get_text()
                text_parts.append(f"## Page {p+1}\n{text[:1500]}")

        doc.close()
        book_text = "\n\n".join(text_parts)
        # Limit total context
        if len(book_text) > 30000:
            book_text = book_text[:30000] + "\n\n[...内容已截断...]"

        toc_str = ""
        if toc:
            toc_str = "\n".join(f"{'  '*(e[0]-1)}{e[1]} (P{e[2]})" for e in toc[:50])

        prompt = (
            f"请对以下书籍进行全面的预览总结分析。\n\n"
            f"书名：{self._book.title}\n"
            f"作者：{self._book.author or '未知'}\n"
            f"总页数：{total_pages}\n\n"
            f"{'目录：' + chr(10) + toc_str + chr(10) + chr(10) if toc_str else ''}"
            f"以下是各章节的内容摘录：\n\n{book_text}\n\n"
            f"请按以下结构输出分析：\n"
            f"1. **全书概述**：用 3-5 句话概括本书的核心主题和价值\n"
            f"2. **各章节总结**：逐章说明叙述逻辑、涉及的关键知识点\n"
            f"3. **知识体系**：本书涉及的核心概念和它们之间的关系\n"
            f"4. **阅读建议**：推荐的阅读顺序、重点章节、预计阅读时间\n"
            f"5. **阅读目标**：读完本书后应该掌握的核心能力或知识\n\n"
            f"请用中文回答，内容尽可能详细丰富。"
        )

        from claude.context_builder import BookContext, ClaudeContext, InteractionContext
        ctx = ClaudeContext(
            action="book_preview",
            book=BookContext(
                title=self._book.title,
                author=self._book.author or "",
                total_pages=total_pages,
            ),
            context=InteractionContext(type="general"),
            user_query=prompt,
            history=[],
        )
        self._agent.send(ctx)

    def _on_chunk(self, text: str) -> None:
        self._result_text += text
        self._browser.setMarkdown(self._result_text)
        scrollbar = self._browser.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _on_finished(self, full_response: str) -> None:
        self._disconnect()
        self._result_text = full_response
        self._progress.setRange(0, 1)
        self._progress.setValue(1)
        self._status_label.setText("分析完成")
        self._save_result()
        self.finished.emit(self._book.id)

    def _on_error(self, err: str) -> None:
        self._disconnect()
        self._error_occurred = True
        self._progress.setRange(0, 1)
        self._progress.setValue(1)
        self._status_label.setText(f"分析出错: {err}")
        if self._result_text:
            self._status_label.setText("分析部分完成（有错误）")
            self._save_result()

    def _disconnect(self) -> None:
        try:
            self._agent.response_chunk.disconnect(self._on_chunk)
            self._agent.response_finished.disconnect(self._on_finished)
            self._agent.error_occurred.disconnect(self._on_error)
        except RuntimeError:
            pass

    def _save_result(self) -> None:
        if not self._result_text:
            return
        data = {
            "book_id": self._book.id,
            "title": self._book.title,
            "preview": self._result_text,
        }
        self._storage.write_book_json(self._book.id, "book_preview.json", data)

    def closeEvent(self, event) -> None:
        self._disconnect()
        super().closeEvent(event)


