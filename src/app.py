"""QApplication 初始化、全局样式、主窗口创建"""

from __future__ import annotations

import sys
from pathlib import Path

# QtWebEngineWidgets must be imported before QApplication is created
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView as _  # noqa: F401
except ImportError:
    pass

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtWidgets import QApplication

from core.config import Config
from core.library import Library
from ui.main_window import MainWindow

DARK_STYLESHEET = """
QMainWindow {
    background: #1a1a2e;
}
QWidget {
    background: #1a1a2e;
    color: #cdd6f4;
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
    font-size: 13px;
}
QMenuBar {
    background: #11111b;
    color: #cdd6f4;
    border-bottom: 1px solid #313244;
    padding: 2px;
}
QMenuBar::item:selected {
    background: #313244;
    border-radius: 4px;
}
QMenu {
    background: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 6px;
    padding: 4px;
}
QMenu::item:selected {
    background: #45475a;
    border-radius: 4px;
}
QTreeWidget, QListWidget {
    background: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 6px;
    outline: none;
    alternate-background-color: #1a1a2e;
}
QTreeWidget::item:selected, QListWidget::item:selected {
    background: #45475a;
}
QTreeWidget::item:hover, QListWidget::item:hover {
    background: #313244;
}
QLineEdit {
    background: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: #89b4fa;
}
QLineEdit:focus {
    border-color: #89b4fa;
}
QPushButton {
    background: #45475a;
    color: #cdd6f4;
    border: none;
    border-radius: 6px;
    padding: 6px 16px;
    font-weight: bold;
}
QPushButton:hover {
    background: #585b70;
}
QPushButton:pressed {
    background: #313244;
}
QSplitter::handle {
    background: #313244;
    width: 2px;
}
QScrollBar:vertical {
    background: #1e1e2e;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #45475a;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #585b70;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QStatusBar {
    background: #11111b;
    color: #6c7086;
    border-top: 1px solid #313244;
}
QLabel {
    background: transparent;
}
QComboBox {
    background: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 4px 8px;
}
QComboBox::drop-down {
    border: none;
}
QComboBox QAbstractItemView {
    background: #1e1e2e;
    color: #cdd6f4;
    selection-background-color: #45475a;
}
QSpinBox {
    background: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 4px 8px;
}
QTextEdit {
    background: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
}
QGraphicsView {
    background: #1e1e2e;
    border: none;
}
"""


class App:
    """应用程序主类"""

    def __init__(self) -> None:
        self._qapp = QApplication(sys.argv)
        self._qapp.setApplicationName("Claude Book Reader")
        self._qapp.setOrganizationName("ClaudeBookReader")

        # 配置
        self._config = Config()
        self._config.load()

        # 数据目录
        self._config.data_dir.mkdir(parents=True, exist_ok=True)

        # 图书库
        self._library = Library()

        # 全局样式
        self._apply_theme()

        # 主窗口
        self._main_window = MainWindow(self._library, self._config, self._library.storage)
        self._main_window.show()

    def _apply_theme(self) -> None:
        theme = self._config.get("app", "theme", default="dark")
        if theme == "dark":
            self._qapp.setStyleSheet(DARK_STYLESHEET)

    def run(self) -> int:
        return self._qapp.exec()
