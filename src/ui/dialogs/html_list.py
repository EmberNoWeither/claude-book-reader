"""HTML 讲解列表 — 浏览和打开已保存的交互式讲解"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

if TYPE_CHECKING:
    from core.storage import Storage


class HtmlListDialog(QDialog):
    """列出某本书的所有 HTML 讲解"""

    open_requested = pyqtSignal(str)  # html_id
    edit_requested = pyqtSignal(str, str)  # html_id, request
    delete_requested = pyqtSignal(str)  # html_id

    def __init__(self, book_id: str, storage: Storage, parent=None) -> None:
        super().__init__(parent)
        self._book_id = book_id
        self._storage = storage
        self.setWindowTitle("交互式 HTML 讲解列表")
        self.setMinimumSize(500, 400)
        self.resize(550, 450)
        self._setup_ui()
        self._load_list()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        header = QLabel("已保存的交互式讲解")
        header.setObjectName("section_header")
        layout.addWidget(header)

        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(self._on_open)
        layout.addWidget(self._list, stretch=1)

        btn_row = QHBoxLayout()
        btn_open = QPushButton("打开")
        btn_open.clicked.connect(self._on_open_selected)
        btn_row.addWidget(btn_open)
        btn_delete = QPushButton("删除")
        btn_delete.clicked.connect(self._on_delete)
        btn_row.addWidget(btn_delete)
        btn_row.addStretch()
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.close)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    def _load_list(self) -> None:
        self._list.clear()
        html_dir = self._storage.book_dir(self._book_id) / "html_explanations"
        meta_path = html_dir / "index.json"
        if not meta_path.exists():
            item = QListWidgetItem("暂无交互式讲解")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self._list.addItem(item)
            return

        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if not meta:
            item = QListWidgetItem("暂无交互式讲解")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self._list.addItem(item)
            return

        for entry in reversed(meta):
            label = f"{entry['title']}  [{entry.get('created_at', '')}]"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, entry["id"])
            self._list.addItem(item)

    def _on_open(self, item: QListWidgetItem = None) -> None:
        if item is None:
            return
        html_id = item.data(Qt.ItemDataRole.UserRole)
        if html_id:
            self.open_requested.emit(html_id)

    def _on_open_selected(self) -> None:
        item = self._list.currentItem()
        self._on_open(item)

    def _on_delete(self) -> None:
        item = self._list.currentItem()
        if not item:
            return
        html_id = item.data(Qt.ItemDataRole.UserRole)
        if not html_id:
            return
        r = QMessageBox.question(self, "确认删除", "确定要删除此讲解吗？")
        if r == QMessageBox.StandardButton.Yes:
            html_dir = self._storage.book_dir(self._book_id) / "html_explanations"
            html_file = html_dir / f"{html_id}.html"
            if html_file.exists():
                html_file.unlink()
            meta_path = html_dir / "index.json"
            if meta_path.exists():
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                meta = [m for m in meta if m["id"] != html_id]
                meta_path.write_text(
                    json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
                )
            self._load_list()

