"""HTML 讲解查看器 — 使用 QWebEngineView 展示交互式 HTML"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import QUrl, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QPushButton,
    QVBoxLayout,
)

if TYPE_CHECKING:
    pass


class HtmlViewerDialog(QDialog):
    """查看已保存的交互式 HTML 讲解"""

    edit_requested = pyqtSignal(str, str)  # html_id, edit_request

    def __init__(self, html_path: Path, html_id: str, title: str = "",
                 parent=None) -> None:
        super().__init__(parent)
        self._html_path = html_path
        self._html_id = html_id
        self.setWindowTitle(f"交互式讲解 — {title or html_id}")
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        try:
            from PyQt6.QtWebEngineWidgets import QWebEngineView
            self._browser = QWebEngineView()
            self._browser.setUrl(QUrl.fromLocalFile(str(self._html_path)))
        except ImportError:
            from PyQt6.QtWidgets import QTextBrowser
            self._browser = QTextBrowser()
            html_content = self._html_path.read_text(encoding="utf-8")
            self._browser.setHtml(html_content)
        layout.addWidget(self._browser, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(8, 4, 8, 4)
        self._btn_edit = QPushButton("再编辑")
        self._btn_edit.setToolTip("让 Claude 在此基础上增加或修改内容")
        self._btn_edit.clicked.connect(self._on_edit)
        btn_row.addWidget(self._btn_edit)
        btn_row.addStretch()
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.close)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    def _on_edit(self) -> None:
        request, ok = QInputDialog.getText(
            self, "再编辑 HTML 讲解",
            "请描述你希望增加或修改的内容：\n（如：增加动画演示、添加更多代码示例等）",
        )
        if ok and request.strip():
            self.edit_requested.emit(self._html_id, request.strip())
            self.close()
