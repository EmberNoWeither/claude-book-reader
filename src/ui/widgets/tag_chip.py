"""标签芯片组件 — 小型彩色标签"""

from PyQt6.QtWidgets import QLabel


class TagChip(QLabel):
    """小型彩色圆角标签"""

    def __init__(self, text: str, color: str = "#3498db", parent=None) -> None:
        super().__init__(text, parent)
        self.setStyleSheet(
            f"""
            QLabel {{
                background: {color}22;
                color: {color};
                border: 1px solid {color}44;
                border-radius: 8px;
                padding: 1px 8px;
                font-size: 10px;
            }}
            """
        )
        self.setFixedHeight(20)
