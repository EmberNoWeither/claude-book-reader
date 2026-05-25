"""上下文文件构建器 — 将当前阅读状态序列化为 JSON 供 Claude 读取"""

from __future__ import annotations

import json
import tempfile
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


@dataclass
class BookContext:
    title: str = ""
    author: str = ""
    current_page: int = 0
    total_pages: int = 0
    current_chapter: str = ""
    toc: list[dict] = field(default_factory=list)


@dataclass
class InteractionContext:
    type: str = "general"          # text_selection | screenshot | chapter | general
    selected_text: str = ""
    surrounding_text: str = ""
    page: int = 0
    screenshot_path: str = ""
    chapter_text: str = ""
    notes: str = ""
    optimization_style: str = ""


@dataclass
class ClaudeContext:
    action: str                    # explain_text | analyze_screenshot | chapter_analysis | ...
    book: BookContext
    context: InteractionContext
    user_query: str = ""
    history: list[dict] = field(default_factory=list)
    version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        return d


class ContextBuilder:
    """构建并写入上下文 JSON 文件"""

    _tmp_dir = Path(tempfile.gettempdir()) / "claude-book-reader"

    def __init__(self) -> None:
        self._tmp_dir.mkdir(parents=True, exist_ok=True)

    def build_text_selection(
        self,
        book: BookContext,
        selected_text: str,
        surrounding_text: str,
        page: int,
        user_query: str,
        history: list[dict],
    ) -> ClaudeContext:
        return ClaudeContext(
            action="explain_text",
            book=book,
            context=InteractionContext(
                type="text_selection",
                selected_text=selected_text,
                surrounding_text=surrounding_text,
                page=page,
            ),
            user_query=user_query,
            history=history,
        )

    def build_screenshot(
        self,
        book: BookContext,
        screenshot_path: str,
        user_query: str,
        history: list[dict],
    ) -> ClaudeContext:
        return ClaudeContext(
            action="analyze_screenshot",
            book=book,
            context=InteractionContext(
                type="screenshot",
                screenshot_path=screenshot_path,
            ),
            user_query=user_query,
            history=history,
        )

    def build_chapter_analysis(
        self,
        book: BookContext,
        chapter_text: str,
        history: list[dict],
    ) -> ClaudeContext:
        return ClaudeContext(
            action="chapter_analysis",
            book=book,
            context=InteractionContext(
                type="chapter",
                chapter_text=chapter_text,
            ),
            user_query="",
            history=history,
        )

    def build_general_qa(
        self,
        book: BookContext,
        user_query: str,
        history: list[dict],
    ) -> ClaudeContext:
        return ClaudeContext(
            action="general_qa",
            book=book,
            context=InteractionContext(type="general"),
            user_query=user_query,
            history=history,
        )

    def build_note_optimization(
        self,
        book: BookContext,
        notes: str,
        optimization_style: str,
        history: list[dict],
    ) -> ClaudeContext:
        return ClaudeContext(
            action="optimize_notes",
            book=book,
            context=InteractionContext(
                type="general",
                notes=notes,
                optimization_style=optimization_style,
            ),
            user_query="",
            history=history,
        )

    def build_concept_extraction(
        self,
        book: BookContext,
        notes_content: str,
        history: list[dict],
    ) -> ClaudeContext:
        return ClaudeContext(
            action="extract_concepts",
            book=book,
            context=InteractionContext(type="general", notes=notes_content),
            user_query="",
            history=history,
        )

    def write_context_file(self, ctx: ClaudeContext) -> Path:
        """将上下文写入临时 JSON 文件，返回文件路径"""
        path = self._tmp_dir / f"ctx-{int(time.time() * 1000)}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(ctx.to_dict(), f, ensure_ascii=False, indent=2)
        return path

    def cleanup_old_files(self, max_age_sec: int = 3600) -> None:
        """清理超过 max_age_sec 秒的旧上下文文件"""
        now = time.time()
        for p in self._tmp_dir.glob("ctx-*.json"):
            if now - p.stat().st_mtime > max_age_sec:
                p.unlink(missing_ok=True)
