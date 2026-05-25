"""ClaudeClient — 通过 claude CLI 进行单次调用，支持流式输出"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from PyQt6.QtCore import QObject, QProcess, pyqtSignal

from .context_builder import ClaudeContext

_TMP_DIR = Path(tempfile.gettempdir()) / "claude-book-reader" / "prompts"


def _build_args(model: str = "") -> tuple[str, list[str]]:
    """返回 (program, args)，prompt 通过 stdin 文件传入"""
    claude_args = ["-p", "-", "--output-format", "stream-json", "--verbose"]
    if model:
        claude_args += ["--model", model]
    if sys.platform == "win32":
        return "cmd", ["/c", "claude"] + claude_args
    return "claude", claude_args


def _build_prompt(ctx: ClaudeContext) -> str:
    """将上下文对象序列化为 prompt 文本"""
    book = ctx.book
    ic = ctx.context

    lines = [
        f"你是《{book.title}》的阅读助手。",
        f"作者：{book.author}，当前第 {book.current_page + 1}/{book.total_pages} 页。",
    ]
    if book.current_chapter:
        lines.append(f"当前章节：{book.current_chapter}")

    if ic.type == "text_selection" and ic.selected_text:
        lines += [
            "",
            f"【用户选中的文字（第 {ic.page + 1} 页）】",
            ic.selected_text,
        ]
        if ic.surrounding_text:
            lines += ["", "【上下文段落】", ic.surrounding_text]

    elif ic.type == "screenshot" and ic.screenshot_path:
        lines += ["", f"【截图路径】{ic.screenshot_path}"]

    elif ic.type == "chapter" and ic.chapter_text:
        lines += ["", "【章节全文】", ic.chapter_text[:4000]]

    if ic.notes and ctx.action == "optimize_notes":
        lines += [
            "",
            "【用户笔记】",
            ic.notes,
            "",
            f"【优化风格】{ic.optimization_style or 'refine'}",
            "请优化以上笔记，使用 Obsidian 兼容的 Markdown 格式，适当使用 [[双链]] 关联概念。",
        ]
    elif ic.notes and ctx.action == "extract_concepts":
        lines += [
            "",
            "【笔记内容】",
            ic.notes,
            "",
            "请从以上笔记中提取关键概念，输出 JSON 数组，每个元素包含：",
            '{"name": "概念名", "description": "简短描述", "aliases": [], '
            '"relations": [{"target": "目标概念", "type": "RELATED_TO", "strength": 5}]}',
        ]

    if ctx.history:
        lines += ["", "【对话历史】"]
        for msg in ctx.history[-10:]:
            role = "用户" if msg["role"] == "user" else "Claude"
            lines.append(f"{role}：{msg['content']}")

    if ctx.user_query:
        lines += ["", f"【用户问题】{ctx.user_query}"]
    else:
        action_prompts = {
            "chapter_analysis": "请分析本章节：列出核心观点、关键概念、值得深入思考的问题。",
            "reading_plan": "请根据目录制定阅读计划。",
            "reading_outline": "请生成详细阅读大纲。",
            "optimize_notes": "请优化以上笔记。",
            "extract_concepts": "请提取关键概念并输出 JSON。",
        }
        lines += ["", action_prompts.get(ctx.action, "请提供帮助。")]

    lines.append("\n请用 Markdown 格式回答，语言与用户问题保持一致（默认中文）。数学公式请使用标准 LaTeX 语法，行内公式用 $...$，块级公式用 $$...$$，确保下标用 _{} 包裹（如 \\sum_{i=1}^{n}）。")
    return "\n".join(lines)


class ClaudeClient(QObject):
    """轻量级单次调用封装，每次调用启动一个新的 claude 子进程，流式读取输出。"""

    response_chunk = pyqtSignal(str)
    response_finished = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, parent: QObject | None = None, model: str = "") -> None:
        super().__init__(parent)
        self._process: QProcess | None = None
        self._buffer = ""
        self._full_response = ""
        self._prompt_file: Path | None = None
        self._model = model
        _TMP_DIR.mkdir(parents=True, exist_ok=True)

    def set_model(self, model: str) -> None:
        self._model = model

    def invoke(self, ctx: ClaudeContext) -> None:
        if self._process and self._process.state() != QProcess.ProcessState.NotRunning:
            self._process.kill()

        self._full_response = ""
        self._buffer = ""

        # prompt 写入临时文件，通过 stdin 传给 claude，避免命令行长度/编码问题
        prompt = _build_prompt(ctx)
        self._prompt_file = _TMP_DIR / f"prompt-{id(self)}.txt"
        self._prompt_file.write_text(prompt, encoding="utf-8")

        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        self._process.setStandardInputFile(str(self._prompt_file))
        self._process.readyReadStandardOutput.connect(self._on_stdout)
        self._process.readyReadStandardError.connect(self._on_stderr)
        self._process.errorOccurred.connect(self._on_process_error)
        self._process.finished.connect(self._on_finished)

        program, args = _build_args(self._model)
        self._process.start(program, args)

    def cancel(self) -> None:
        if self._process and self._process.state() != QProcess.ProcessState.NotRunning:
            self._process.kill()

    def _on_stdout(self) -> None:
        raw = self._process.readAllStandardOutput().data().decode("utf-8", errors="replace")
        self._buffer += raw
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            line = line.strip()
            if not line:
                continue
            text = self._parse_stream_line(line)
            if text:
                self._full_response += text
                self.response_chunk.emit(text)

    def _on_stderr(self) -> None:
        err = self._process.readAllStandardError().data().decode("utf-8", errors="replace").strip()
        if err:
            self.error_occurred.emit(err)

    def _on_process_error(self, error) -> None:
        msg = {
            QProcess.ProcessError.FailedToStart: "claude CLI 启动失败，请确认已安装 Claude Code 且在 PATH 中",
            QProcess.ProcessError.Crashed: "claude 进程意外崩溃",
            QProcess.ProcessError.Timedout: "claude 进程超时",
        }.get(error, f"进程错误: {error}")
        self.error_occurred.emit(msg)

    def _on_finished(self, exit_code: int, _exit_status) -> None:
        if self._buffer.strip():
            text = self._parse_stream_line(self._buffer.strip())
            if text:
                self._full_response += text
        if self._prompt_file:
            self._prompt_file.unlink(missing_ok=True)
            self._prompt_file = None
        if exit_code != 0 and not self._full_response:
            self.error_occurred.emit(f"claude 进程退出码 {exit_code}")
        else:
            self.response_finished.emit(self._full_response)

    @staticmethod
    def _parse_stream_line(line: str) -> str:
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            from utils.logger import get_logger
            get_logger(__name__).debug("Non-JSON stream line: %s", line[:200])
            return ""
        msg_type = obj.get("type", "")
        if msg_type == "assistant":
            parts = obj.get("message", {}).get("content", [])
            return "".join(p.get("text", "") for p in parts if p.get("type") == "text")
        if msg_type == "result":
            return obj.get("result", "")
        return ""


class TitleGenerator(QObject):
    """轻量级标题生成器 — 单独 QProcess 调用，不走 Agent 历史"""

    title_generated = pyqtSignal(str, str)  # note_id, title

    def __init__(self, model: str = "", parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._model = model
        self._process: QProcess | None = None
        self._buffer = ""
        self._full_response = ""
        self._note_id = ""
        self._prompt_file: Path | None = None

    def set_model(self, model: str) -> None:
        self._model = model

    def generate(self, note_id: str, content: str) -> None:
        if self._process and self._process.state() != QProcess.ProcessState.NotRunning:
            return

        self._note_id = note_id
        self._full_response = ""
        self._buffer = ""

        prompt = f"为以下笔记内容生成一个简短标题（10字以内），只输出标题文字，不要加引号或其他格式：\n{content[:300]}"
        self._prompt_file = _TMP_DIR / f"title-{id(self)}.txt"
        self._prompt_file.write_text(prompt, encoding="utf-8")

        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        self._process.setStandardInputFile(str(self._prompt_file))
        self._process.readyReadStandardOutput.connect(self._on_stdout)
        self._process.finished.connect(self._on_finished)

        program, args = _build_args(self._model)
        self._process.start(program, args)

    def _on_stdout(self) -> None:
        raw = self._process.readAllStandardOutput().data().decode("utf-8", errors="replace")
        self._buffer += raw
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            line = line.strip()
            if not line:
                continue
            text = ClaudeClient._parse_stream_line(line)
            if text:
                self._full_response += text

    def _on_finished(self, exit_code: int, _exit_status) -> None:
        if self._buffer.strip():
            text = ClaudeClient._parse_stream_line(self._buffer.strip())
            if text:
                self._full_response += text
        if self._prompt_file:
            self._prompt_file.unlink(missing_ok=True)
            self._prompt_file = None
        title = self._full_response.strip().strip('"').strip("'").strip()[:30]
        if title:
            self.title_generated.emit(self._note_id, title)

