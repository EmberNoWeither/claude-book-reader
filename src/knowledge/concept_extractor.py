"""概念提取器 — 解析 Claude 返回的 JSON，去重后存入图谱"""

from __future__ import annotations

import json
import re

from PyQt6.QtCore import QObject, pyqtSignal

from .models import Concept, ConceptLink
from .graph_engine import GraphEngine


class ConceptExtractor(QObject):
    """从 Claude 响应中解析概念并集成到知识图谱"""

    extraction_finished = pyqtSignal(list)  # list[Concept]
    error_occurred = pyqtSignal(str)

    def __init__(self, graph_engine: GraphEngine, parent=None) -> None:
        super().__init__(parent)
        self._graph = graph_engine

    def process_response(self, response: str, book_id: str) -> list[Concept]:
        raw = self._parse_json(response)
        if not raw:
            self.error_occurred.emit("无法从响应中解析概念 JSON")
            return []

        added: list[Concept] = []
        for item in raw:
            concept = Concept(
                name=item.get("name", ""),
                description=item.get("description", ""),
                aliases=item.get("aliases", []),
                source_books=[{"book_id": book_id}],
            )
            if not concept.name:
                continue
            result = self._graph.add_concept(concept)
            added.append(result)

            for rel in item.get("relations", []):
                target_name = rel.get("target", "")
                if not target_name:
                    continue
                target = self._graph.find_by_name(target_name)
                if not target:
                    target = Concept(name=target_name, source_books=[{"book_id": book_id}])
                    target = self._graph.add_concept(target)
                link = ConceptLink(
                    source_id=result.id,
                    target_id=target.id,
                    relation_type=rel.get("type", "RELATED_TO"),
                    strength=rel.get("strength", 5),
                    source_book_id=book_id,
                )
                self._graph.add_link(link)

        self._graph.save()
        self.extraction_finished.emit(added)
        return added

    def _parse_json(self, text: str) -> list[dict] | None:
        match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
        json_str = match.group(1).strip() if match else text.strip()
        try:
            data = json.loads(json_str)
            if isinstance(data, list):
                return data
            return None
        except json.JSONDecodeError:
            return None
