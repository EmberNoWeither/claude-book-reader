"""新建标签对话框"""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
)

from core.library import Library


TAG_COLORS = [
    "#e74c3c", "#e67e22", "#f1c40f", "#2ecc71",
    "#3498db", "#9b59b6", "#1abc9c", "#e91e63",
]


class AddTagDialog(QDialog):
    def __init__(self, library: Library, parent=None) -> None:
        super().__init__(parent)
        self._library = library
        self._selected_color = TAG_COLORS[0]
        self.setWindowTitle("新建标签")
        self.setMinimumWidth(300)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("标签名称:"))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("例如: 重点阅读")
        layout.addWidget(self._name_edit)

        layout.addWidget(QLabel("颜色:"))
        color_layout = QHBoxLayout()
        for c in TAG_COLORS:
            btn = QPushButton()
            btn.setFixedSize(28, 28)
            btn.setStyleSheet(
                f"QPushButton {{ background: {c}; border-radius: 14px; "
                f"border: 2px solid {'white' if c == self._selected_color else 'transparent'}; }}"
            )
            btn.clicked.connect(lambda checked, col=c: self._select_color(col))
            color_layout.addWidget(btn)
        color_layout.addStretch()
        layout.addLayout(color_layout)

        btn_layout = QHBoxLayout()
        btn_save = QPushButton("保存")
        btn_save.clicked.connect(self._save)
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def _select_color(self, color: str) -> None:
        self._selected_color = color

    def _save(self) -> None:
        name = self._name_edit.text().strip()
        if not name:
            return
        self._library.add_tag(name, self._selected_color)
        self.accept()
