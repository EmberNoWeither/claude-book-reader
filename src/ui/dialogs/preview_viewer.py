"""全书总结查看器 — 只读展示已保存的全书预览"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

if TYPE_CHECKING:
    from core.book import Book


class PreviewViewerDialog(QDialog):
    """只读查看已保存的全书预览总结"""

    def __init__(self, book: Book, preview_text: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"全书总结 — {book.title}")
        self.setMinimumSize(700, 500)
        self.resize(800, 600)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        header = QLabel(f"《{book.title}》全书预览总结")
        header.setObjectName("section_header")
        layout.addWidget(header)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(False)
        browser.setMarkdown(preview_text)
        layout.addWidget(browser, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.close)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)
