"""截图选区工具 — 透明覆盖层 + 橡皮筋框选 + 截图保存"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

from PyQt6.QtCore import QPoint, QRect, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QCursor, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QApplication, QRubberBand, QWidget


class ScreenshotTool(QWidget):
    """
    全屏透明覆盖层，用于截取屏幕区域。
    用法：
        tool = ScreenshotTool()
        tool.screenshot_taken.connect(handle_path)
        tool.show()
    """

    screenshot_taken = pyqtSignal(str)   # 截图文件路径
    cancelled = pyqtSignal()

    _TMP_DIR = Path(tempfile.gettempdir()) / "claude-book-reader" / "screenshots"

    def __init__(self, parent=None) -> None:
        super().__init__(parent, Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint)
        self._TMP_DIR.mkdir(parents=True, exist_ok=True)
        self._origin = QPoint()
        self._rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self)
        self._screen_pixmap: QPixmap | None = None

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        self.setWindowOpacity(0.35)

    def activate(self) -> None:
        """截取当前屏幕，进入选区模式"""
        screen = QApplication.primaryScreen()
        self._screen_pixmap = screen.grabWindow(0)
        self.setGeometry(screen.geometry())
        self.show()
        self.raise_()
        self.activateWindow()

    # ── Qt 事件 ───────────────────────────────────────

    def paintEvent(self, event) -> None:
        if self._screen_pixmap:
            painter = QPainter(self)
            painter.drawPixmap(0, 0, self._screen_pixmap)
            # 整体半透明遮罩
            painter.fillRect(self.rect(), QColor(0, 0, 0, 90))

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = event.pos()
            self._rubber_band.setGeometry(QRect(self._origin, self._origin))
            self._rubber_band.show()

    def mouseMoveEvent(self, event) -> None:
        if not self._origin.isNull():
            rect = QRect(self._origin, event.pos()).normalized()
            self._rubber_band.setGeometry(rect)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and not self._origin.isNull():
            rect = QRect(self._origin, event.pos()).normalized()
            self._rubber_band.hide()
            self.hide()
            if rect.width() > 5 and rect.height() > 5 and self._screen_pixmap:
                cropped = self._screen_pixmap.copy(rect)
                path = self._save(cropped)
                self.screenshot_taken.emit(str(path))
            else:
                self.cancelled.emit()
            self._origin = QPoint()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self._rubber_band.hide()
            self.hide()
            self._origin = QPoint()
            self.cancelled.emit()

    # ── 内部 ─────────────────────────────────────────

    def _save(self, pixmap: QPixmap) -> Path:
        path = self._TMP_DIR / f"shot-{int(time.time() * 1000)}.png"
        pixmap.save(str(path), "PNG")
        return path
