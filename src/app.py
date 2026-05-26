"""QApplication 初始化、全局样式、主窗口创建"""

from __future__ import annotations

import sys

# QtWebEngineWidgets must be imported before QApplication is created
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView as _  # noqa: F401
except ImportError:
    pass

from PyQt6.QtWidgets import QApplication, QMessageBox

from core.config import Config
from core.library import Library
from ui.main_window import MainWindow
from ui.themes import ThemeManager
from utils.logger import get_logger, init_logging


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

        # 日志（依赖 data_dir 已就绪）
        init_logging()
        self._log = get_logger(__name__)
        self._install_excepthook()
        self._log.info("Application starting")

        # 图书库
        self._library = Library()

        # 主题系统
        self._theme_manager = ThemeManager(self._qapp, self._config)

        # 主窗口
        self._main_window = MainWindow(
            self._library, self._config, self._library.storage, self._theme_manager
        )
        self._main_window.show()


    def _install_excepthook(self) -> None:
        """全局异常钩子：未捕获异常写日志 + 弹窗提示，避免静默崩溃"""
        def hook(exc_type, exc_value, exc_tb):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_tb)
                return
            self._log.exception(
                "Unhandled exception", exc_info=(exc_type, exc_value, exc_tb)
            )
            try:
                QMessageBox.critical(
                    None,
                    "意外错误",
                    f"{exc_type.__name__}: {exc_value}\n\n详情已写入日志文件。",
                )
            except Exception:
                pass

        sys.excepthook = hook

    def run(self) -> int:
        return self._qapp.exec()
