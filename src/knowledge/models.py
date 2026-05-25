"""知识图谱数据模型"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Concept:
    """知识图谱节点"""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    name: str = ""
    description: str = ""
    aliases: list[str] = field(default_factory=list)
    source_books: list[dict] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    modified_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "aliases": self.aliases,
            "source_books": self.source_books,
            "tags": self.tags,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Concept:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ConceptLink:
    """知识图谱边"""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    source_id: str = ""
    target_id: str = ""
    relation_type: str = "RELATED_TO"  # IS_A | RELATED_TO | PART_OF | LEADS_TO | APPLIES_TO
    strength: int = 5
    description: str = ""
    source_book_id: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type,
            "strength": self.strength,
            "description": self.description,
            "source_book_id": self.source_book_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ConceptLink:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
