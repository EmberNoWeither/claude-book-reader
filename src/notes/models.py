"""笔记数据模型"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Note:
    """单条笔记"""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    book_id: str = ""
    note_type: str = "page_anchor"  # page_anchor | chapter | global | highlight
    page: int = 0
    chapter: str = ""
    title: str = ""
    content: str = ""
    highlighted_text: str = ""
    highlight_rects: list[list[float]] = field(default_factory=list)  # [[x0,y0,x1,y1], ...]
    tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    modified_at: str = field(default_factory=lambda: datetime.now().isoformat())
    optimized_content: str = ""
    optimization_style: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "book_id": self.book_id,
            "note_type": self.note_type,
            "page": self.page,
            "chapter": self.chapter,
            "title": self.title,
            "content": self.content,
            "highlighted_text": self.highlighted_text,
            "highlight_rects": self.highlight_rects,
            "tags": self.tags,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "optimized_content": self.optimized_content,
            "optimization_style": self.optimization_style,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Note:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
