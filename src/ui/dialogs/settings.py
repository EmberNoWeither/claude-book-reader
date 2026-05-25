"""设置对话框 — 占位，Phase 5 完善"""

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel


class SettingsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setMinimumSize(400, 300)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("设置面板 — 将在 Phase 5 实现"))
