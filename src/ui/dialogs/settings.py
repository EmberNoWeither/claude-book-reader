"""设置对话框 — 外观 / 阅读 / Claude 配置"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
)

if TYPE_CHECKING:
    from core.config import Config
    from ui.themes.theme_manager import ThemeManager


class SettingsDialog(QDialog):
    """应用设置对话框"""

    def __init__(self, config: Config, theme_manager: ThemeManager | None = None, parent=None) -> None:
        super().__init__(parent)
        self._config = config
        self._theme_manager = theme_manager
        self._pending_theme: str = config.get("app", "theme", default="dark") or "dark"
        self.setWindowTitle("设置")
        self.setMinimumSize(440, 380)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # ── 外观 ──
        appearance = QGroupBox("外观")
        app_layout = QVBoxLayout(appearance)

        theme_row = QHBoxLayout()
        theme_row.addWidget(QLabel("主题"))
        self._radio_dark = QRadioButton("暗色")
        self._radio_light = QRadioButton("亮色")
        self._radio_warm = QRadioButton("暖色")

        current = self._pending_theme
        if current == "light":
            self._radio_light.setChecked(True)
        elif current == "warm":
            self._radio_warm.setChecked(True)
        else:
            self._radio_dark.setChecked(True)

        self._radio_dark.toggled.connect(lambda c: c and self._on_theme("dark"))
        self._radio_light.toggled.connect(lambda c: c and self._on_theme("light"))
        self._radio_warm.toggled.connect(lambda c: c and self._on_theme("warm"))

        theme_row.addWidget(self._radio_dark)
        theme_row.addWidget(self._radio_light)
        theme_row.addWidget(self._radio_warm)
        theme_row.addStretch()
        app_layout.addLayout(theme_row)
        layout.addWidget(appearance)

        # ── 阅读 ──
        reading = QGroupBox("阅读")
        read_layout = QVBoxLayout(reading)

        idle_row = QHBoxLayout()
        idle_row.addWidget(QLabel("闲置自动结束会话"))
        self._idle_spin = QSpinBox()
        self._idle_spin.setRange(1, 60)
        self._idle_spin.setSuffix(" 分钟")
        self._idle_spin.setValue(self._config.get("reading", "idle_timeout_minutes", default=5))
        idle_row.addWidget(self._idle_spin)
        idle_row.addStretch()
        read_layout.addLayout(idle_row)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("默认阅读模式"))
        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["单页连续", "双页连续", "单页翻页", "双页翻页"])
        mode_map = {"single_continuous": 0, "double_continuous": 1, "single_flip": 2, "double_flip": 3}
        current_mode = self._config.get("app", "default_reading_mode", default="single_continuous")
        self._mode_combo.setCurrentIndex(mode_map.get(current_mode, 0))
        mode_row.addWidget(self._mode_combo)
        mode_row.addStretch()
        read_layout.addLayout(mode_row)

        layout.addWidget(reading)

        # ── Claude ──
        claude = QGroupBox("Claude")
        claude_layout = QVBoxLayout(claude)

        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("默认模型"))
        self._model_combo = QComboBox()
        models = self._config.get("claude", "available_models", default=[])
        self._model_combo.addItem("默认", "")
        for m in models:
            self._model_combo.addItem(m, m)
        current_model = self._config.get("claude", "model", default="")
        idx = self._model_combo.findData(current_model)
        if idx >= 0:
            self._model_combo.setCurrentIndex(idx)
        model_row.addWidget(self._model_combo)
        model_row.addStretch()
        claude_layout.addLayout(model_row)

        layout.addWidget(claude)

        # ── Buttons ──
        layout.addStretch()
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_theme(self, name: str) -> None:
        self._pending_theme = name
        if self._theme_manager:
            self._theme_manager.apply(name)

    def _on_accept(self) -> None:
        self._config.set("app", "theme", value=self._pending_theme)
        self._config.set("reading", "idle_timeout_minutes", value=self._idle_spin.value())
        mode_keys = ["single_continuous", "double_continuous", "single_flip", "double_flip"]
        self._config.set("app", "default_reading_mode", value=mode_keys[self._mode_combo.currentIndex()])
        self._config.set("claude", "model", value=self._model_combo.currentData())
        self._config.save()
        self.accept()

