"""主题管理器 — 加载 QSS + 提供 Palette + 通知订阅者"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication

from .palette import DARK, PALETTES, Palette

if TYPE_CHECKING:
    from core.config import Config

_THEMES_DIR = Path(__file__).parent


class ThemeManager(QObject):
    theme_changed = pyqtSignal(str)

    def __init__(self, app: QApplication, config: Config, parent=None) -> None:
        super().__init__(parent)
        self._app = app
        self._config = config
        self._current_name: str = config.get("app", "theme", default="dark") or "dark"
        self._palette: Palette = PALETTES.get(self._current_name, DARK)
        self._env = Environment(
            loader=FileSystemLoader(str(_THEMES_DIR)),
            autoescape=False,
        )
        self.apply(self._current_name)

    def current(self) -> str:
        return self._current_name

    def palette(self) -> Palette:
        return self._palette

    def apply(self, name: str) -> None:
        if name not in PALETTES:
            name = "dark"
        self._current_name = name
        self._palette = PALETTES[name]
        qss = self._render_qss(name)
        self._app.setStyleSheet(qss)
        self.theme_changed.emit(name)

    def _render_qss(self, name: str) -> str:
        template_file = f"{name}.qss"
        try:
            tmpl = self._env.get_template(template_file)
        except Exception:
            tmpl = self._env.get_template("dark.qss")
        from dataclasses import asdict
        return tmpl.render(**asdict(self._palette))
