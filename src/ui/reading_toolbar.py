"""Reading toolbar — mode switch, zoom, page navigation."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QWidget,
)

from ui.widgets.page_canvas import (
    MODE_DOUBLE_CONTINUOUS,
    MODE_DOUBLE_FLIP,
    MODE_SINGLE_CONTINUOUS,
    MODE_SINGLE_FLIP,
)


class ReadingToolbar(QWidget):
    """Top toolbar for reading controls."""

    mode_changed = pyqtSignal(str)
    zoom_in = pyqtSignal()
    zoom_out = pyqtSignal()
    fit_width = pyqtSignal()
    fit_page = pyqtSignal()
    zoom_original = pyqtSignal()
    go_to_page = pyqtSignal(int)
    add_bookmark = pyqtSignal()
    eye_protection_toggled = pyqtSignal(bool)
    brightness_changed = pyqtSignal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        # Mode buttons
        self._btn_single_cont = QPushButton("单页连续")
        self._btn_single_cont.setCheckable(True)
        self._btn_single_cont.setChecked(True)
        self._btn_single_cont.setToolTip("单页连续滚动 (Ctrl+1)")

        self._btn_double_cont = QPushButton("双页连续")
        self._btn_double_cont.setCheckable(True)
        self._btn_double_cont.setToolTip("双页连续滚动 (Ctrl+2)")

        self._btn_single_flip = QPushButton("单页翻页")
        self._btn_single_flip.setCheckable(True)
        self._btn_single_flip.setToolTip("单页翻页 (Ctrl+3)")

        self._btn_double_flip = QPushButton("双页翻页")
        self._btn_double_flip.setCheckable(True)
        self._btn_double_flip.setToolTip("双页翻页 (Ctrl+4)")

        for btn in [self._btn_single_cont, self._btn_double_cont, self._btn_single_flip, self._btn_double_flip]:
            btn.setProperty("variant", "mode")

        self._btn_single_cont.clicked.connect(lambda: self._on_mode(MODE_SINGLE_CONTINUOUS))
        self._btn_double_cont.clicked.connect(lambda: self._on_mode(MODE_DOUBLE_CONTINUOUS))
        self._btn_single_flip.clicked.connect(lambda: self._on_mode(MODE_SINGLE_FLIP))
        self._btn_double_flip.clicked.connect(lambda: self._on_mode(MODE_DOUBLE_FLIP))

        layout.addWidget(self._btn_single_cont)
        layout.addWidget(self._btn_double_cont)
        layout.addWidget(self._btn_single_flip)
        layout.addWidget(self._btn_double_flip)

        layout.addSpacing(12)

        # Zoom controls
        btn_zoom_out = QPushButton("−")
        btn_zoom_out.setFixedSize(28, 28)
        btn_zoom_out.clicked.connect(self.zoom_out.emit)
        layout.addWidget(btn_zoom_out)

        self._zoom_label = QLabel("100%")
        self._zoom_label.setFixedWidth(45)
        self._zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._zoom_label.setObjectName("zoom_label")
        layout.addWidget(self._zoom_label)

        btn_zoom_in = QPushButton("＋")
        btn_zoom_in.setFixedSize(28, 28)
        btn_zoom_in.clicked.connect(self.zoom_in.emit)
        layout.addWidget(btn_zoom_in)

        btn_fit_w = QPushButton("适应宽度")
        btn_fit_w.clicked.connect(self.fit_width.emit)
        layout.addWidget(btn_fit_w)

        btn_fit_p = QPushButton("适应页面")
        btn_fit_p.clicked.connect(self.fit_page.emit)
        layout.addWidget(btn_fit_p)

        btn_orig = QPushButton("100%")
        btn_orig.clicked.connect(self.zoom_original.emit)
        layout.addWidget(btn_orig)

        for btn in [btn_zoom_out, btn_zoom_in, btn_fit_w, btn_fit_p, btn_orig]:
            btn.setProperty("variant", "toolbar")

        layout.addStretch()

        # Page navigation
        btn_prev = QPushButton("◀")
        btn_prev.setFixedSize(32, 28)
        btn_prev.clicked.connect(self._on_prev)
        layout.addWidget(btn_prev)

        self._page_spin = QSpinBox()
        self._page_spin.setFixedWidth(60)
        self._page_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._page_spin.valueChanged.connect(self._on_page_spin)
        layout.addWidget(self._page_spin)

        self._total_label = QLabel("/ 0")
        self._total_label.setObjectName("total_label")
        layout.addWidget(self._total_label)

        btn_next = QPushButton("▶")
        btn_next.setFixedSize(32, 28)
        btn_next.clicked.connect(self._on_next)
        layout.addWidget(btn_next)

        for btn in [btn_prev, btn_next]:
            btn.setProperty("variant", "toolbar")

        layout.addSpacing(8)

        # Bookmark button
        btn_bm = QPushButton("🔖 添加书签")
        btn_bm.clicked.connect(self.add_bookmark.emit)
        btn_bm.setProperty("variant", "toolbar")
        layout.addWidget(btn_bm)

        layout.addSpacing(12)

        # Eye protection controls
        self._btn_eye = QPushButton("🌙 护眼")
        self._btn_eye.setCheckable(True)
        self._btn_eye.setProperty("variant", "mode")
        self._btn_eye.setToolTip("护眼模式：叠加暖色滤镜")
        self._btn_eye.toggled.connect(self.eye_protection_toggled.emit)
        layout.addWidget(self._btn_eye)

        bright_label = QLabel("亮度")
        bright_label.setObjectName("total_label")
        layout.addWidget(bright_label)
        self._brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self._brightness_slider.setRange(50, 150)
        self._brightness_slider.setValue(100)
        self._brightness_slider.setFixedWidth(80)
        self._brightness_slider.setToolTip("调节 PDF 亮度 (50%-150%)")
        self._brightness_slider.valueChanged.connect(self.brightness_changed.emit)
        layout.addWidget(self._brightness_slider)

    def _on_mode(self, mode: str) -> None:
        self._btn_single_cont.setChecked(mode == MODE_SINGLE_CONTINUOUS)
        self._btn_double_cont.setChecked(mode == MODE_DOUBLE_CONTINUOUS)
        self._btn_single_flip.setChecked(mode == MODE_SINGLE_FLIP)
        self._btn_double_flip.setChecked(mode == MODE_DOUBLE_FLIP)
        self.mode_changed.emit(mode)

    def _on_prev(self) -> None:
        self.go_to_page.emit(self._page_spin.value() - 1)

    def _on_next(self) -> None:
        self.go_to_page.emit(self._page_spin.value() + 1)

    def _on_page_spin(self, page: int) -> None:
        self.go_to_page.emit(page - 1)  # convert 1-based → 0-based

    def set_zoom(self, zoom: float) -> None:
        self._zoom_label.setText(f"{zoom * 100:.0f}%")

    def set_page(self, page: int, total: int) -> None:
        self._page_spin.blockSignals(True)
        self._page_spin.setRange(1, total)
        self._page_spin.setValue(page + 1)  # 0-based → 1-based
        self._page_spin.blockSignals(False)
        self._total_label.setText(f"/ {total}")

    def set_mode_buttons(self, mode: str) -> None:
        self._btn_single_cont.setChecked(mode == MODE_SINGLE_CONTINUOUS)
        self._btn_double_cont.setChecked(mode == MODE_DOUBLE_CONTINUOUS)
        self._btn_single_flip.setChecked(mode == MODE_SINGLE_FLIP)
        self._btn_double_flip.setChecked(mode == MODE_DOUBLE_FLIP)
