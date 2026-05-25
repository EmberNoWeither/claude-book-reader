"""新建分类对话框"""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QComboBox,
)

from core.library import Library


class AddCategoryDialog(QDialog):
    def __init__(self, library: Library, parent_id: str = "", parent=None) -> None:
        super().__init__(parent)
        self._library = library
        self._parent_id = parent_id
        self.setWindowTitle("新建分类")
        self.setMinimumWidth(350)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # 父分类
        layout.addWidget(QLabel("父分类:"))
        self._parent_combo = QComboBox()
        self._parent_combo.addItem("(无 — 顶级分类)", "")
        for c, depth in self._library.get_category_flat():
            prefix = "  " * depth
            self._parent_combo.addItem(f"{prefix}{c.name}", c.id)
        if self._parent_id:
            idx = self._parent_combo.findData(self._parent_id)
            if idx >= 0:
                self._parent_combo.setCurrentIndex(idx)
        layout.addWidget(self._parent_combo)

        # 名称
        layout.addWidget(QLabel("分类名称:"))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("例如: 机器学习")
        layout.addWidget(self._name_edit)

        # 描述
        layout.addWidget(QLabel("描述 (可选):"))
        self._desc_edit = QTextEdit()
        self._desc_edit.setMaximumHeight(80)
        layout.addWidget(self._desc_edit)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("保存")
        btn_save.clicked.connect(self._save)
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def _save(self) -> None:
        name = self._name_edit.text().strip()
        if not name:
            return
        parent_id = self._parent_combo.currentData()
        self._library.add_category(name, parent_id)
        self.accept()
