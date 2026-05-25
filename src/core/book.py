"""图书模型"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Book:
    """单本书的元数据"""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str = ""
    author: str = ""
    isbn: str = ""
    publisher: str = ""
    year: int = 0
    pages: int = 0
    file_path: str = ""
    cover_image_path: str = ""
    category_id: str = ""
    tags: list[str] = field(default_factory=list)
    reading_status: str = "unread"  # unread / reading / completed
    current_page: int = 0
    total_reading_time_sec: int = 0
    rating: int = 0  # 1-5, 0 = 未评分
    personal_note: str = ""
    added_date: str = field(default_factory=lambda: datetime.now().isoformat())
    last_read_date: str = ""
    indexed_pages: int = 0

    @property
    def progress_pct(self) -> float:
        if self.pages <= 0:
            return 0.0
        return min(100.0, self.current_page / self.pages * 100)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "isbn": self.isbn,
            "publisher": self.publisher,
            "year": self.year,
            "pages": self.pages,
            "file_path": self.file_path,
            "cover_image_path": self.cover_image_path,
            "category_id": self.category_id,
            "tags": self.tags,
            "reading_status": self.reading_status,
            "current_page": self.current_page,
            "total_reading_time_sec": self.total_reading_time_sec,
            "rating": self.rating,
            "personal_note": self.personal_note,
            "added_date": self.added_date,
            "last_read_date": self.last_read_date,
            "indexed_pages": self.indexed_pages,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Book:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class Category:
    """分类节点（树形结构）"""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    parent_id: str = ""
    description: str = ""
    children: list[Category] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "parent_id": self.parent_id,
            "description": self.description,
            "children": [c.to_dict() for c in self.children],
        }

    @classmethod
    def from_dict(cls, d: dict) -> Category:
        children = [Category.from_dict(c) for c in d.get("children", [])]
        return cls(
            id=d.get("id", ""),
            name=d.get("name", ""),
            parent_id=d.get("parent_id", ""),
            description=d.get("description", ""),
            children=children,
        )


@dataclass
class Tag:
    """标签"""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    color: str = "#3498db"

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "color": self.color}

    @classmethod
    def from_dict(cls, d: dict) -> Tag:
        return cls(id=d.get("id", ""), name=d.get("name", ""), color=d.get("color", "#3498db"))


@dataclass
class Bookmark:
    """书签"""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    book_id: str = ""
    page_number: int = 0
    title: str = ""
    chapter_title: str = ""
    note: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "book_id": self.book_id,
            "page_number": self.page_number,
            "title": self.title,
            "chapter_title": self.chapter_title,
            "note": self.note,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Bookmark:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
