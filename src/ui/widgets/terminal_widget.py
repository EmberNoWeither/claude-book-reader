"""终端聊天组件 — 显示对话历史，支持 Markdown 渲染"""

from __future__ import annotations

import html
import time

try:
    import markdown2
    _HAS_MARKDOWN2 = True
except ImportError:
    _HAS_MARKDOWN2 = False

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


def _md_to_html(text: str) -> str:
    if _HAS_MARKDOWN2:
        return markdown2.markdown(text, extras=["fenced-code-blocks", "tables", "strike"])
    return "<pre>" + html.escape(text) + "</pre>"


_BUBBLE_CSS = """
<style>
body { font-family: 'Segoe UI', sans-serif; font-size: 13px; margin: 0; padding: 0; }
.msg-user { background: #313244; border-radius: 8px; padding: 8px 12px; margin: 6px 0; }
.msg-user .role { color: #89b4fa; font-weight: bold; font-size: 11px; margin-bottom: 4px; }
.msg-assistant { background: #1e1e2e; border-left: 3px solid #cba6f7; padding: 8px 12px; margin: 6px 0; }
.msg-assistant .role { color: #cba6f7; font-weight: bold; font-size: 11px; margin-bottom: 4px; }
.msg-error { background: #3b1f1f; border-left: 3px solid #f38ba8; padding: 8px 12px; margin: 6px 0; }
.msg-error .role { color: #f38ba8; font-weight: bold; font-size: 11px; }
.msg-thinking { color: #6c7086; font-style: italic; padding: 4px 12px; }
code { background: #313244; padding: 1px 4px; border-radius: 3px; font-family: monospace; }
pre { background: #313244; padding: 8px; border-radius: 6px; overflow-x: auto; }
pre code { background: none; padding: 0; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #45475a; padding: 4px 8px; }
th { background: #313244; }
</style>
"""


class TerminalWidget(QWidget):
    """聊天终端：显示对话气泡 + 输入框"""

    message_submitted = pyqtSignal(str)   # 用户提交消息
    save_to_notes = pyqtSignal(str)       # 保存最后一条 AI 回复到笔记

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._last_assistant_text = ""
        self._messages: list[dict] = []   # {"role": user|assistant|error|thinking, "text": str, "ts": str}
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # 对话显示区
        self._browser = QTextBrowser()
        self._browser.setOpenExternalLinks(True)
        self._browser.setStyleSheet(
            "QTextBrowser { background: #1e1e2e; color: #cdd6f4; border: none; }"
        )
        self._browser.document().setDefaultStyleSheet(_BUBBLE_CSS)
        layout.addWidget(self._browser, stretch=1)

        # 输入区
        input_row = QWidget()
        input_layout = QHBoxLayout(input_row)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(4)

        self._input = QTextEdit()
        self._input.setPlaceholderText("输入问题，Ctrl+Enter 发送…")
        self._input.setMaximumHeight(80)
        self._input.setStyleSheet(
            "QTextEdit { background: #313244; color: #cdd6f4; border: 1px solid #45475a;"
            " border-radius: 6px; padding: 6px; }"
        )
        self._input.installEventFilter(self)
        input_layout.addWidget(self._input, stretch=1)

        btn_col = QVBoxLayout()
        btn_col.setSpacing(4)
        self._btn_send = QPushButton("发送")
        self._btn_send.setFixedWidth(60)
        self._btn_send.setStyleSheet(
            "QPushButton { background: #89b4fa; color: #1e1e2e; border-radius: 4px; padding: 4px; font-weight: bold; }"
            "QPushButton:hover { background: #b4d0ff; }"
            "QPushButton:disabled { background: #45475a; color: #6c7086; }"
        )
        self._btn_send.clicked.connect(self._submit)
        btn_col.addWidget(self._btn_send)

        self._btn_save = QPushButton("存笔记")
        self._btn_save.setFixedWidth(60)
        self._btn_save.setStyleSheet(
            "QPushButton { background: #a6e3a1; color: #1e1e2e; border-radius: 4px; padding: 4px; }"
            "QPushButton:hover { background: #c0f0bb; }"
            "QPushButton:disabled { background: #45475a; color: #6c7086; }"
        )
        self._btn_save.setEnabled(False)
        self._btn_save.clicked.connect(self._on_save)
        btn_col.addWidget(self._btn_save)
        input_layout.addLayout(btn_col)

        layout.addWidget(input_row)

    # ── 公共 API ──────────────────────────────────────

    def append_user(self, text: str) -> None:
        self._messages.append({"role": "user", "text": text, "ts": time.strftime("%H:%M")})
        self._redraw()

    def begin_assistant_stream(self) -> None:
        """添加"正在思考"占位消息"""
        self._last_assistant_text = ""
        self._messages.append({"role": "thinking", "text": "", "ts": time.strftime("%H:%M")})
        self._redraw()

    def append_assistant_chunk(self, chunk: str) -> None:
        """追加流式片段到占位消息"""
        self._last_assistant_text += chunk

    def finish_assistant_stream(self, full_text: str) -> None:
        """将占位消息替换为完整 Markdown 渲染结果"""
        self._last_assistant_text = full_text
        # 找到最后一条 thinking 消息，替换掉
        for i in range(len(self._messages) - 1, -1, -1):
            if self._messages[i]["role"] == "thinking":
                if full_text:
                    self._messages[i] = {"role": "assistant", "text": full_text, "ts": self._messages[i]["ts"]}
                else:
                    self._messages.pop(i)
                break
        self._redraw()
        self._btn_save.setEnabled(bool(full_text))

    def append_error(self, err: str) -> None:
        self._messages.append({"role": "error", "text": err, "ts": time.strftime("%H:%M")})
        self._redraw()

    def set_busy(self, busy: bool) -> None:
        self._btn_send.setEnabled(not busy)
        self._input.setReadOnly(busy)

    def clear(self) -> None:
        self._messages.clear()
        self._last_assistant_text = ""
        self._browser.clear()
        self._btn_save.setEnabled(False)

    def focus_input(self) -> None:
        self._input.setFocus()

    # ── 内部 ─────────────────────────────────────────

    def _redraw(self) -> None:
        """重绘整个对话区域"""
        parts = [_BUBBLE_CSS, "<body>"]
        for msg in self._messages:
            role = msg["role"]
            ts = msg.get("ts", "")
            text = msg["text"]
            if role == "user":
                escaped = html.escape(text).replace("\n", "<br>")
                parts.append(f'<div class="msg-user"><div class="role">你 · {ts}</div>{escaped}</div>')
            elif role == "assistant":
                rendered = _md_to_html(text)
                parts.append(f'<div class="msg-assistant"><div class="role">Claude · {ts}</div>{rendered}</div>')
            elif role == "thinking":
                parts.append('<div class="msg-thinking">Claude 正在思考…</div>')
            elif role == "error":
                escaped = html.escape(text)
                parts.append(f'<div class="msg-error"><div class="role">错误</div>{escaped}</div>')
        parts.append("</body>")
        self._browser.setHtml("".join(parts))
        self._scroll_to_bottom()

    def _append_html(self, html_str: str) -> None:
        self._browser.append(html_str)
        self._scroll_to_bottom()

    def _scroll_to_bottom(self) -> None:
        sb = self._browser.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _submit(self) -> None:
        text = self._input.toPlainText().strip()
        if not text:
            return
        self._input.clear()
        self.message_submitted.emit(text)

    def _on_save(self) -> None:
        if self._last_assistant_text:
            self.save_to_notes.emit(self._last_assistant_text)

    def eventFilter(self, obj, event) -> bool:
        from PyQt6.QtCore import QEvent
        from PyQt6.QtGui import QKeyEvent
        if obj is self._input and event.type() == QEvent.Type.KeyPress:
            ke: QKeyEvent = event
            if (ke.key() == Qt.Key.Key_Return
                    and ke.modifiers() & Qt.KeyboardModifier.ControlModifier):
                self._submit()
                return True
        return super().eventFilter(obj, event)
