"""ClaudeAgent — 每本书一个 Agent，维护对话历史"""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

from .claude_client import ClaudeClient
from .context_builder import BookContext, ClaudeContext, ContextBuilder


class ClaudeAgent(QObject):
    """
    与单本书绑定的 Claude 会话代理。
    维护对话历史，每次调用通过 ClaudeClient 发送完整上下文。
    """

    response_chunk = pyqtSignal(str)
    response_finished = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    busy_changed = pyqtSignal(bool)

    MAX_HISTORY = 40  # 最多保留 40 条消息（20 轮对话）

    def __init__(self, book: BookContext, parent: QObject | None = None, model: str = "") -> None:
        super().__init__(parent)
        self.book = book
        self._history: list[dict] = []
        self._book_preview: str = ""
        self._client = ClaudeClient(self, model=model)
        self._client.response_chunk.connect(self.response_chunk)
        self._client.response_finished.connect(self._on_finished)
        self._client.error_occurred.connect(self._on_error)
        self._pending_user_msg = ""
        self._busy = False

    def set_book_preview(self, preview: str) -> None:
        self._book_preview = preview

    def set_model(self, model: str) -> None:
        self._client.set_model(model)

    @property
    def is_busy(self) -> bool:
        return self._busy

    @property
    def history(self) -> list[dict]:
        return list(self._history)

    def send(self, ctx: ClaudeContext) -> None:
        """发送消息（附带完整历史）"""
        if self._busy:
            return
        history = list(self._history)
        if self._book_preview and ctx.action != "book_preview":
            history = [{"role": "system", "content": f"[全书预览总结]\n{self._book_preview}"}] + history
        ctx.history = history
        self._pending_user_msg = ctx.user_query or f"[{ctx.action}]"
        self._set_busy(True)
        self._client.invoke(ctx)

    def send_text_question(
        self,
        selected_text: str,
        surrounding_text: str,
        page: int,
        user_query: str,
    ) -> None:
        builder = ContextBuilder()
        ctx = builder.build_text_selection(
            book=self.book,
            selected_text=selected_text,
            surrounding_text=surrounding_text,
            page=page,
            user_query=user_query,
            history=self._history,
        )
        self.send(ctx)

    def send_screenshot_question(
        self, screenshot_path: str, user_query: str
    ) -> None:
        builder = ContextBuilder()
        ctx = builder.build_screenshot(
            book=self.book,
            screenshot_path=screenshot_path,
            user_query=user_query,
            history=self._history,
        )
        self.send(ctx)

    def send_general_question(self, user_query: str) -> None:
        builder = ContextBuilder()
        ctx = builder.build_general_qa(
            book=self.book,
            user_query=user_query,
            history=self._history,
        )
        self.send(ctx)

    def send_chapter_analysis(self, chapter_text: str) -> None:
        builder = ContextBuilder()
        ctx = builder.build_chapter_analysis(
            book=self.book,
            chapter_text=chapter_text,
            history=self._history,
        )
        self.send(ctx)

    def send_note_optimization(self, notes: str, style: str) -> None:
        builder = ContextBuilder()
        ctx = builder.build_note_optimization(
            book=self.book,
            notes=notes,
            optimization_style=style,
            history=self._history,
        )
        self.send(ctx)

    def send_concept_extraction(self, notes_content: str) -> None:
        builder = ContextBuilder()
        ctx = builder.build_concept_extraction(
            book=self.book,
            notes_content=notes_content,
            history=self._history,
        )
        self.send(ctx)

    def send_note_followup(self, note_content: str, question: str) -> None:
        builder = ContextBuilder()
        ctx = builder.build_note_followup(
            book=self.book,
            note_content=note_content,
            question=question,
            history=self._history,
        )
        self.send(ctx)

    def cancel(self) -> None:
        self._client.cancel()
        self._set_busy(False)

    def clear_history(self) -> None:
        self._history.clear()

    def update_book_context(self, page: int, chapter: str) -> None:
        self.book.current_page = page
        self.book.current_chapter = chapter

    # ── 内部 ─────────────────────────────────────────

    def _on_finished(self, full_response: str) -> None:
        if self._pending_user_msg:
            self._history.append({"role": "user", "content": self._pending_user_msg})
        if full_response:
            self._history.append({"role": "assistant", "content": full_response})
        # 裁剪历史
        if len(self._history) > self.MAX_HISTORY:
            self._history = self._history[-self.MAX_HISTORY:]
        self._pending_user_msg = ""
        self._set_busy(False)
        self.response_finished.emit(full_response)

    def _on_error(self, err: str) -> None:
        self._pending_user_msg = ""
        self._set_busy(False)
        self.error_occurred.emit(err)

    def _set_busy(self, busy: bool) -> None:
        if self._busy != busy:
            self._busy = busy
            self.busy_changed.emit(busy)


class ClaudeAgentManager(QObject):
    """管理所有书籍的 Agent 实例，限制最大并发数"""

    MAX_AGENTS = 3

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._agents: dict[str, ClaudeAgent] = {}
        self._order: list[str] = []  # 按打开顺序排列

    def get_or_create(self, book_id: str, book: BookContext, model: str = "") -> ClaudeAgent:
        if book_id in self._agents:
            return self._agents[book_id]
        # 超出上限时关闭最早打开的
        if len(self._agents) >= self.MAX_AGENTS:
            oldest = self._order[0]
            self.close_book(oldest)
        agent = ClaudeAgent(book, self, model=model)
        self._agents[book_id] = agent
        self._order.append(book_id)
        return agent

    def set_model_all(self, model: str) -> None:
        """更新所有 Agent 的模型"""
        for agent in self._agents.values():
            agent.set_model(model)

    def get(self, book_id: str) -> ClaudeAgent | None:
        return self._agents.get(book_id)

    def close_book(self, book_id: str) -> None:
        agent = self._agents.pop(book_id, None)
        if agent:
            agent.cancel()
            agent.deleteLater()
        if book_id in self._order:
            self._order.remove(book_id)

    def close_all(self) -> None:
        for book_id in list(self._agents):
            self.close_book(book_id)
