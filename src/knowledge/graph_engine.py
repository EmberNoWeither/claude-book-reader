"""知识图谱引擎 — NetworkX 图构建、CRUD、去重合并、布局计算"""

from __future__ import annotations

import networkx as nx

from core.storage import Storage

from .models import Concept, ConceptLink


class GraphEngine:
    """管理概念图谱：加载/保存/查询/去重"""

    def __init__(self, storage: Storage) -> None:
        self._storage = storage
        self._graph = nx.Graph()
        self._concepts: dict[str, Concept] = {}
        self._links: dict[str, ConceptLink] = {}
        self.load()

    def load(self) -> None:
        raw_concepts = self._storage.read_json("concepts.json")
        raw_links = self._storage.read_json("concept_links.json")
        self._concepts.clear()
        self._links.clear()
        self._graph.clear()

        if isinstance(raw_concepts, list):
            for d in raw_concepts:
                c = Concept.from_dict(d)
                self._concepts[c.id] = c
                self._graph.add_node(c.id, label=c.name)

        if isinstance(raw_links, list):
            for d in raw_links:
                link = ConceptLink.from_dict(d)
                self._links[link.id] = link
                self._graph.add_edge(
                    link.source_id, link.target_id,
                    id=link.id, relation=link.relation_type, weight=link.strength,
                )

    def save(self) -> None:
        self._storage.write_json(
            "concepts.json", [c.to_dict() for c in self._concepts.values()]
        )
        self._storage.write_json(
            "concept_links.json", [link.to_dict() for link in self._links.values()]
        )

    # ── CRUD ──────────────────────────────────────────

    def add_concept(self, concept: Concept) -> Concept:
        existing = self.find_by_name(concept.name)
        if existing:
            return self._merge_concept(existing, concept)
        self._concepts[concept.id] = concept
        self._graph.add_node(concept.id, label=concept.name)
        return concept

    def add_link(self, link: ConceptLink) -> ConceptLink:
        if link.source_id not in self._concepts or link.target_id not in self._concepts:
            return link
        self._links[link.id] = link
        self._graph.add_edge(
            link.source_id, link.target_id,
            id=link.id, relation=link.relation_type, weight=link.strength,
        )
        return link

    def remove_concept(self, concept_id: str) -> None:
        self._concepts.pop(concept_id, None)
        links_to_remove = [
            lid for lid, link in self._links.items()
            if link.source_id == concept_id or link.target_id == concept_id
        ]
        for lid in links_to_remove:
            self._links.pop(lid, None)
        if concept_id in self._graph:
            self._graph.remove_node(concept_id)

    def remove_link(self, link_id: str) -> None:
        link = self._links.pop(link_id, None)
        if link and self._graph.has_edge(link.source_id, link.target_id):
            self._graph.remove_edge(link.source_id, link.target_id)

    # ── 查询 ──────────────────────────────────────────

    @property
    def concepts(self) -> list[Concept]:
        return list(self._concepts.values())

    @property
    def links(self) -> list[ConceptLink]:
        return list(self._links.values())

    def get_concept(self, concept_id: str) -> Concept | None:
        return self._concepts.get(concept_id)

    def find_by_name(self, name: str) -> Concept | None:
        name_lower = name.lower()
        for c in self._concepts.values():
            if c.name.lower() == name_lower:
                return c
            if any(a.lower() == name_lower for a in c.aliases):
                return c
        return None

    def neighbors(self, concept_id: str, depth: int = 1) -> list[Concept]:
        if concept_id not in self._graph:
            return []
        visited: set[str] = set()
        frontier = {concept_id}
        for _ in range(depth):
            next_frontier: set[str] = set()
            for nid in frontier:
                for neighbor in self._graph.neighbors(nid):
                    if neighbor not in visited and neighbor != concept_id:
                        next_frontier.add(neighbor)
            visited.update(next_frontier)
            frontier = next_frontier
        return [self._concepts[nid] for nid in visited if nid in self._concepts]

    def concepts_for_book(self, book_id: str) -> list[Concept]:
        return [
            c for c in self._concepts.values()
            if any(s.get("book_id") == book_id for s in c.source_books)
        ]

    # ── 布局 ──────────────────────────────────────────

    def compute_layout(
        self, concept_ids: list[str] | None = None, algorithm: str = "spring"
    ) -> dict[str, tuple[float, float]]:
        if concept_ids:
            subgraph = self._graph.subgraph(
                [cid for cid in concept_ids if cid in self._graph]
            )
        else:
            subgraph = self._graph

        if len(subgraph) == 0:
            return {}

        layout_fn = {
            "spring": nx.spring_layout,
            "kamada_kawai": nx.kamada_kawai_layout,
            "shell": nx.shell_layout,
        }.get(algorithm, nx.spring_layout)

        pos = layout_fn(subgraph)
        return {nid: (float(x), float(y)) for nid, (x, y) in pos.items()}

    # ── 去重合并 ──────────────────────────────────────

    def _merge_concept(self, existing: Concept, new: Concept) -> Concept:
        for src in new.source_books:
            if src not in existing.source_books:
                existing.source_books.append(src)
        for alias in new.aliases:
            if alias not in existing.aliases:
                existing.aliases.append(alias)
        if new.description and not existing.description:
            existing.description = new.description
        return existing
