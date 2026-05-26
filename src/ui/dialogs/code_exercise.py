"""代码练习生成对话框 — Claude 生成代码文件到本地目录"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
)

if TYPE_CHECKING:
    from claude.claude_agent import ClaudeAgent
    from core.book import Book
    from core.config import Config

CODE_EXERCISE_PROMPT = """\
请根据以下书籍内容，生成代码练习题和示例代码。

书名：{title}
作者：{author}

相关内容：
---
{content}
---

练习类型：{exercise_type}

要求：
1. 生成完整可运行的代码文件
2. 包含详细的中文注释说明
3. 练习题要有明确的题目描述和预期输出
4. 示例代码要有逐步讲解
5. 如果是练习题，提供参考答案（放在单独的文件中）

请按以下格式输出（每个文件用 === 分隔）：
=== filename: 文件名.扩展名 ===
文件内容
=== end ===

可以输出多个文件。请直接输出，不要用 markdown 代码块包裹整体。\
"""

EXERCISE_TYPES = [
    ("practice", "练习题（含参考答案）"),
    ("example", "代码讲解示例"),
    ("project", "小项目实战"),
    ("quiz", "概念测验 + 代码验证"),
]


class CodeExerciseDialog(QDialog):
    """代码练习生成对话框"""

    finished = pyqtSignal(str)  # output directory path

    def __init__(self, book: Book, config: Config, agent: ClaudeAgent,
                 parent=None) -> None:
        super().__init__(parent)
        self._book = book
        self._config = config
        self._agent = agent
        self._result_text = ""
        self._output_dir: Path | None = None

        self.setWindowTitle(f"生成代码练习 — {book.title}")
        self.setMinimumSize(600, 500)
        self.resize(700, 550)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Output directory
        dir_row = QHBoxLayout()
        dir_row.addWidget(QLabel("输出目录："))
        self._dir_input = QLineEdit()
        self._dir_input.setReadOnly(True)
        saved_dir = self._config.get("code_exercises", "output_dir") or ""
        if saved_dir:
            self._dir_input.setText(saved_dir)
        dir_row.addWidget(self._dir_input, stretch=1)
        btn_browse = QPushButton("浏览...")
        btn_browse.clicked.connect(self._on_browse_dir)
        dir_row.addWidget(btn_browse)
        layout.addLayout(dir_row)

        # Exercise type
        type_row = QHBoxLayout()
        type_row.addWidget(QLabel("练习类型："))
        self._type_combo = QComboBox()
        for key, label in EXERCISE_TYPES:
            self._type_combo.addItem(label, key)
        type_row.addWidget(self._type_combo, stretch=1)
        layout.addLayout(type_row)

        # Content input
        layout.addWidget(QLabel("相关内容（选中的文本、笔记或章节描述）："))
        self._content_input = QTextEdit()
        self._content_input.setMaximumHeight(120)
        self._content_input.setPlaceholderText("粘贴或输入与练习相关的书籍内容...")
        layout.addWidget(self._content_input)

        # Progress area
        self._status_label = QLabel("")
        self._status_label.setObjectName("section_header")
        layout.addWidget(self._status_label)

        self._progress = QProgressBar()
        self._progress.setRange(0, 1)
        self._progress.setValue(0)
        self._progress.hide()
        layout.addWidget(self._progress)

        # Result display
        self._browser = QTextBrowser()
        self._browser.hide()
        layout.addWidget(self._browser, stretch=1)

        # Buttons
        btn_row = QHBoxLayout()
        self._btn_generate = QPushButton("生成")
        self._btn_generate.clicked.connect(self._on_generate)
        btn_row.addWidget(self._btn_generate)
        btn_row.addStretch()
        self._btn_open_dir = QPushButton("打开输出目录")
        self._btn_open_dir.clicked.connect(self._on_open_dir)
        self._btn_open_dir.hide()
        btn_row.addWidget(self._btn_open_dir)
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.close)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    def _on_browse_dir(self) -> None:
        current = self._dir_input.text() or str(Path.home())
        d = QFileDialog.getExistingDirectory(self, "选择代码练习输出目录", current)
        if d:
            self._dir_input.setText(d)
            self._config.set("code_exercises", "output_dir", value=d)
            self._config.save()

    def _on_generate(self) -> None:
        output_base = self._dir_input.text()
        if not output_base:
            QMessageBox.warning(self, "提示", "请先选择输出目录")
            return
        content = self._content_input.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "提示", "请输入相关内容")
            return
        if self._agent.is_busy:
            QMessageBox.information(self, "提示", "Claude 正在处理其他任务，请稍后再试")
            return

        # Prepare output directory: base/book_title/
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', self._book.title)[:50]
        self._output_dir = Path(output_base) / safe_title
        self._output_dir.mkdir(parents=True, exist_ok=True)

        type_label = self._type_combo.currentText()

        self._btn_generate.setEnabled(False)
        self._progress.setRange(0, 0)
        self._progress.show()
        self._browser.show()
        self._browser.clear()
        self._status_label.setText(f"正在生成{type_label}...")
        self._result_text = ""

        self._agent.response_chunk.connect(self._on_chunk)
        self._agent.response_finished.connect(self._on_finished)
        self._agent.error_occurred.connect(self._on_error)

        prompt = CODE_EXERCISE_PROMPT.format(
            title=self._book.title,
            author=self._book.author or "未知",
            content=content[:15000],
            exercise_type=type_label,
        )
        from claude.context_builder import BookContext, ClaudeContext, InteractionContext
        ctx = ClaudeContext(
            action="code_exercise",
            book=BookContext(
                title=self._book.title,
                author=self._book.author or "",
                total_pages=self._book.pages,
            ),
            context=InteractionContext(type="general"),
            user_query=prompt,
            history=[],
            no_tools=True,
        )
        self._agent.send(ctx)

    def _on_chunk(self, text: str) -> None:
        self._result_text += text
        char_count = len(self._result_text)
        self._browser.setPlainText(f"已生成 {char_count} 字符...\n\n{self._result_text[-500:]}")

    def _on_finished(self, full_response: str) -> None:
        self._disconnect()
        self._result_text = full_response
        self._progress.setRange(0, 1)
        self._progress.setValue(1)
        self._btn_generate.setEnabled(True)

        files_written = self._parse_and_write_files(full_response)
        if files_written:
            self._status_label.setText(f"完成！已生成 {len(files_written)} 个文件")
            self._browser.setMarkdown(
                "**生成的文件：**\n\n" +
                "\n".join(f"- `{f}`" for f in files_written)
            )
            self._btn_open_dir.show()
            self.finished.emit(str(self._output_dir))
        else:
            self._status_label.setText("完成，但未能解析出文件（已保存原始输出）")
            fallback = self._output_dir / "output.txt"
            fallback.write_text(full_response, encoding="utf-8")
            self._browser.setPlainText(full_response[:2000])
            self._btn_open_dir.show()

    def _on_error(self, err: str) -> None:
        self._disconnect()
        self._progress.setRange(0, 1)
        self._progress.setValue(1)
        self._btn_generate.setEnabled(True)
        self._status_label.setText(f"生成出错: {err}")

    def _disconnect(self) -> None:
        try:
            self._agent.response_chunk.disconnect(self._on_chunk)
        except (RuntimeError, TypeError):
            pass
        try:
            self._agent.response_finished.disconnect(self._on_finished)
        except (RuntimeError, TypeError):
            pass
        try:
            self._agent.error_occurred.disconnect(self._on_error)
        except (RuntimeError, TypeError):
            pass

    def _parse_and_write_files(self, response: str) -> list[str]:
        """Parse === filename: xxx === blocks and write files."""
        pattern = r'===\s*filename:\s*(.+?)\s*===\s*\n(.*?)===\s*end\s*==='
        matches = re.findall(pattern, response, re.DOTALL)
        written: list[str] = []
        for filename, content in matches:
            filename = filename.strip()
            filename = re.sub(r'[<>:"|?*]', '_', filename)
            file_path = self._output_dir / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content.strip(), encoding="utf-8")
            written.append(filename)
        return written

    def _on_open_dir(self) -> None:
        if self._output_dir and self._output_dir.exists():
            import subprocess
            subprocess.Popen(["explorer", str(self._output_dir)])

    def closeEvent(self, event) -> None:
        self._disconnect()
        super().closeEvent(event)
